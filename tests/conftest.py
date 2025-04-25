"""
Test configuration and fixtures for pytest.
"""

import os
import subprocess
import contextlib
import pytest
from pathlib import Path

# Configure pytest_asyncio globally
pytest_plugins = ["pytest_asyncio"]


# Custom fixture for cleaning up resources
@pytest.fixture
def resource_cleaner():
    """
    Provides an exit stack that ensures resources are properly closed after tests.

    This helps prevent ResourceWarning by ensuring proper cleanup of file handles,
    sockets, and other resources created during tests.

    Example usage:
        def test_file_operations(resource_cleaner):
            # Files will be closed automatically at test exit
            file = resource_cleaner.enter_context(open("some_file.txt", "r"))
            # Test code that uses the file
    """
    with contextlib.ExitStack() as stack:
        yield stack
        # Resources will be automatically closed when the test exits


# Custom fixture for cleaning up asyncio resources
@pytest.fixture
def clean_asyncio():
    """
    Provides a clean event loop for each test and ensures proper resource cleanup.

    This fixture:
    1. Creates a new event loop for test isolation
    2. Properly cancels pending tasks after the test
    3. Correctly shuts down async generators
    4. Closes the loop cleanly to avoid resource warnings

    Returns:
        The event loop for the test to use
    """
    import asyncio
    import gc

    # Create a new event loop for proper test isolation
    # No need to suppress warnings - we've configured proper scopes
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Yield the loop to the test
    yield loop

    # Clean up resources after the test
    try:
        # Cancel all pending tasks
        pending = asyncio.all_tasks(loop)
        if pending:
            # Cancel all tasks first
            for task in pending:
                task.cancel()

            # Wait for cancellation to complete with timeout
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

        # Properly shut down async generators
        # This prevents "coroutine was never awaited" warnings
        if hasattr(loop, "shutdown_asyncgens"):
            loop.run_until_complete(loop.shutdown_asyncgens())

        # Close the loop properly
        loop.close()

    except (RuntimeError, asyncio.CancelledError) as e:
        # Only log specific understood errors to avoid silent failures
        import logging

        logging.getLogger("tests").debug(f"Controlled exception during event loop cleanup: {e}")

    # Create a new event loop for the next test
    asyncio.set_event_loop(asyncio.new_event_loop())

    # Force garbage collection to clean up any lingering objects
    gc.collect()


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
    """Check if Podman is available on the system."""
    try:
        with subprocess.Popen(
            ["podman", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        ) as process:
            process.communicate(timeout=5)
            return process.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


@contextlib.contextmanager
def safe_open(file_path, mode):
    """Safely open a file and ensure it's closed."""
    file = open(file_path, mode)
    try:
        yield file
    finally:
        file.close()


def build_container_image(project_root, use_mock_sbctl=False):
    """
    Build the Podman image for tests.

    Args:
        project_root: The root directory of the project
        use_mock_sbctl: Whether to use the mock sbctl implementation

    Returns:
        A tuple of (success, result) where success is a boolean and result
        is either the subprocess.CompletedProcess or an exception
    """
    # Find the build script - should be in the scripts directory
    build_script = project_root / "scripts" / "build.sh"

    if not build_script.exists():
        return False, "Build script not found"

    try:
        # Remove any existing image first to ensure a clean build
        with subprocess.Popen(
            ["podman", "rmi", "-f", "mcp-server-troubleshoot:latest"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ) as process:
            process.communicate(timeout=30)

        # For test mode with mock sbctl, we need to modify the Containerfile
        if use_mock_sbctl:
            # Create a temporary Containerfile.test
            containerfile = project_root / "Containerfile"
            if not containerfile.exists():
                return False, "Containerfile not found"

            # Read the original Containerfile
            containerfile_content = ""
            with safe_open(containerfile, "r") as f:
                containerfile_content = f.read()

            # Create a modified version that uses mock_sbctl.py
            containerfile_test = project_root / "Containerfile.test"

            # Replace the sbctl installation section with the mock version
            mock_sbctl_section = """
# Use mock sbctl script instead of the real one
COPY tests/fixtures/mock_sbctl.py /usr/local/bin/sbctl
RUN chmod +x /usr/local/bin/sbctl
"""
            # Find the right section to replace
            if "Install the real sbctl binary" in containerfile_content:
                # Replace the real sbctl installation with the mock one
                containerfile_content = containerfile_content.replace(
                    '# Install the real sbctl binary - AMD64 version for standard container usage\nRUN mkdir -p /tmp/sbctl && cd /tmp/sbctl && \\\n    curl -L -o sbctl.tar.gz "https://github.com/replicatedhq/sbctl/releases/latest/download/sbctl_linux_amd64.tar.gz" && \\\n    tar xzf sbctl.tar.gz && \\\n    chmod +x sbctl && \\\n    mv sbctl /usr/local/bin/ && \\\n    cd / && \\\n    rm -rf /tmp/sbctl && \\\n    sbctl --help',
                    mock_sbctl_section,
                )
            else:
                # If we can't find the exact section, just add it before creating the data directory
                containerfile_content = containerfile_content.replace(
                    "# Create data directory for bundles",
                    mock_sbctl_section + "\n# Create data directory for bundles",
                )

            # Write the modified Containerfile
            with safe_open(containerfile_test, "w") as f:
                f.write(containerfile_content)

            # Build using the temporary Containerfile
            result = None
            with subprocess.Popen(
                [
                    "podman",
                    "build",
                    "-f",
                    "Containerfile.test",
                    "-t",
                    "mcp-server-troubleshoot:latest",
                    ".",
                ],
                cwd=str(project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ) as process:
                stdout, stderr = process.communicate(timeout=300)
                if process.returncode != 0:
                    raise subprocess.CalledProcessError(
                        process.returncode, process.args, stdout, stderr
                    )
                result = type(
                    "CompletedProcess", (), {"returncode": 0, "stdout": stdout, "stderr": stderr}
                )

            # Clean up the temporary Containerfile
            if containerfile_test.exists():
                containerfile_test.unlink()
        else:
            # Use the standard build script
            result = None
            with subprocess.Popen(
                [str(build_script)],
                cwd=str(project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ) as process:
                stdout, stderr = process.communicate(timeout=300)
                if process.returncode != 0:
                    raise subprocess.CalledProcessError(
                        process.returncode, process.args, stdout, stderr
                    )
                result = type(
                    "CompletedProcess", (), {"returncode": 0, "stdout": stdout, "stderr": stderr}
                )

        return True, result
    except subprocess.CalledProcessError as e:
        return False, e
    except Exception as e:
        return False, e


@pytest.fixture(scope="session")
def docker_image(request):
    """
    Session-scoped fixture that ensures the Podman image is built once for all tests.

    If the test is marked with 'mock_sbctl', a test image with mock sbctl will be built.
    Otherwise, the standard image will be built.

    This is used by all e2e tests to avoid rebuilding the image for each test file.

    Args:
        request: The pytest request object

    Returns:
        The name of the Podman image
    """
    # Skip if Podman is not available
    if not is_docker_available():
        pytest.skip("Podman is not available")

    # Get project root directory
    project_root = Path(__file__).parents[1]

    # Determine if we should use mock sbctl based on markers
    use_mock_sbctl = request.node.get_closest_marker("mock_sbctl") is not None

    # Can also be controlled by environment variable for non-marker tests
    if os.environ.get("USE_MOCK_SBCTL", "").lower() in ("true", "1", "yes"):
        use_mock_sbctl = True

    # Print what we're doing
    if use_mock_sbctl:
        print("\nBuilding Podman image with mock sbctl for tests...")
    else:
        print("\nBuilding standard Podman image for tests...")

    # Build the Podman image
    success, result = build_container_image(project_root, use_mock_sbctl)

    if not success:
        if isinstance(result, str):
            pytest.skip(f"Failed to build Podman image: {result}")
        else:
            pytest.skip(f"Failed to build Podman image: {result.stderr}")

    # Yield to allow tests to run
    yield "mcp-server-troubleshoot:latest"

    # Explicitly clean up any running containers
    with subprocess.Popen(
        ["podman", "ps", "-q", "--filter", "ancestor=mcp-server-troubleshoot:latest"],
        stdout=subprocess.PIPE,
        text=True,
    ) as process:
        containers = process.communicate(timeout=10)[0].strip().split("\n")

    for container_id in containers:
        if container_id:
            try:
                with subprocess.Popen(
                    ["podman", "stop", container_id],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                ) as process:
                    process.communicate(timeout=10)
            except Exception:
                pass


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
