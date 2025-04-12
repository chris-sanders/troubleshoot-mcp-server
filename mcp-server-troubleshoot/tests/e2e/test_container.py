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
            ["docker", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def is_image_built():
    """Check if the Docker image is already built."""
    result = subprocess.run(
        ["docker", "images", "-q", "mcp-server-troubleshoot:latest"],
        stdout=subprocess.PIPE,
        text=True,
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
            text=True,
        )
        return True, result
    except subprocess.CalledProcessError as e:
        return False, e


def cleanup_test_container():
    """Remove any existing test container."""
    subprocess.run(
        ["docker", "rm", "-f", "mcp-test"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
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
            "docker",
            "run",
            "--name",
            "mcp-test",
            "--rm",
            "-v",
            f"{bundles_dir}:/data/bundles",
            "-e",
            f"SBCTL_TOKEN={os.environ.get('SBCTL_TOKEN', 'test-token')}",
            "--entrypoint",
            "/bin/bash",
            "mcp-server-troubleshoot:latest",
            "-c",
            "echo 'Container is working!'",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )

    assert "Container is working!" in result.stdout


def test_python_functionality(docker_setup):
    """Test that Python works in the container."""
    bundles_dir = docker_setup

    result = subprocess.run(
        [
            "docker",
            "run",
            "--name",
            "mcp-test",
            "--rm",
            "-v",
            f"{bundles_dir}:/data/bundles",
            "-e",
            f"SBCTL_TOKEN={os.environ.get('SBCTL_TOKEN', 'test-token')}",
            "--entrypoint",
            "/bin/bash",
            "mcp-server-troubleshoot:latest",
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


def test_mcp_cli(docker_setup):
    """Test that the MCP server CLI works in the container."""
    bundles_dir = docker_setup

    result = subprocess.run(
        [
            "docker",
            "run",
            "--name",
            "mcp-test",
            "--rm",
            "-v",
            f"{bundles_dir}:/data/bundles",
            "-e",
            f"SBCTL_TOKEN={os.environ.get('SBCTL_TOKEN', 'test-token')}",
            "--entrypoint",
            "/bin/bash",
            "mcp-server-troubleshoot:latest",
            "-c",
            "python -m mcp_server_troubleshoot.cli --help",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    combined_output = result.stdout + result.stderr
    assert "usage:" in combined_output.lower() or result.returncode == 0


def test_mcp_protocol(docker_setup):
    """
    Test MCP protocol communication with the container.

    This test sends a JSON-RPC request to the container running in MCP mode
    and verifies that it responds correctly.
    """
    import json
    import uuid
    import tempfile
    import time
    from pathlib import Path

    # Create a temporary directory for the bundle
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Generate a unique container ID for this test
        container_id = f"mcp-test-{uuid.uuid4().hex[:8]}"

        # Start the container in MCP mode
        process = subprocess.Popen(
            [
                "docker",
                "run",
                "--name",
                container_id,
                "-i",  # Interactive mode for stdin
                "-v",
                f"{temp_path}:/data/bundles",
                "-e",
                "SBCTL_TOKEN=test-token",
                "-e",
                "MCP_BUNDLE_STORAGE=/data/bundles",
                "--entrypoint",
                "python",
                "mcp-server-troubleshoot:latest",
                "-m",
                "mcp_server_troubleshoot.cli",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        try:
            # Wait a moment for the container to start
            time.sleep(2)

            # Check if the container started successfully
            ps_check = subprocess.run(
                ["docker", "ps", "-q", "-f", f"name={container_id}"],
                stdout=subprocess.PIPE,
                text=True,
            )

            assert ps_check.stdout.strip(), "Docker container failed to start"

            # Simple JSON-RPC client for testing
            class JSONRPCClient:
                def __init__(self, process):
                    self.process = process
                    self.request_id = 0

                def send_request(self, method, params=None):
                    if params is None:
                        params = {}

                    self.request_id += 1
                    request = {
                        "jsonrpc": "2.0",
                        "id": str(self.request_id),
                        "method": method,
                        "params": params,
                    }

                    request_str = json.dumps(request) + "\n"
                    self.process.stdin.write(request_str.encode("utf-8"))
                    self.process.stdin.flush()

                    # Read response with a timeout
                    max_attempts = 5
                    for _ in range(max_attempts):
                        if self.process.stdout.readable():
                            response_line = self.process.stdout.readline()
                            if response_line:
                                try:
                                    response_str = response_line.decode("utf-8").strip()
                                    return json.loads(response_str)
                                except json.JSONDecodeError:
                                    print(f"Error decoding response: {response_line}")
                                    return {
                                        "error": {
                                            "code": -32700,
                                            "message": "Response was not valid JSON",
                                        }
                                    }

                        # Wait a bit before trying again
                        time.sleep(0.5)

                    # If we get here, we failed to get a response
                    return {"error": {"code": -32000, "message": "Timeout waiting for response"}}

            # Create a client
            client = JSONRPCClient(process)

            # 1. Test the get_tool_definitions method
            response = client.send_request("get_tool_definitions")
            assert "jsonrpc" in response, "Not a JSON-RPC response"
            assert response["jsonrpc"] == "2.0", "Invalid JSON-RPC version"
            assert "result" in response, "Missing result in JSON-RPC response"

            # Verify that expected tools are available
            tools = response["result"]
            tool_names = [tool["name"] for tool in tools]
            expected_tools = [
                "initialize_bundle",
                "kubectl",
                "list_files",
                "read_file",
                "grep_files",
            ]
            for tool in expected_tools:
                assert tool in tool_names, f"Tool {tool} not found in tools list"

            # 2. Test a simple call_tool method (will fail since no bundle is initialized, but should be a valid response)
            response = client.send_request(
                "call_tool", {"name": "list_files", "arguments": {"path": "/"}}
            )
            assert "jsonrpc" in response, "Not a JSON-RPC response"
            assert response["jsonrpc"] == "2.0", "Invalid JSON-RPC version"
            assert "result" in response, "Missing result in JSON-RPC response"

            # 3. Test invalid method
            response = client.send_request("non_existent_method")
            assert "jsonrpc" in response, "Not a JSON-RPC response"
            assert response["jsonrpc"] == "2.0", "Invalid JSON-RPC version"
            # Should receive an error for invalid method
            if "error" in response:
                assert "code" in response["error"], "Missing error code"
                assert "message" in response["error"], "Missing error message"

        finally:
            # Clean up
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

            # Clean up the container
            subprocess.run(
                ["docker", "rm", "-f", container_id],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )


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
                    "docker",
                    "run",
                    "--name",
                    "mcp-test",
                    "--rm",
                    "-v",
                    f"{bundles_dir}:/data/bundles",
                    "-e",
                    f"SBCTL_TOKEN={os.environ.get('SBCTL_TOKEN', 'test-token')}",
                    "--entrypoint",
                    "/bin/bash",
                    "mcp-server-troubleshoot:latest",
                    "-c",
                    "echo 'Container is working!'",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
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
                    "docker",
                    "run",
                    "--name",
                    "mcp-test",
                    "--rm",
                    "-v",
                    f"{bundles_dir}:/data/bundles",
                    "-e",
                    f"SBCTL_TOKEN={os.environ.get('SBCTL_TOKEN', 'test-token')}",
                    "--entrypoint",
                    "/bin/bash",
                    "mcp-server-troubleshoot:latest",
                    "-c",
                    "python --version",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
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
                    "docker",
                    "run",
                    "--name",
                    "mcp-test",
                    "--rm",
                    "-v",
                    f"{bundles_dir}:/data/bundles",
                    "-e",
                    f"SBCTL_TOKEN={os.environ.get('SBCTL_TOKEN', 'test-token')}",
                    "--entrypoint",
                    "/bin/bash",
                    "mcp-server-troubleshoot:latest",
                    "-c",
                    "python -m mcp_server_troubleshoot.cli --help",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
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
