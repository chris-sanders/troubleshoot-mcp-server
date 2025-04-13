"""
Test configuration and fixtures for pytest.
"""

import os
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


def build_docker_image(project_root, use_mock_sbctl=False):
    """
    Build the Docker image for tests.
    
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
        subprocess.run(
            ["docker", "rmi", "-f", "mcp-server-troubleshoot:latest"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        
        # For test mode with mock sbctl, we need to modify the Dockerfile
        if use_mock_sbctl:
            # Create a temporary Dockerfile.test
            dockerfile = project_root / "Dockerfile"
            if not dockerfile.exists():
                return False, "Dockerfile not found"
                
            # Read the original Dockerfile
            with open(dockerfile, "r") as f:
                dockerfile_content = f.read()
            
            # Create a modified version that uses mock_sbctl.py
            dockerfile_test = project_root / "Dockerfile.test"
            
            # Replace the sbctl installation section with the mock version
            mock_sbctl_section = """
# Use mock sbctl script instead of the real one
COPY tests/fixtures/mock_sbctl.py /usr/local/bin/sbctl
RUN chmod +x /usr/local/bin/sbctl
"""
            # Find the right section to replace
            if "Install the real sbctl binary" in dockerfile_content:
                # Replace the real sbctl installation with the mock one
                dockerfile_content = dockerfile_content.replace(
                    "# Install the real sbctl binary - AMD64 version for standard container usage\nRUN mkdir -p /tmp/sbctl && cd /tmp/sbctl && \\\n    curl -L -o sbctl.tar.gz \"https://github.com/replicatedhq/sbctl/releases/latest/download/sbctl_linux_amd64.tar.gz\" && \\\n    tar xzf sbctl.tar.gz && \\\n    chmod +x sbctl && \\\n    mv sbctl /usr/local/bin/ && \\\n    cd / && \\\n    rm -rf /tmp/sbctl && \\\n    sbctl --help",
                    mock_sbctl_section
                )
            else:
                # If we can't find the exact section, just add it before creating the data directory
                dockerfile_content = dockerfile_content.replace(
                    "# Create data directory for bundles", 
                    mock_sbctl_section + "\n# Create data directory for bundles"
                )
                
            # Write the modified Dockerfile
            with open(dockerfile_test, "w") as f:
                f.write(dockerfile_content)
                
            # Build using the temporary Dockerfile
            result = subprocess.run(
                ["docker", "build", "-f", "Dockerfile.test", "-t", "mcp-server-troubleshoot:latest", "."],
                check=True,
                cwd=str(project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            
            # Clean up the temporary Dockerfile
            dockerfile_test.unlink()
        else:
            # Use the standard build script
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
def docker_image(request):
    """
    Session-scoped fixture that ensures the Docker image is built once for all tests.
    
    If the test is marked with 'mock_sbctl', a test image with mock sbctl will be built.
    Otherwise, the standard image will be built.

    This is used by all e2e tests to avoid rebuilding the image for each test file.
    
    Args:
        request: The pytest request object
        
    Returns:
        The name of the Docker image
    """
    # Skip if Docker is not available
    if not is_docker_available():
        pytest.skip("Docker is not available")

    # Get project root directory
    project_root = Path(__file__).parents[1]
    
    # Determine if we should use mock sbctl based on markers
    use_mock_sbctl = request.node.get_closest_marker("mock_sbctl") is not None
    
    # Can also be controlled by environment variable for non-marker tests
    if os.environ.get("USE_MOCK_SBCTL", "").lower() in ("true", "1", "yes"):
        use_mock_sbctl = True
        
    # Print what we're doing
    if use_mock_sbctl:
        print("\nBuilding Docker image with mock sbctl for tests...")
    else:
        print("\nBuilding standard Docker image for tests...")
        
    # Build the Docker image
    success, result = build_docker_image(project_root, use_mock_sbctl)

    if not success:
        if isinstance(result, str):
            pytest.skip(f"Failed to build Docker image: {result}")
        else:
            pytest.skip(f"Failed to build Docker image: {result.stderr}")

    # Yield to allow tests to run
    yield "mcp-server-troubleshoot:latest"
    
    # Cleanup is not included here as this fixture has session scope
    # The image will be cleaned up when pytest exits
    # If specific test cases need cleanup, they should handle it themselves


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
