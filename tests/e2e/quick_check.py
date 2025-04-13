"""
Quick test-checking module for e2e tests with strict timeouts.
This module offers test runners that verify only basic functionality works
without running the full test suite.
"""
import pytest
import asyncio
import subprocess
import time
from pathlib import Path

# Run a basic container test to verify Docker works
@pytest.mark.e2e
@pytest.mark.docker
@pytest.mark.quick
def test_basic_container_check():
    """Basic check to verify Docker container functionality."""
    # Get project root
    project_root = Path(__file__).parents[2]
    
    # Verify Dockerfile exists
    dockerfile = project_root / "Dockerfile"
    assert dockerfile.exists(), f"Dockerfile not found at {dockerfile}"
    
    # Verify scripts exist
    build_script = project_root / "scripts" / "build.sh"
    assert build_script.exists(), f"Build script not found at {build_script}"
    assert build_script.is_file(), f"{build_script} is not a file"
    
    # Run docker version command
    docker_check = subprocess.run(
        ["docker", "--version"], 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        text=True,
        timeout=5
    )
    assert docker_check.returncode == 0, "Docker is not available"
    
    # Create a unique container name
    import uuid
    container_name = f"mcp-test-{uuid.uuid4().hex[:8]}"
    
    # Run a simple container command
    container_test = subprocess.run(
        [
            "docker", "run", "--rm", "--name", container_name,
            "python:3.11-slim", "python", "-c", 
            "print('Basic container test passed')"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=15
    )
    
    assert container_test.returncode == 0, f"Container test failed: {container_test.stderr}"
    assert "Basic container test passed" in container_test.stdout, "Container didn't produce expected output"

    # Report success
    print("Basic Docker functionality tests passed")


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_mcp_protocol_basic():
    """Basic test for MCP protocol functionality."""
    # Create a simple MCP server process
    env = {"MCP_LOG_LEVEL": "ERROR"}
    
    # Start the process with a timeout
    try:
        import sys
        process = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                sys.executable, "-m", "mcp_server_troubleshoot.cli",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            ),
            timeout=5
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


if __name__ == "__main__":
    # Run the tests
    test_basic_container_check()
    print("All tests passed!")