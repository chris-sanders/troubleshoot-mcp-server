"""
Tests for the Docker build and run processes.
"""

import os
import subprocess
import tempfile
from pathlib import Path
import pytest


def run_command(cmd, cwd=None, check=True):
    """Run a command and return its output."""
    try:
        result = subprocess.run(
            cmd, shell=True, check=check, cwd=cwd, text=True, 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}")
        print(f"Command: {cmd}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        raise


def test_dockerfile_exists():
    """Test that the Dockerfile exists in the project directory."""
    project_dir = Path(__file__).parents[1]
    dockerfile_path = project_dir / "Dockerfile"
    assert dockerfile_path.exists(), "Dockerfile does not exist"


def test_dockerignore_exists():
    """Test that the .dockerignore file exists in the project directory."""
    project_dir = Path(__file__).parents[1]
    dockerignore_path = project_dir / ".dockerignore"
    assert dockerignore_path.exists(), ".dockerignore does not exist"


def test_build_script_exists_and_executable():
    """Test that the build script exists and is executable."""
    project_dir = Path(__file__).parents[1]
    build_script = project_dir / "build.sh"
    assert build_script.exists(), "build.sh does not exist"
    assert os.access(build_script, os.X_OK), "build.sh is not executable"


def test_run_script_exists_and_executable():
    """Test that the run script exists and is executable."""
    project_dir = Path(__file__).parents[1]
    run_script = project_dir / "run.sh"
    assert run_script.exists(), "run.sh does not exist"
    assert os.access(run_script, os.X_OK), "run.sh is not executable"


@pytest.mark.docker
def test_docker_build():
    """Test that the Docker image builds successfully."""
    project_dir = Path(__file__).parents[1]
    
    # Use a unique tag for testing
    test_tag = "mcp-server-troubleshoot:test"
    
    try:
        # First, verify Dockerfile exists
        dockerfile_path = project_dir / "Dockerfile"
        assert dockerfile_path.exists(), "Dockerfile not found"
        
        # Print Dockerfile content for debugging
        print(f"\nDockerfile content:\n{dockerfile_path.read_text()}\n")
        
        # Build the image with progress output
        print("\nBuilding Docker image...")
        output = run_command(
            f"docker build --progress=plain -t {test_tag} .", 
            cwd=str(project_dir)
        )
        print(f"\nBuild output:\n{output}\n")
        
        # Check if the image exists
        images = run_command("docker images", check=False)
        print(f"\nDocker images:\n{images}\n")
        
        assert test_tag.split(":")[0] in images, "Built image not found"
        
    except Exception as e:
        print(f"Docker build test failed: {str(e)}")
        raise
        
    finally:
        # Clean up
        try:
            run_command(f"docker rmi {test_tag}", check=False)
            print(f"\nRemoved test image {test_tag}")
        except subprocess.CalledProcessError:
            print(f"\nFailed to remove test image {test_tag}")
            pass  # Ignore errors during cleanup


@pytest.mark.docker
def test_docker_run():
    """Test that the Docker container runs and exits successfully."""
    project_dir = Path(__file__).parents[1]
    
    # Use a unique tag for testing
    test_tag = "mcp-server-troubleshoot:test-run"
    
    try:
        # Build the image
        run_command(
            f"docker build -t {test_tag} .", cwd=str(project_dir)
        )
        
        # Create a temporary directory for the bundle
        with tempfile.TemporaryDirectory() as temp_dir:
            # Run the container with --help to get quick exit
            output = run_command(
                f"docker run --rm -v {temp_dir}:/data/bundles {test_tag} --help",
                cwd=str(project_dir)
            )
            
            # Verify output contains help message
            assert "usage:" in output.lower(), "Container did not run correctly"
            assert "bundle" in output.lower(), "Container output incorrect"
            
            # Test the bundle volume is correctly mounted
            volume_test = run_command(
                f"docker run --rm --entrypoint sh {test_tag} -c 'ls -la /data'",
                cwd=str(project_dir)
            )
            assert "bundles" in volume_test.lower(), "Volume mount point not found"
        
    finally:
        # Clean up
        try:
            run_command(f"docker rmi {test_tag}", check=False)
        except subprocess.CalledProcessError:
            pass  # Ignore errors during cleanup


@pytest.mark.docker
def test_sbctl_installed():
    """Test that sbctl is installed in the container."""
    project_dir = Path(__file__).parents[1]
    
    # Use a unique tag for testing
    test_tag = "mcp-server-troubleshoot:test-sbctl"
    
    try:
        # Build the image
        run_command(
            f"docker build -t {test_tag} .", cwd=str(project_dir)
        )
        
        # Run the container and check if sbctl is installed
        # Use 'sh -c' to run a shell command instead of entrypoint
        output = run_command(
            f"docker run --rm --entrypoint sh {test_tag} -c 'ls -la /usr/local/bin/sbctl'",
            cwd=str(project_dir), check=False
        )
        
        # Check output shows sbctl exists
        assert "sbctl" in output.lower(), "sbctl not properly installed in container"
            
    finally:
        # Clean up
        try:
            run_command(f"docker rmi {test_tag}", check=False)
        except subprocess.CalledProcessError:
            pass  # Ignore errors during cleanup


@pytest.mark.docker
def test_kubectl_installed():
    """Test that kubectl is installed in the container."""
    project_dir = Path(__file__).parents[1]
    
    # Use a unique tag for testing
    test_tag = "mcp-server-troubleshoot:test-kubectl"
    
    try:
        # Build the image
        run_command(
            f"docker build -t {test_tag} .", cwd=str(project_dir)
        )
        
        # Run the container and check if kubectl is installed
        # Use 'sh -c' to run a shell command instead of entrypoint
        output = run_command(
            f"docker run --rm --entrypoint sh {test_tag} -c 'ls -la /usr/local/bin/kubectl'",
            cwd=str(project_dir), check=False
        )
        
        # Check output shows kubectl exists
        assert "kubectl" in output.lower(), "kubectl not properly installed in container"
            
    finally:
        # Clean up
        try:
            run_command(f"docker rmi {test_tag}", check=False)
        except subprocess.CalledProcessError:
            pass  # Ignore errors during cleanup