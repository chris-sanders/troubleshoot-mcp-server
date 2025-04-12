"""
Test configuration and fixtures for pytest.
"""

import subprocess
import pytest
from pathlib import Path


@pytest.fixture
def fixtures_dir() -> Path:
    """
    Returns the path to the test fixtures directory.

    This is a standardized location for test data files.
    """
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def test_support_bundle(fixtures_dir) -> Path:
    """
    Returns the path to the test support bundle file.

    This fixture ensures the support bundle exists before returning it.
    """
    bundle_path = fixtures_dir / "support-bundle-2025-04-11T14_05_31.tar.gz"
    assert bundle_path.exists(), f"Support bundle not found at {bundle_path}"
    return bundle_path


def is_docker_available():
    """Check if Docker is available on the system."""
    try:
        subprocess.run(
            ["docker", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def build_docker_image(project_root):
    """Build the Docker image for tests."""
    # Find the build script
    build_script = project_root / "scripts" / "build.sh"
    if not build_script.exists():
        build_script = project_root / "build.sh"

    if not build_script.exists():
        return False, "Build script not found"

    try:
        # Remove any existing image first to ensure a clean build
        subprocess.run(
            ["docker", "rmi", "-f", "mcp-server-troubleshoot:latest"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Build the image
        result = subprocess.run(
            [str(build_script)],
            check=True,
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return True, result
    except subprocess.CalledProcessError as e:
        return False, e


@pytest.fixture(scope="session")
def docker_image():
    """
    Session-scoped fixture that ensures the Docker image is built once for all tests.

    This is used by all e2e tests to avoid rebuilding the image for each test file.
    """
    # Skip if Docker is not available
    if not is_docker_available():
        pytest.skip("Docker is not available")

    # Get project root directory
    project_root = Path(__file__).parent.parent

    # Build the Docker image
    print("\nBuilding Docker image for all tests...")
    success, result = build_docker_image(project_root)

    if not success:
        if isinstance(result, str):
            pytest.skip(f"Failed to build Docker image: {result}")
        else:
            pytest.skip(f"Failed to build Docker image: {result.stderr}")

    # Yield to allow tests to run
    yield "mcp-server-troubleshoot:latest"

    # Cleanup is optional here - we could leave the image for future use
    # If you want to clean up after all tests:
    # subprocess.run(["docker", "rmi", "-f", "mcp-server-troubleshoot:latest"],
    #                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@pytest.fixture(scope="session")
def ensure_bundles_directory():
    """
    Get the standard bundle directory for tests.

    This consistently uses the fixtures directory that contains the actual test bundle
    instead of the empty bundles directory.
    """
    fixtures_dir = Path(__file__).parent / "fixtures"
    assert fixtures_dir.exists(), f"Fixtures directory not found at {fixtures_dir}"
    return fixtures_dir
