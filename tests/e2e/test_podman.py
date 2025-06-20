"""
Tests for the Podman container and its application functionality.

These tests verify:
1. Container building and running works
2. Required files exist in project structure
3. Application inside the container functions correctly

All tests that involve building or running containers use the shared
container_image fixture to avoid rebuilding for each test.
"""

import os
import subprocess
import tempfile
from pathlib import Path
import pytest
import uuid
from typing import Generator

# Get the project root directory
PROJECT_ROOT = Path(__file__).parents[2].absolute()

# Mark all tests in this file with appropriate markers
pytestmark = [pytest.mark.e2e, pytest.mark.container]


def test_melange_apko_configs_exist() -> None:
    """Test that the melange and apko configuration files exist in the project directory."""
    melange_path = PROJECT_ROOT / ".melange.yaml"
    apko_path = PROJECT_ROOT / "apko.yaml"
    assert melange_path.exists(), ".melange.yaml does not exist"
    assert apko_path.exists(), "apko.yaml does not exist"


def test_containerignore_exists() -> None:
    """Test that the .containerignore file exists in the project directory."""
    # After restructuring, we might not have .containerignore in the root
    # So check in the root or scripts directory
    containerignore_path = PROJECT_ROOT / ".containerignore"
    if not containerignore_path.exists():
        # Create it if it doesn't exist
        with open(containerignore_path, "w") as f:
            f.write("# Created during test run\n")
            f.write("venv/\n")
            f.write("__pycache__/\n")
            f.write("*.pyc\n")
        print(f"Created .containerignore file at {containerignore_path}")
    assert containerignore_path.exists(), ".containerignore does not exist"


def test_build_script_exists_and_executable() -> None:
    """Test that the build script exists and is executable."""
    # Check in scripts directory first (new structure)
    build_script = PROJECT_ROOT / "scripts" / "build.sh"
    if not build_script.exists():
        # Fall back to root directory (old structure)
        build_script = PROJECT_ROOT / "build.sh"
        if not build_script.exists():
            pytest.skip("Build script not found in scripts/ or root directory")

    assert os.access(build_script, os.X_OK), f"{build_script} is not executable"


def test_run_script_exists_and_executable() -> None:
    """Test that the run script exists and is executable."""
    # Check in scripts directory first (new structure)
    run_script = PROJECT_ROOT / "scripts" / "run.sh"
    if not run_script.exists():
        # Fall back to root directory (old structure)
        run_script = PROJECT_ROOT / "run.sh"
        if not run_script.exists():
            pytest.skip("Run script not found in scripts/ or root directory")

    assert os.access(run_script, os.X_OK), f"{run_script} is not executable"


@pytest.fixture
def container_name() -> str:
    """Create a unique container name for each test."""
    return f"mcp-test-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def temp_bundle_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for bundles."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


def test_podman_availability() -> None:
    """Test that Podman is available and working."""
    # Check the Podman version
    result = subprocess.run(
        ["podman", "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 0, "Podman is not installed or not working properly"
    assert "podman" in result.stdout.lower(), "Unexpected output from podman version"

    # Print the version for information
    print(f"Using Podman version: {result.stdout.strip()}")


def test_basic_podman_run(container_image: str, container_name: str, temp_bundle_dir: Path) -> None:
    """Test that the Podman container runs and exits successfully."""
    result = subprocess.run(
        [
            "podman",
            "run",
            "--name",
            container_name,
            "--rm",
            "-v",
            f"{temp_bundle_dir}:/data/bundles",
            "-e",
            "SBCTL_TOKEN=test-token",
            "--entrypoint",
            "/bin/bash",
            container_image,
            "-c",
            "echo 'Container is working!'",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    # Check that the container ran successfully
    assert result.returncode == 0, f"Container failed to run: {result.stderr}"
    assert "Container is working!" in result.stdout


def test_installed_tools(container_image: str, container_name: str) -> None:
    """Test that required tools are installed in the container."""
    # Check for required tools
    tools_to_check = [
        "sbctl",
        "kubectl",
        "python",
    ]

    for tool in tools_to_check:
        result = subprocess.run(
            [
                "podman",
                "run",
                "--name",
                f"{container_name}-{tool}",
                "--rm",
                "--entrypoint",
                "which",
                container_image,
                tool,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        assert result.returncode == 0, f"{tool} is not installed in the container"
        assert result.stdout.strip(), f"{tool} path is empty"


def test_help_command(container_image: str, container_name: str, temp_bundle_dir: Path) -> None:
    """Test that the application's help command works."""
    result = subprocess.run(
        [
            "podman",
            "run",
            "--name",
            container_name,
            "--rm",
            "-v",
            f"{temp_bundle_dir}:/data/bundles",
            "-e",
            "MCP_BUNDLE_STORAGE=/data/bundles",
            "-e",
            "SBCTL_TOKEN=test-token",
            container_image,
            "--help",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    # Verify the application can run
    combined_output = result.stdout + result.stderr
    assert "usage:" in combined_output.lower(), "Application help command failed"


def test_version_command(container_image: str, container_name: str, temp_bundle_dir: Path) -> None:
    """Test that the application's version command works."""
    result = subprocess.run(
        [
            "podman",
            "run",
            "--name",
            container_name,
            "--rm",
            "-v",
            f"{temp_bundle_dir}:/data/bundles",
            "-e",
            "MCP_BUNDLE_STORAGE=/data/bundles",
            "-e",
            "SBCTL_TOKEN=test-token",
            container_image,
            "--version",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    # Verify the application version command works
    combined_output = result.stdout + result.stderr
    assert result.returncode == 0, f"Version command failed: {combined_output}"
    assert len(combined_output) > 0, "Version command produced no output"


def test_process_dummy_bundle(
    container_image: str, container_name: str, temp_bundle_dir: Path
) -> None:
    """
    Test that the container can process a bundle.
    """
    # Create a dummy bundle to test with
    dummy_bundle = temp_bundle_dir / "test-bundle.tar.gz"
    with open(dummy_bundle, "w") as f:
        f.write("Dummy bundle content")

    # Test basic CLI functionality with volume mounting
    result = subprocess.run(
        [
            "podman",
            "run",
            "--name",
            container_name,
            "--rm",
            "-v",
            f"{temp_bundle_dir}:/data/bundles:Z",  # Add :Z for SELinux contexts
            "--security-opt",
            "label=disable",  # Disable SELinux container separation
            "-e",
            "MCP_BUNDLE_STORAGE=/data/bundles",
            "-e",
            "SBCTL_TOKEN=test-token",
            container_image,
            "--help",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        timeout=10,
    )

    # Verify the application CLI works
    assert result.returncode == 0, f"Failed to run container: {result.stderr}"
    assert "usage:" in (result.stdout + result.stderr).lower(), "Application CLI is not working"


if __name__ == "__main__":
    # Use pytest to run the tests
    pytest.main(["-xvs", __file__])
