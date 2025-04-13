#!/usr/bin/env python3
"""
Simple MCP client for testing.

This script starts an MCP server and communicates with it via stdin/stdout.
It's a simplified version of the test suite that can be run directly for
quick testing during development.

Usage:
  python mcp_client_test.py
"""

# Set up logging
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("mcp_client_test")

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Path to the fixtures directory containing test bundles
FIXTURES_DIR = Path(__file__).parents[1] / "fixtures"
TEST_BUNDLE = FIXTURES_DIR / "support-bundle-2025-04-11T14_05_31.tar.gz"


class MCPClient:
    """Client for communicating with the MCP server."""

    def __init__(self, process):
        """Initialize with a subprocess connected to an MCP server."""
        self.process = process
        self.request_id = 0
        self.logger = logging.getLogger("mcp_client_test.client")
        self.logger.debug("MCP client initialized")

    def send_request(self, method, params=None):
        """Send a JSON-RPC request to the server."""
        if params is None:
            params = {}

        self.request_id += 1
        request = {"jsonrpc": "2.0", "id": str(self.request_id), "method": method, "params": params}

        self.logger.info(f"Sending request: {json.dumps(request)}")
        request_str = json.dumps(request) + "\n"

        try:
            self.process.stdin.write(request_str.encode("utf-8"))
            self.process.stdin.flush()
            self.logger.debug("Request sent and flushed")
        except BrokenPipeError as e:
            self.logger.error(f"Failed to send request: {e}")
            return None

        # Read the response from the process's stdout
        self.logger.debug("Waiting for response...")
        response_line = self.process.stdout.readline()
        if not response_line:
            self.logger.error("No response received")
            return None

        try:
            self.logger.debug(f"Raw response: {response_line}")
            response = json.loads(response_line.decode("utf-8"))
            self.logger.info(f"Received response: {json.dumps(response)[:200]}...")
            return response
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode response: {e}")
            self.logger.error(f"Raw response: {response_line}")
            return None

    def list_tools(self):
        """Get the list of available tools from the server."""
        return self.send_request("get_tool_definitions")

    def call_tool(self, name, arguments):
        """Call a tool on the server."""
        return self.send_request("call_tool", {"name": name, "arguments": arguments})

    def close(self):
        """Close the connection and terminate the subprocess."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()


def main():
    """Run the MCP client test."""
    print("Starting MCP client test")

    # Create a temporary directory for bundle storage
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_bundle_dir = Path(temp_dir)
        print(f"Created temporary directory: {temp_bundle_dir}")

        # Set up mock sbctl
        mock_sbctl_path = FIXTURES_DIR / "mock_sbctl.py"
        temp_bin_dir = temp_bundle_dir / "bin"
        temp_bin_dir.mkdir(exist_ok=True)
        sbctl_link = temp_bin_dir / "sbctl"

        print(f"Creating mock sbctl at: {sbctl_link}")
        with open(sbctl_link, "w") as f:
            f.write(
                f"""#!/bin/bash
python "{mock_sbctl_path}" "$@"
"""
            )
        os.chmod(sbctl_link, 0o755)

        # Copy the test bundle if it exists
        if TEST_BUNDLE.exists():
            import shutil

            test_bundle_copy = temp_bundle_dir / TEST_BUNDLE.name
            shutil.copy(TEST_BUNDLE, test_bundle_copy)
            print(f"Copied test bundle to: {test_bundle_copy}")
        else:
            print("Warning: Test bundle not found")

        # Set environment variables
        env = os.environ.copy()
        env["MCP_BUNDLE_STORAGE"] = str(temp_bundle_dir)
        env["PYTHONUNBUFFERED"] = "1"
        env["MAX_INITIALIZATION_TIMEOUT"] = "10"
        env["MAX_DOWNLOAD_TIMEOUT"] = "10"
        env["PATH"] = f"{temp_bin_dir}:{env.get('PATH', '')}"

        print("Starting MCP server process")
        process = subprocess.Popen(
            [sys.executable, "-m", "mcp_server_troubleshoot.cli", "--verbose"],
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )

        # Create a thread to read stderr in the background
        import threading

        def read_stderr():
            while True:
                line = process.stderr.readline()
                if not line:
                    break
                print(f"STDERR: {line.decode('utf-8', errors='replace').strip()}")

        stderr_thread = threading.Thread(target=read_stderr)
        stderr_thread.daemon = True
        stderr_thread.start()

        # Wait for server to start
        print("Waiting for server to start...")
        time.sleep(2)

        # Create the client
        client = MCPClient(process)

        try:
            # Test 1: List tools
            print("\n=== Test 1: List tools ===")
            response = client.list_tools()
            if response:
                tools = response.get("result", [])
                print(f"Found {len(tools)} tools:")
                for tool in tools:
                    print(f"  - {tool['name']}")

            # Test 2: Initialize bundle
            if TEST_BUNDLE.exists():
                print("\n=== Test 2: Initialize bundle ===")
                response = client.call_tool(
                    "initialize_bundle", {"source": str(test_bundle_copy), "force": True}
                )
                if response:
                    result = response.get("result", [])
                    if result:
                        text = result[0].get("text", "")
                        print(f"Initialization result: {text[:200]}...")

                # Test 3: List files
                print("\n=== Test 3: List files ===")
                response = client.call_tool("list_files", {"path": "/"})
                if response:
                    result = response.get("result", [])
                    if result:
                        text = result[0].get("text", "")
                        print(f"List files result: {text[:200]}...")

                # Test 4: List available bundles
                print("\n=== Test 4: List available bundles ===")
                response = client.call_tool("list_available_bundles", {"include_invalid": False})
                if response:
                    result = response.get("result", [])
                    if result:
                        text = result[0].get("text", "")
                        print(f"List available bundles result: {text[:200]}...")

                # Test 5: Execute kubectl
                print("\n=== Test 5: Execute kubectl ===")
                response = client.call_tool("kubectl", {"command": "get nodes"})
                if response:
                    result = response.get("result", [])
                    if result:
                        text = result[0].get("text", "")
                        print(f"Kubectl result: {text[:200]}...")

        finally:
            print("\nClosing client and terminating server")
            client.close()


if __name__ == "__main__":
    main()
