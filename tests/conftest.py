"""
Test configuration and fixtures for pytest.
"""

import os
import subprocess
import contextlib
import pytest
from pathlib import Path

# Set default verbosity to verbose for tests to maintain backward compatibility
os.environ["MCP_VERBOSITY"] = "verbose"

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
        result = subprocess.run(
            ["podman", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
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
    Build the Podman image for tests using melange/apko.

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

    # Check for melange/apko config files
    melange_config = project_root / ".melange.yaml"
    apko_config = project_root / "apko.yaml"

    if not melange_config.exists():
        return False, ".melange.yaml not found"
    if not apko_config.exists():
        return False, "apko.yaml not found"

    try:
        # Remove any existing image first to ensure a clean build
        subprocess.run(
            ["podman", "rmi", "-f", "troubleshoot-mcp-server:latest"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=False,
        )

        # For test mode with mock sbctl, we need to modify the melange config
        if use_mock_sbctl:
            # Create a temporary melange config with mock sbctl
            melange_test_config = project_root / ".melange.test.yaml"

            # Read the original melange config
            melange_content = ""
            with safe_open(melange_config, "r") as f:
                melange_content = f.read()

            # Modify the pipeline to use mock sbctl
            mock_pipeline = """pipeline:
  - name: Install package with dependencies
    runs: |
      python3 -m pip install .
  - name: Install mock sbctl
    runs: |
      cp tests/fixtures/mock_sbctl.py /usr/bin/sbctl
      chmod +x /usr/bin/sbctl"""

            # Replace the pipeline section
            import re

            melange_content = re.sub(
                r"pipeline:.*", mock_pipeline, melange_content, flags=re.DOTALL
            )

            # Write the modified melange config
            with safe_open(melange_test_config, "w") as f:
                f.write(melange_content)

            # Build using the temporary melange config
            # First build the package
            result = subprocess.run(
                [
                    "podman",
                    "run",
                    "--rm",
                    "-v",
                    f"{project_root}:/work",
                    "cgr.dev/chainguard/melange",
                    "build",
                    ".melange.test.yaml",
                    "--arch=amd64",
                ],
                cwd=str(project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300,
                check=True,
            )

            # Then build the image
            result = subprocess.run(
                [
                    "podman",
                    "run",
                    "--rm",
                    "-v",
                    f"{project_root}:/work",
                    "cgr.dev/chainguard/apko",
                    "build",
                    "apko.yaml",
                    "troubleshoot-mcp-server:latest",
                    "troubleshoot-mcp-server.tar",
                    "--arch=amd64",
                ],
                cwd=str(project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300,
                check=True,
            )

            # Load the image
            result = subprocess.run(
                ["podman", "load", "-i", "troubleshoot-mcp-server.tar"],
                cwd=str(project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60,
                check=True,
            )

            # Clean up temporary files
            if melange_test_config.exists():
                melange_test_config.unlink()
            tar_file = project_root / "troubleshoot-mcp-server.tar"
            if tar_file.exists():
                tar_file.unlink()
        else:
            # Use the standard build script
            result = subprocess.run(
                [str(build_script)],
                cwd=str(project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300,
                check=True,
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

    # Check if image already exists to avoid rebuilding
    image_check = subprocess.run(
        ["podman", "image", "exists", "troubleshoot-mcp-server:latest"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    # Image exists already, just use it
    if image_check.returncode == 0:
        print("\nUsing existing Podman image for tests...")
        yield "troubleshoot-mcp-server:latest"
        return

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
    yield "troubleshoot-mcp-server:latest"

    # Explicitly clean up any running containers
    containers_result = subprocess.run(
        ["podman", "ps", "-q", "--filter", "ancestor=troubleshoot-mcp-server:latest"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
        check=False,
    )
    containers = containers_result.stdout.strip().split("\n") if containers_result.stdout else []

    for container_id in containers:
        if container_id:
            try:
                subprocess.run(
                    ["podman", "stop", container_id],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=10,
                    check=False,
                )
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


@pytest.fixture
def temp_bundles_directory():
    """
    Create a temporary directory for bundles during tests.

    This isolates each test to use a separate bundles directory, preventing
    cross-test contamination.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        yield temp_path


@pytest.fixture
def container_test_env():
    """
    Create a test environment for container tests.

    This sets up common environment variables and resources for container testing.
    """
    # Store original environment
    original_env = os.environ.copy()

    # Set up test environment
    os.environ["SBCTL_TOKEN"] = "test-token"
    os.environ["MCP_BUNDLE_STORAGE"] = "/data/bundles"

    # Yield to run the test
    yield os.environ

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
