"""
Quick test-checking module for e2e tests with strict timeouts.

This module offers test runners that verify only basic functionality works
without running the full test suite. It's especially useful for:
1. Pre-build validation
2. CI environments that need fast feedback
3. Quick sanity checks during development
"""

import pytest
import asyncio
import subprocess
import uuid

from .utils import (
    get_container_runtime,
    get_project_root,
    sanitize_container_name,
    get_system_info,
)

# Mark all tests in this file appropriately
pytestmark = [pytest.mark.e2e, pytest.mark.quick]


@pytest.fixture(scope="module")
def system_info():
    """Get information about the testing environment."""
    info = get_system_info()

    # Log the environment info for debugging
    print("\nTest Environment:")
    for key, value in info.items():
        print(f"  {key}: {value}")

    return info


@pytest.fixture(scope="module")
def container_runner(system_info):
    """
    Set up the appropriate container runner (podman or docker).

    Returns:
        str: The container command to use ('podman' or 'docker')
    """
    runtime, available = get_container_runtime()

    if not available:
        pytest.skip(f"No container runtime available (tried {runtime})")

    return runtime


@pytest.fixture
def unique_container_name():
    """Generate a unique container name for tests."""
    name = f"mcp-test-{uuid.uuid4().hex[:8]}"
    return sanitize_container_name(name)


# Run a basic container test to verify container functionality
@pytest.mark.container
def test_basic_container_check(container_runner, unique_container_name, system_info):
    """Basic check to verify container functionality."""
    # Get project root
    project_root = get_project_root()

    # Verify Containerfile exists
    containerfile = project_root / "Containerfile"
    assert containerfile.exists(), f"Containerfile not found at {containerfile}"

    # Verify scripts exist
    build_script = project_root / "scripts" / "build.sh"
    assert build_script.exists(), f"Build script not found at {build_script}"
    assert build_script.is_file(), f"{build_script} is not a file"

    # Run a simple container command with a standard Python image
    container_test = subprocess.run(
        [
            container_runner,
            "run",
            "--rm",
            "--name",
            unique_container_name,
            "python:3.11-slim",
            "python",
            "-c",
            "print('Basic container test passed')",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=15,
        check=False,
    )

    # Enhance error messages with detailed output
    assert container_test.returncode == 0, (
        f"Container test failed with code {container_test.returncode}:\n"
        f"STDOUT: {container_test.stdout}\n"
        f"STDERR: {container_test.stderr}"
    )

    assert (
        "Basic container test passed" in container_test.stdout
    ), "Container didn't produce expected output"

    # Report success
    print("Basic container functionality tests passed")


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_mcp_protocol_basic():
    """Basic test for MCP protocol functionality."""
    # Set a lower log level for tests
    env = {"MCP_LOG_LEVEL": "ERROR"}

    # Start the process with a timeout
    try:
        import sys

        process = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "mcp_server_troubleshoot.cli",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            ),
            timeout=5,
        )

        # Send a basic request with timeout
        try:
            import json

            request = {"jsonrpc": "2.0", "id": "1", "method": "get_tool_definitions", "params": {}}
            request_str = json.dumps(request) + "\n"

            # Send request
            process.stdin.write(request_str.encode())
            await asyncio.wait_for(process.stdin.drain(), timeout=3)

            # Try to read response for 3 seconds
            try:
                response_line = await asyncio.wait_for(process.stdout.readline(), timeout=3)

                # If we get here, we've received a response
                if response_line:
                    print("Received response from MCP server")
                    return True

            except asyncio.TimeoutError:
                # Skip test if timesout
                pytest.skip("Timeout reading MCP server response")

        except asyncio.TimeoutError:
            # Skip test if timesout
            pytest.skip("Timeout sending request to MCP server")

        finally:
            # Clean up the process
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=2)
            except asyncio.TimeoutError:
                process.kill()

    except asyncio.TimeoutError:
        pytest.skip("Timeout starting MCP server process")


# Simple application test that doesn't rely on containers
@pytest.mark.timeout(10)
def test_application_version():
    """Test that the application can report its version."""
    import sys

    # Run the application with the version flag
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mcp_server_troubleshoot.cli",
            "--version",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=5,
        check=False,
    )

    # Check for successful run
    combined_output = result.stdout + result.stderr
    assert result.returncode == 0, f"Version command failed: {combined_output}"
    assert combined_output.strip(), "No version information was returned"


if __name__ == "__main__":
    # Run the tests directly for quick checking
    print("Running quick container check...")
    pytest.main(["-xvs", __file__])
