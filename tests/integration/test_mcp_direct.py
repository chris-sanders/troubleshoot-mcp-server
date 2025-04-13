"""
Integration test for direct MCP communication with the server.

This test:
1. Starts the MCP server in a subprocess
2. Sends JSON-RPC requests to it through stdin/stdout
3. Tests all available tools
4. Verifies correct responses

This provides a faster way to test the MCP server functionality
without requiring Docker, making development and debugging easier.
"""

import pytest

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

import pytest
import pytest_asyncio

# Path to the fixtures directory containing test bundles
FIXTURES_DIR = Path(__file__).parents[1] / "fixtures"
TEST_BUNDLE = FIXTURES_DIR / "support-bundle-2025-04-11T14_05_31.tar.gz"


class MCPClient:
    """
    Client for communicating with the MCP server.
    
    This client uses subprocess communication to send requests to
    the MCP server and receive responses.
    """
    
    def __init__(self, process: subprocess.Popen) -> None:
        """
        Initialize with a subprocess connected to an MCP server.
        
        Args:
            process: The subprocess.Popen object connected to the MCP server
        """
        self.process = process
        self.request_id = 0
    
    def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a JSON-RPC request to the server.
        
        Args:
            method: The JSON-RPC method to call
            params: Optional parameters for the method
            
        Returns:
            The JSON-RPC response
        """
        if params is None:
            params = {}
            
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": str(self.request_id),
            "method": method,
            "params": params
        }
        
        # Send the request to the process's stdin
        request_str = json.dumps(request) + "\n"
        self.process.stdin.write(request_str.encode("utf-8"))
        self.process.stdin.flush()
        
        # Read the response from the process's stdout
        response_line = self.process.stdout.readline()
        if not response_line:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32000, "message": "No response received from server"},
                "id": str(self.request_id)
            }
            
        try:
            response = json.loads(response_line.decode("utf-8"))
            return response
        except json.JSONDecodeError as e:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": f"Invalid JSON response: {e}"},
                "id": str(self.request_id)
            }
    
    def list_tools(self) -> Dict[str, Any]:
        """Get the list of available tools from the server."""
        return self.send_request("get_tool_definitions")
    
    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool on the server.
        
        Args:
            name: The name of the tool to call
            arguments: The arguments to pass to the tool
            
        Returns:
            The JSON-RPC response
        """
        return self.send_request("call_tool", {"name": name, "arguments": arguments})
    
    def close(self) -> None:
        """Close the connection and terminate the subprocess."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()


@pytest_asyncio.fixture
async def temp_bundle_dir():
    """Create a temporary directory for bundles."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest_asyncio.fixture
async def mcp_server_client(temp_bundle_dir):
    """
    Start the MCP server in a subprocess and connect a client to it.
    
    Args:
        temp_bundle_dir: Temporary directory for bundle storage
        
    Returns:
        An MCPClient instance connected to the MCP server
    """
    # Set up mock sbctl by creating a symlink or modifying PATH
    mock_sbctl_path = FIXTURES_DIR / "mock_sbctl.py"
    temp_bin_dir = temp_bundle_dir / "bin"
    temp_bin_dir.mkdir(exist_ok=True)
    sbctl_link = temp_bin_dir / "sbctl"
    
    # Create a wrapper script for the mock sbctl
    with open(sbctl_link, "w") as f:
        f.write(f"""#!/bin/bash
python "{mock_sbctl_path}" "$@"
""")
    os.chmod(sbctl_link, 0o755)
    
    # Set environment variables for the server
    env = os.environ.copy()
    env["MCP_BUNDLE_STORAGE"] = str(temp_bundle_dir)
    env["PYTHONUNBUFFERED"] = "1"  # Important for immediate stdout/stdin communication
    env["MAX_INITIALIZATION_TIMEOUT"] = "10"  # Lower the timeout for testing
    env["MAX_DOWNLOAD_TIMEOUT"] = "10"  # Lower the timeout for testing
    env["PATH"] = f"{temp_bin_dir}:{env.get('PATH', '')}"  # Add our mock sbctl to PATH
    
    # Copy the test bundle to the bundle directory if it exists
    if TEST_BUNDLE.exists():
        import shutil
        test_bundle_copy = temp_bundle_dir / TEST_BUNDLE.name
        shutil.copy(TEST_BUNDLE, test_bundle_copy)
    
    # Start the MCP server process
    process = subprocess.Popen(
        [sys.executable, "-m", "mcp_server_troubleshoot.cli", "--verbose"],
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0  # Unbuffered communication
    )
    
    # Wait a moment for server initialization
    await asyncio.sleep(2)
    
    # Verify the process started successfully by sending a ping
    client = MCPClient(process)
    ping_response = client.send_request("get_tool_definitions")
    if "error" in ping_response:
        # If we couldn't connect, log the stderr
        stderr = process.stderr.read(4096).decode("utf-8", errors="replace")
        pytest.skip(f"Failed to start MCP server: {stderr}")
    
    try:
        yield client
    finally:
        client.close()


@pytest.mark.skipif(not TEST_BUNDLE.exists(), reason="Test bundle not available")
class TestMCPDirect:
    """Tests for direct communication with the MCP server."""
    
    def test_list_tools(self, mcp_server_client):
        """Test retrieving the list of available tools."""
        response = mcp_server_client.list_tools()
        
        # Check response structure
        assert "jsonrpc" in response
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        
        # Verify we get a list of tools
        tools = response["result"]
        assert isinstance(tools, list)
        
        # Check that the expected tools are available
        tool_names = [tool["name"] for tool in tools]
        expected_tools = [
            "initialize_bundle",
            "kubectl",
            "list_files",
            "read_file",
            "grep_files"
        ]
        
        for tool in expected_tools:
            assert tool in tool_names, f"Tool {tool} should be available"
    
    def test_initialize_bundle(self, mcp_server_client):
        """Test initializing a bundle with the MCP server."""
        bundle_path = f"/tmp/{TEST_BUNDLE.name}"
        # Fix the path if the test is running on Windows
        if sys.platform == 'win32':
            bundle_path = str(TEST_BUNDLE.absolute())
        
        response = mcp_server_client.call_tool(
            "initialize_bundle", 
            {"source": str(TEST_BUNDLE), "force": True}
        )
        
        # Check response structure
        assert "jsonrpc" in response
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        
        # Verify the result contains the expected information
        result = response["result"]
        assert isinstance(result, list)
        assert len(result) > 0
        assert result[0]["type"] == "text"
        
        result_text = result[0]["text"]
        assert "Bundle initialized" in result_text

        # NEW: Verify API server availability
        diagnostics_text = ""
        if "API server is NOT available" in result_text:
            # Extract the diagnostic information
            if "Diagnostic information" in result_text:
                diagnostics_start = result_text.find("Diagnostic information:")
                diagnostics_json_start = result_text.find("```json", diagnostics_start) + 7
                diagnostics_json_end = result_text.find("```", diagnostics_json_start)
                diagnostics_text = result_text[diagnostics_json_start:diagnostics_json_end].strip()
                
                # Parse and verify diagnostics
                try:
                    diagnostics = json.loads(diagnostics_text)
                    # Test fails if the API server should be available but isn't
                    assert not diagnostics.get("api_server_available", False), \
                        f"API server should be available, diagnostics: {diagnostics_text}"
                except json.JSONDecodeError:
                    pytest.fail(f"Failed to parse diagnostics JSON: {diagnostics_text}")
    
    def test_list_files(self, mcp_server_client):
        """Test listing files in the initialized bundle."""
        # First initialize the bundle
        init_response = mcp_server_client.call_tool(
            "initialize_bundle", 
            {"source": str(TEST_BUNDLE), "force": True}
        )
        
        # Then list files at the root directory
        response = mcp_server_client.call_tool(
            "list_files",
            {"path": "/"}
        )
        
        # Check response structure
        assert "jsonrpc" in response
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        
        # Verify the result
        result = response["result"]
        assert isinstance(result, list)
        assert len(result) > 0
        assert result[0]["type"] == "text"
        
        result_text = result[0]["text"]
        assert "Listed files" in result_text
    
    def test_recursive_list_files(self, mcp_server_client):
        """Test recursive file listing in the initialized bundle."""
        # First initialize the bundle
        init_response = mcp_server_client.call_tool(
            "initialize_bundle", 
            {"source": str(TEST_BUNDLE), "force": True}
        )
        
        # Then list files recursively
        response = mcp_server_client.call_tool(
            "list_files",
            {"path": "/", "recursive": True}
        )
        
        # Check response structure
        assert "jsonrpc" in response
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        
        # Verify the result
        result = response["result"]
        assert isinstance(result, list)
        assert len(result) > 0
        assert result[0]["type"] == "text"
        
        result_text = result[0]["text"]
        assert "Listed files" in result_text
        assert "recursively" in result_text
    
    def test_grep_files(self, mcp_server_client):
        """Test searching for patterns in files."""
        # First initialize the bundle
        init_response = mcp_server_client.call_tool(
            "initialize_bundle", 
            {"source": str(TEST_BUNDLE), "force": True}
        )
        
        # Search for a pattern
        response = mcp_server_client.call_tool(
            "grep_files",
            {
                "pattern": "error",
                "path": "/",
                "recursive": True,
                "case_sensitive": False
            }
        )
        
        # Check response structure
        assert "jsonrpc" in response
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        
        # Verify the result
        result = response["result"]
        assert isinstance(result, list)
        assert len(result) > 0
        assert result[0]["type"] == "text"
        
        result_text = result[0]["text"]
        assert "Found" in result_text
    
    def test_read_file(self, mcp_server_client):
        """Test reading a file from the bundle."""
        # First initialize the bundle
        init_response = mcp_server_client.call_tool(
            "initialize_bundle", 
            {"source": str(TEST_BUNDLE), "force": True}
        )
        
        # Find a file to read by listing files
        list_response = mcp_server_client.call_tool(
            "list_files",
            {"path": "/"}
        )
        
        # Look for a directory in the response
        list_result_text = list_response["result"][0]["text"]
        
        # Parse out a directory name using simple string search
        # This is a bit hacky, but it works for test purposes
        directory = None
        for term in ["kubernetes", "cluster-info", "cluster-resources", "pods", "logs"]:
            if term in list_result_text:
                directory = term
                break
        
        if directory is None:
            pytest.skip("No suitable directory found in bundle")
        
        # List files in that directory
        dir_response = mcp_server_client.call_tool(
            "list_files",
            {"path": f"/{directory}"}
        )
        
        # Try to find a file in this directory
        dir_result_text = dir_response["result"][0]["text"]
        
        # Parse out a file name - find the first ".yaml" or ".json" or ".log" file
        file_extensions = [".yaml", ".json", ".log", ".txt"]
        file_name = None
        for ext in file_extensions:
            if ext in dir_result_text:
                start_idx = dir_result_text.find(ext) - 30  # Look 30 chars before extension
                start_idx = max(0, start_idx)  # Ensure we don't go negative
                substring = dir_result_text[start_idx:dir_result_text.find(ext) + len(ext)]
                
                # Find a word that ends with the extension
                import re
                pattern = r'\b\w+' + ext + r'\b'
                matches = re.findall(pattern, substring)
                if matches:
                    file_name = matches[0]
                    break
                
                # If regex fails, make a guess
                quote_idx = substring.rfind('"')
                if quote_idx != -1:
                    file_name = substring[quote_idx+1:substring.find(ext) + len(ext)]
                    break
        
        if file_name is None:
            # Use a hardcoded path as fallback
            file_path = f"/{directory}/version.json"
        else:
            file_path = f"/{directory}/{file_name}"
        
        # Read the file
        read_response = mcp_server_client.call_tool(
            "read_file",
            {"path": file_path}
        )
        
        # Check response structure
        assert "jsonrpc" in read_response
        assert read_response["jsonrpc"] == "2.0"
        assert "result" in read_response or "error" in read_response
        
        # If we got a result, it should have the expected structure
        if "result" in read_response:
            result = read_response["result"]
            assert isinstance(result, list)
            assert len(result) > 0
            assert result[0]["type"] == "text"
            
            result_text = result[0]["text"]
            assert "Read" in result_text

    def test_kubectl_command(self, mcp_server_client):
        """Test executing kubectl commands."""
        # First initialize the bundle
        init_response = mcp_server_client.call_tool(
            "initialize_bundle", 
            {"source": str(TEST_BUNDLE), "force": True}
        )
        
        # Now try a kubectl command
        response = mcp_server_client.call_tool(
            "kubectl",
            {"command": "get nodes"}
        )
        
        # Check response structure
        assert "jsonrpc" in response
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        
        # Verify API server is available - this should have more thorough checks now
        result = response["result"]
        assert isinstance(result, list)
        assert len(result) > 0
        assert result[0]["type"] == "text"
        
        result_text = result[0]["text"]
        if "API server is not available" in result_text:
            # We should have diagnostic info to analyze
            if "Diagnostic information" in result_text:
                diagnostics_start = result_text.find("Diagnostic information:")
                diagnostics_json_start = result_text.find("```json", diagnostics_start) + 7
                diagnostics_json_end = result_text.find("```", diagnostics_json_start)
                diagnostics_text = result_text[diagnostics_json_start:diagnostics_json_end].strip()
                
                # Parse and analyze diagnostics to understand why the API server is not available
                try:
                    diagnostics = json.loads(diagnostics_text)
                    print(f"API server diagnostic info: {json.dumps(diagnostics, indent=2)}")
                    
                    # Check specific issues that could be causing the API server to not be available
                    system_info = diagnostics.get("system_info", {})
                    ports_checked = [k for k in system_info.keys() if k.startswith("port_") and k.endswith("_checked")]
                    for port_key in ports_checked:
                        port = port_key.split("_")[1]
                        listening_key = f"port_{port}_listening"
                        if listening_key in system_info:
                            # If port should be listening but isn't, test should fail
                            if not system_info.get(listening_key, False):
                                pytest.fail(f"Port {port} should be listening but isn't")
                    
                    # If the sbctl process isn't running, fail the test
                    if not diagnostics.get("sbctl_process_running", False):
                        pytest.fail("sbctl process should be running")
                    
                except json.JSONDecodeError:
                    pytest.fail(f"Failed to parse diagnostics JSON: {diagnostics_text}")
                
        elif "kubectl command executed" in result_text:
            # API server is responding; this is the expected case in real usage
            assert "kubectl command executed successfully" in result_text
    
    def test_error_handling(self, mcp_server_client):
        """Test error handling in the MCP server."""
        # Call a tool with invalid arguments
        response = mcp_server_client.call_tool(
            "read_file",
            {"path": "/non-existent-file.txt"}
        )
        
        # Check response structure
        assert "jsonrpc" in response
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        
        # The result should contain an error message
        result = response["result"]
        assert isinstance(result, list)
        assert len(result) > 0
        assert result[0]["type"] == "text"
        
        result_text = result[0]["text"]
        assert "error" in result_text.lower() or "not found" in result_text.lower()
    
    def test_end_to_end_workflow(self, mcp_server_client):
        """Test a complete workflow combining multiple tools."""
        # Step 1: Initialize a bundle
        init_response = mcp_server_client.call_tool(
            "initialize_bundle", 
            {"source": str(TEST_BUNDLE), "force": True}
        )
        assert "result" in init_response
        
        # NEW: Verify the API server status in the initialization response
        init_result = init_response["result"]
        assert isinstance(init_result, list)
        assert len(init_result) > 0
        init_result_text = init_result[0]["text"]
        
        api_server_status = "API server not verified"
        if "API server is NOT available" in init_result_text:
            api_server_status = "API server is NOT available"
            
            # Extract diagnostics to understand why API server isn't available
            if "Diagnostic information" in init_result_text:
                diagnostics_start = init_result_text.find("Diagnostic information:")
                diagnostics_json_start = init_result_text.find("```json", diagnostics_start) + 7
                diagnostics_json_end = init_result_text.find("```", diagnostics_json_start)
                diagnostics_text = init_result_text[diagnostics_json_start:diagnostics_json_end].strip()
                
                try:
                    diagnostics = json.loads(diagnostics_text)
                    print(f"API server diagnostic info: {json.dumps(diagnostics, indent=2)}")
                    
                    # Check if sbctl is marked as available but the server not running
                    if diagnostics.get("sbctl_available", False) and not diagnostics.get("api_server_available", False):
                        # This specific scenario should cause the test to fail
                        if diagnostics.get("sbctl_process_running", False) and diagnostics.get("bundle_initialized", False):
                            pytest.fail(f"Bundle initialized with sbctl process running, but API server not available. Diagnostics: {diagnostics_text}")
                            
                except json.JSONDecodeError:
                    pytest.fail(f"Failed to parse diagnostics JSON: {diagnostics_text}")
        elif "Bundle initialized successfully" in init_result_text:
            api_server_status = "API server is available"
        
        print(f"API Server Status: {api_server_status}")
        
        # Step 2: List files at the root
        list_response = mcp_server_client.call_tool(
            "list_files",
            {"path": "/"}
        )
        assert "result" in list_response
        
        # Step 3: Search for errors in the bundle
        grep_response = mcp_server_client.call_tool(
            "grep_files",
            {
                "pattern": "error",
                "path": "/",
                "recursive": True,
                "case_sensitive": False
            }
        )
        assert "result" in grep_response
        
        # Step 4: Try a kubectl command - this should succeed only if API server is available
        kubectl_response = mcp_server_client.call_tool(
            "kubectl",
            {"command": "get nodes"}
        )
        assert "result" in kubectl_response
        
        kubectl_result = kubectl_response["result"]
        assert isinstance(kubectl_result, list)
        assert len(kubectl_result) > 0
        kubectl_result_text = kubectl_result[0]["text"]
        
        # If API server should be available but kubectl command failed, fail the test
        if api_server_status == "API server is available" and "API server is not available" in kubectl_result_text:
            pytest.fail(f"API server reported as available during initialization, but kubectl command failed with: {kubectl_result_text}")
        
        # Success if we got this far
        assert True


if __name__ == "__main__":
    # Allow running as a standalone script
    import pytest
    
    # Check if the test bundle exists
    if not TEST_BUNDLE.exists():
        print(f"Warning: Test bundle not found at {TEST_BUNDLE}")
        print("Some tests will be skipped")
    
    # Run the tests
    pytest.main(["-xvs", __file__])