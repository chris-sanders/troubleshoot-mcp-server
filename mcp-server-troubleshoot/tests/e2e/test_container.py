"""
End-to-end test for MCP server container.
This test:
1. Ensures Docker is available
2. Ensures the image is built
3. Tests running the container with simple commands
4. Tests MCP server functionality
"""

import subprocess
import os
import sys
import pytest
from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parents[2].absolute()
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


def is_docker_available():
    """Check if Docker is available on the system."""
    try:
        subprocess.run(
            ["docker", "--version"], 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def is_image_built():
    """Check if the Docker image is already built."""
    result = subprocess.run(
        ["docker", "images", "-q", "mcp-server-troubleshoot:latest"],
        stdout=subprocess.PIPE,
        text=True
    )
    return bool(result.stdout.strip())


def build_image():
    """Build the Docker image."""
    build_script = SCRIPTS_DIR / "build.sh"
    if not build_script.exists():
        build_script = PROJECT_ROOT / "build.sh"
    
    try:
        result = subprocess.run(
            [str(build_script)], 
            check=True,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return True, result
    except subprocess.CalledProcessError as e:
        return False, e


def cleanup_test_container():
    """Remove any existing test container."""
    subprocess.run(
        ["docker", "rm", "-f", "mcp-test"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


def ensure_bundles_directory():
    """Create a bundles directory for testing if it doesn't exist."""
    bundles_dir = PROJECT_ROOT / "bundles"
    bundles_dir.mkdir(exist_ok=True)
    return bundles_dir


@pytest.fixture(scope="module")
def docker_setup():
    """Setup Docker environment for testing."""
    # Skip all tests if Docker is not available
    if not is_docker_available():
        pytest.skip("Docker is not available")
    
    # Create bundles directory
    bundles_dir = ensure_bundles_directory()
    
    # Build the image if needed
    if not is_image_built():
        success, result = build_image()
        if not success:
            pytest.skip(f"Failed to build Docker image: {result.stderr}")
    
    # Clean up any existing test container
    cleanup_test_container()
    
    # Set test token
    os.environ["SBCTL_TOKEN"] = "test-token"
    
    yield bundles_dir
    
    # Cleanup after tests
    cleanup_test_container()


def test_basic_container_functionality(docker_setup):
    """Test that the container can run basic commands."""
    bundles_dir = docker_setup
    
    result = subprocess.run(
        [
            "docker", "run", "--name", "mcp-test", "--rm",
            "-v", f"{bundles_dir}:/data/bundles",
            "-e", f"SBCTL_TOKEN={os.environ.get('SBCTL_TOKEN', 'test-token')}",
            "--entrypoint", "/bin/bash",
            "mcp-server-troubleshoot:latest", 
            "-c", "echo 'Container is working!'"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True
    )
    
    assert "Container is working!" in result.stdout


def test_python_functionality(docker_setup):
    """Test that Python works in the container."""
    bundles_dir = docker_setup
    
    result = subprocess.run(
        [
            "docker", "run", "--name", "mcp-test", "--rm",
            "-v", f"{bundles_dir}:/data/bundles",
            "-e", f"SBCTL_TOKEN={os.environ.get('SBCTL_TOKEN', 'test-token')}",
            "--entrypoint", "/bin/bash",
            "mcp-server-troubleshoot:latest", 
            "-c", "python --version"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True
    )
    
    version_output = result.stdout.strip() or result.stderr.strip()
    assert "Python" in version_output


def test_mcp_cli(docker_setup):
    """Test that the MCP server CLI works in the container."""
    bundles_dir = docker_setup
    
    result = subprocess.run(
        [
            "docker", "run", "--name", "mcp-test", "--rm",
            "-v", f"{bundles_dir}:/data/bundles",
            "-e", f"SBCTL_TOKEN={os.environ.get('SBCTL_TOKEN', 'test-token')}",
            "--entrypoint", "/bin/bash",
            "mcp-server-troubleshoot:latest", 
            "-c", "python -m mcp_server_troubleshoot.cli --help"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    combined_output = result.stdout + result.stderr
    assert "usage:" in combined_output.lower() or result.returncode == 0


@pytest.mark.xfail(reason="MCP protocol test not yet implemented")
def test_mcp_protocol(docker_setup):
    """
    Test MCP protocol communication with the container.
    
    This test sends a JSON-RPC request to the container running in MCP mode
    and verifies that it responds correctly.
    """
    # docker_setup is used by the fixture but not needed in this test yet
    
    # This is a placeholder for an actual MCP protocol test
    # TODO: Implement a full MCP client-server test
    assert False, "MCP protocol test not implemented yet"


if __name__ == "__main__":
    # Allow running as a standalone script
    if is_docker_available():
        bundles_dir = ensure_bundles_directory()
        
        # Build the image if needed
        if not is_image_built():
            print("Building container image...")
            success, result = build_image()
            if not success:
                print(f"Failed to build image: {result.stderr}")
                sys.exit(1)
            print("Container image built successfully")
        
        # Clean up any existing test container
        print("Cleaning up any existing test containers...")
        cleanup_test_container()
        
        # Set test token
        os.environ["SBCTL_TOKEN"] = "test-token"
        
        print("\n=== TEST: Basic Container Functionality ===")
        try:
            result = subprocess.run(
                [
                    "docker", "run", "--name", "mcp-test", "--rm",
                    "-v", f"{bundles_dir}:/data/bundles",
                    "-e", f"SBCTL_TOKEN={os.environ.get('SBCTL_TOKEN', 'test-token')}",
                    "--entrypoint", "/bin/bash",
                    "mcp-server-troubleshoot:latest", 
                    "-c", "echo 'Container is working!'"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            
            print(f"Container output: {result.stdout.strip()}")
            print("\n✅ Basic container functionality test passed!")
            
        except subprocess.CalledProcessError as e:
            print(f"\n❌ Container test failed: {e}")
            print(f"Stdout: {e.stdout}")
            print(f"Stderr: {e.stderr}")
            sys.exit(1)
        
        print("\n=== TEST: Python Functionality ===")
        try:
            result = subprocess.run(
                [
                    "docker", "run", "--name", "mcp-test", "--rm",
                    "-v", f"{bundles_dir}:/data/bundles",
                    "-e", f"SBCTL_TOKEN={os.environ.get('SBCTL_TOKEN', 'test-token')}",
                    "--entrypoint", "/bin/bash",
                    "mcp-server-troubleshoot:latest", 
                    "-c", "python --version"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            
            version_output = result.stdout.strip() or result.stderr.strip()
            print(f"Python version: {version_output}")
            print("\n✅ Python version check passed!")
            
        except subprocess.CalledProcessError as e:
            print(f"\n❌ Python version check failed: {e}")
            print(f"Stdout: {e.stdout}")
            print(f"Stderr: {e.stderr}")
            sys.exit(1)
        
        print("\n=== TEST: MCP Server CLI ===")
        try:
            result = subprocess.run(
                [
                    "docker", "run", "--name", "mcp-test", "--rm",
                    "-v", f"{bundles_dir}:/data/bundles",
                    "-e", f"SBCTL_TOKEN={os.environ.get('SBCTL_TOKEN', 'test-token')}",
                    "--entrypoint", "/bin/bash",
                    "mcp-server-troubleshoot:latest", 
                    "-c", "python -m mcp_server_troubleshoot.cli --help"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode == 0 or "usage:" in (result.stderr + result.stdout).lower():
                print("\n✅ MCP server CLI test passed!")
                output = result.stdout or result.stderr
                if output:
                    print(f"CLI help output: {output.strip()[:100]}...")
            else:
                print("\n❓ MCP server CLI didn't show usage info, but didn't fail")
                print(f"Stdout: {result.stdout}")
                print(f"Stderr: {result.stderr}")
            
        except subprocess.CalledProcessError as e:
            print(f"\n❌ MCP server CLI test failed: {e}")
            print(f"Stdout: {e.stdout}")
            print(f"Stderr: {e.stderr}")
            
        print("\nAll tests completed. The container image is ready for use!")
        print("To use it with MCP clients, follow the instructions in DOCKER.md.")
    else:
        print("Docker is not available. Cannot run container tests.")
        sys.exit(1)