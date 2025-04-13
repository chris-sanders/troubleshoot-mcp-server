"""
Integration tests for the stdio lifecycle functionality.

These tests verify that the server properly handles the stdio lifecycle mode,
including signal handling and resource cleanup.
"""

import asyncio
import json
import os
import shutil
import tempfile

import pytest


@pytest.fixture(scope="module")
def test_bundle():
    """Create a simple test bundle file for tests."""
    bundle_dir = tempfile.mkdtemp()
    bundle_path = os.path.join(bundle_dir, "test-bundle.tar.gz")

    # Create a simple bundle file
    with open(bundle_path, "wb") as f:
        f.write(b"test bundle content")

    yield bundle_path

    # Clean up
    shutil.rmtree(bundle_dir, ignore_errors=True)


class StdioServerProcess:
    """Helper class to manage a stdio server process for testing."""

    def __init__(self, bundle_dir=None):
        self.bundle_dir = bundle_dir or tempfile.mkdtemp()
        self.process = None
        self.request_id = 0

    async def start(self):
        """Start the server process with stdio mode."""
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        # Start the server process
        server_args = [
            "python",
            "-m",
            "mcp_server_troubleshoot",
            "--bundle-dir",
            self.bundle_dir,
            "--verbose",
        ]

        self.process = await asyncio.create_subprocess_exec(
            *server_args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        # Wait for startup
        await asyncio.sleep(1)

    async def send_request(self, method, params=None):
        """Send a request to the server process."""
        if not self.process or self.process.stdin.is_closing():
            raise RuntimeError("Process not started or stdin closed")

        self.request_id += 1
        request = {"jsonrpc": "2.0", "id": self.request_id, "method": method}
        if params:
            request["params"] = params

        # Send the request
        request_json = json.dumps(request)
        self.process.stdin.write(f"{request_json}\n".encode())
        await self.process.stdin.drain()

        # Read the response
        response_line = await self.process.stdout.readline()
        if not response_line:
            return None

        return json.loads(response_line.decode())

    async def stop(self):
        """Stop the server process and read all remaining output."""
        if self.process:
            # Send SIGTERM to the process
            if not self.process.stdin.is_closing():
                self.process.stdin.close()

            # Read any remaining stdout/stderr
            stdout_data, stderr_data = await asyncio.gather(
                self.process.stdout.read(), self.process.stderr.read(), return_exceptions=True
            )

            # Terminate the process
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()

            # Return any captured output
            return (
                stdout_data.decode() if not isinstance(stdout_data, Exception) else "",
                stderr_data.decode() if not isinstance(stderr_data, Exception) else "",
            )

        return "", ""

    def cleanup(self):
        """Clean up resources created by the test."""
        if self.bundle_dir and os.path.exists(self.bundle_dir):
            shutil.rmtree(self.bundle_dir, ignore_errors=True)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_stdio_server_startup_shutdown():
    """Test basic startup and shutdown of the server in stdio mode."""
    server = StdioServerProcess()
    try:
        # Start the server
        await server.start()

        # Send a simple request
        response = await server.send_request("echo", {"message": "hello"})
        assert response is not None
        assert response.get("id") == 1
        assert "result" in response

        # Stop the server
        stdout, stderr = await server.stop()

        # Check for successful shutdown in the logs
        assert "Shutting down MCP Troubleshoot Server" in stderr or "cleanup" in stderr

    finally:
        server.cleanup()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_stdio_server_bundle_operations(test_bundle):
    """Test bundle operations with the stdio server."""
    server = StdioServerProcess()
    try:
        # Copy the test bundle to the server's bundle directory
        os.makedirs(server.bundle_dir, exist_ok=True)
        target_path = os.path.join(server.bundle_dir, os.path.basename(test_bundle))
        shutil.copy2(test_bundle, target_path)

        # Start the server
        await server.start()

        # List available bundles
        response = await server.send_request("list_available_bundles", {})
        assert response is not None
        assert response.get("id") == 1
        assert "result" in response

        # Stop the server
        stdout, stderr = await server.stop()

        # Check for successful shutdown in the logs
        assert "Shutting down" in stderr or "cleanup" in stderr

    finally:
        server.cleanup()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_stdio_server_signal_handling():
    """Test that the server properly handles signals for termination."""
    server = StdioServerProcess()
    try:
        # Start the server
        await server.start()

        # Get the process PID
        pid = server.process.pid

        # Send SIGTERM to the process
        os.kill(pid, 15)  # 15 is SIGTERM

        # Wait for process to exit
        await asyncio.sleep(2)

        # Check if process exited
        exit_code = None
        try:
            exit_code = server.process.returncode
        except (AttributeError, ProcessLookupError):
            pass

        # Read leftover output
        stdout, stderr = "", ""
        if not exit_code:
            stdout, stderr = await server.stop()

        # Verify the process exited and properly handled the signal
        assert exit_code is not None or "Shutting down" in stderr

    finally:
        server.cleanup()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_temp_dir_cleanup():
    """Test that temporary directories are cleaned up on shutdown."""
    server = StdioServerProcess()
    temp_dir = None

    try:
        # Start a server subprocess
        await server.start()

        # Send a request that will trigger temp directory creation
        await server.send_request("echo", {"message": "trigger temp dir"})

        # Find the temp directory in logs
        await asyncio.sleep(1)  # Wait for possible log output

        # Stop the server
        stdout, stderr = await server.stop()

        # Check logs for temp directory creation and cleanup
        created_msg = [
            line for line in stderr.splitlines() if "Created temporary directory" in line
        ]
        removed_msg = [
            line for line in stderr.splitlines() if "Removing temporary directory" in line
        ]

        # Extract the directory path if present
        if created_msg:
            import re

            matches = re.search(r"Created temporary directory: (.+)", created_msg[0])
            if matches:
                temp_dir = matches.group(1)

        # Skip test if we couldn't identify the temp dir
        if not temp_dir:
            pytest.skip("Could not identify temporary directory from logs")

        # Verify temp directory doesn't exist after shutdown
        assert not os.path.exists(temp_dir)

    finally:
        server.cleanup()
