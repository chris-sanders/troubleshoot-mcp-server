"""
End-to-end tests for the MCP server container.

These tests verify the container functionality:
1. Building the container image
2. Running the container with basic commands
3. Testing the MCP server functionality within the container

The tests use fixtures to ensure container images are built only once and
shared across tests for efficiency.
"""

import os
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

import pytest

# Get the project root directory
PROJECT_ROOT = Path(__file__).parents[2].absolute()

# Mark all tests in this file
pytestmark = [pytest.mark.e2e, pytest.mark.container]

# The image tag to use for all tests
TEST_IMAGE_TAG = "mcp-server-troubleshoot:test"


@pytest.fixture(scope="module")
def container_image():
    """
    Build the container image once for all tests.

    This fixture:
    1. Checks if podman is available
    2. Builds the container image
    3. Verifies the build was successful
    4. Cleans up the image after all tests are done

    Returns:
        The image tag that can be used in tests
    """
    # Check that Podman is available
    try:
        subprocess.run(
            ["podman", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=5,
        )
    except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("Podman is not available")

    try:
        # Build the image (this is done once per test module)
        print(f"\nBuilding container image: {TEST_IMAGE_TAG}")
        result = subprocess.run(
            ["podman", "build", "-t", TEST_IMAGE_TAG, "-f", "Containerfile", "."],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,  # Don't raise exception, handle it ourselves
            timeout=300,  # 5 minutes timeout for build
        )

        # Check if build succeeded
        if result.returncode != 0:
            pytest.fail(f"Container build failed: {result.stderr}")

        # Verify image exists
        image_check = subprocess.run(
            ["podman", "image", "exists", TEST_IMAGE_TAG],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

        if image_check.returncode != 0:
            pytest.fail(f"Image {TEST_IMAGE_TAG} not found after build")

        # The image is ready for use
        yield TEST_IMAGE_TAG

    finally:
        # Clean up the test image after all tests
        print(f"\nCleaning up container image: {TEST_IMAGE_TAG}")
        subprocess.run(
            ["podman", "rmi", "-f", TEST_IMAGE_TAG],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


@pytest.fixture
def bundles_directory():
    """Create a temporary directory for bundles."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def test_container(container_image, bundles_directory):
    """
    Setup and teardown for an individual container test.

    This fixture:
    1. Takes the already-built container image from the container_image fixture
    2. Creates a unique container name for this test
    3. Handles cleanup of the container after the test

    Returns:
        A tuple of (container_name, bundles_directory)
    """
    # Generate a unique container name for this test
    container_name = f"mcp-test-{uuid.uuid4().hex[:8]}"

    # Set test environment variables
    test_env = os.environ.copy()
    test_env["SBCTL_TOKEN"] = "test-token"

    # The container is created and managed by individual tests
    yield container_name, bundles_directory, test_env

    # Clean up the container after the test
    subprocess.run(
        ["podman", "rm", "-f", container_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def test_basic_container_functionality(container_image, test_container):
    """Test that the container can run basic commands."""
    container_name, bundles_dir, env = test_container

    result = subprocess.run(
        [
            "podman",
            "run",
            "--name",
            container_name,
            "--rm",
            "-v",
            f"{bundles_dir}:/data/bundles",
            "-e",
            f"SBCTL_TOKEN={env.get('SBCTL_TOKEN', 'test-token')}",
            "--entrypoint",
            "/bin/bash",
            container_image,
            "-c",
            "echo 'Container is working!'",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )

    assert "Container is working!" in result.stdout


def test_python_functionality(container_image, test_container):
    """Test that Python works correctly in the container."""
    container_name, bundles_dir, env = test_container

    result = subprocess.run(
        [
            "podman",
            "run",
            "--name",
            container_name,
            "--rm",
            "-v",
            f"{bundles_dir}:/data/bundles",
            "-e",
            f"SBCTL_TOKEN={env.get('SBCTL_TOKEN', 'test-token')}",
            "--entrypoint",
            "/bin/bash",
            container_image,
            "-c",
            "python --version",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )

    version_output = result.stdout.strip() or result.stderr.strip()
    assert "Python" in version_output


def test_mcp_cli(container_image, test_container):
    """Test that the MCP server CLI works in the container."""
    container_name, bundles_dir, env = test_container

    result = subprocess.run(
        [
            "podman",
            "run",
            "--name",
            container_name,
            "--rm",
            "-v",
            f"{bundles_dir}:/data/bundles",
            "-e",
            f"SBCTL_TOKEN={env.get('SBCTL_TOKEN', 'test-token')}",
            "--entrypoint",
            "/bin/bash",
            container_image,
            "-c",
            "python -m mcp_server_troubleshoot.cli --help",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    combined_output = result.stdout + result.stderr
    assert "usage:" in combined_output.lower() or result.returncode == 0, "CLI help command failed"


def test_required_tools_installed(container_image, test_container):
    """Test that required tools are installed in the container."""
    container_name, bundles_dir, env = test_container

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
                container_name,
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


@pytest.mark.timeout(30)  # Set a timeout for the test
def test_mcp_server_startup(container_image, test_container):
    """
    Test that the MCP server starts up correctly in the container.

    This test:
    1. Starts the container in detached mode
    2. Verifies the container is running
    3. Checks the container logs for expected startup messages
    """
    container_name, bundles_dir, env = test_container

    # Start the container in detached mode
    container_start = subprocess.run(
        [
            "podman",
            "run",
            "--name",
            container_name,
            "-d",  # Detached mode
            "-i",  # Interactive mode for stdin
            "-v",
            f"{bundles_dir}:/data/bundles",
            "-e",
            "SBCTL_TOKEN=test-token",
            "-e",
            "MCP_BUNDLE_STORAGE=/data/bundles",
            container_image,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    # Check if the container started successfully
    assert container_start.returncode == 0, f"Failed to start container: {container_start.stderr}"

    try:
        # Wait a moment for the container to start
        time.sleep(2)

        # Check if the container is running
        ps_check = subprocess.run(
            ["podman", "ps", "-q", "-f", f"name={container_name}"],
            stdout=subprocess.PIPE,
            text=True,
        )

        assert ps_check.stdout.strip(), "Container failed to start or exited immediately"

        # Check the container logs
        logs_check = subprocess.run(
            ["podman", "logs", container_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        combined_logs = logs_check.stdout + logs_check.stderr

        # Check for expected startup messages (adjust based on your actual logs)
        assert (
            "signal handlers" in combined_logs.lower() or "starting" in combined_logs.lower()
        ), "Container logs don't show expected startup messages"

    finally:
        # The fixture will clean up the container
        pass


def test_volume_mounting(container_image, test_container):
    """Test that volumes are mounted correctly in the container."""
    container_name, bundles_dir, env = test_container

    # Create a test file in the bundles directory
    test_filename = "test_volume_mount.txt"
    test_content = "This is a test file for volume mounting"
    test_file_path = bundles_dir / test_filename

    with open(test_file_path, "w") as f:
        f.write(test_content)

    # Check if the file is visible inside the container
    result = subprocess.run(
        [
            "podman",
            "run",
            "--name",
            container_name,
            "--rm",
            "-v",
            f"{bundles_dir}:/data/bundles",
            "--entrypoint",
            "/bin/bash",
            container_image,
            "-c",
            f"cat /data/bundles/{test_filename}",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )

    assert test_content in result.stdout, "Volume mount failed, test file not visible in container"


if __name__ == "__main__":
    """
    Allow running this test file directly.

    This provides a convenient way to run just the container tests during development:
    python -m tests.e2e.test_container_consolidated
    """
    # Use pytest to run the tests
    pytest.main(["-xvs", __file__])
