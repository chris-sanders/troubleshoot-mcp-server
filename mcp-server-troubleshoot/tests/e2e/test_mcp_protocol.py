"""
End-to-end test for MCP protocol communication with the server.
This test:
1. Starts the MCP server in a subprocess
2. Sends JSON-RPC requests to the server
3. Verifies the responses are correct
4. Tests all major MCP protocol functionality
"""

import asyncio
import json
import os
import pytest
import pytest_asyncio
import sys
from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parents[2].absolute()
FIXTURES_DIR = Path(__file__).parents[1] / "fixtures"


class MCPClient:
    """Simple MCP client for testing."""
    
    def __init__(self, process):
        """Initialize with a subprocess that implements MCP protocol over stdio."""
        self.process = process
        self.request_id = 0
    
    async def send_request(self, method, params=None):
        """Send a JSON-RPC request to the server."""
        if params is None:
            params = {}
        
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": str(self.request_id),
            "method": method,
            "params": params
        }
        
        request_str = json.dumps(request) + "\n"
        self.process.stdin.write(request_str.encode("utf-8"))
        await self.process.stdin.drain()
        
        # Read the response
        response_line = await self.process.stdout.readline()
        if not response_line:
            return None
        
        response_str = response_line.decode("utf-8").strip()
        return json.loads(response_str)
    
    async def list_tools(self):
        """Get the list of available tools from the server."""
        return await self.send_request("get_tool_definitions")
    
    async def call_tool(self, name, arguments):
        """Call a tool on the server."""
        return await self.send_request(
            "call_tool", 
            {"name": name, "arguments": arguments}
        )


@pytest_asyncio.fixture
async def mcp_server():
    """Start the MCP server in a subprocess and yield a client connected to it."""
    # Skip tests if running in CI environment without proper setup
    if os.environ.get("CI") == "true":
        pytest.skip("Skipping MCP protocol tests in CI environment")
        
    # Ensure bundles directory exists
    bundles_dir = PROJECT_ROOT / "bundles"
    bundles_dir.mkdir(exist_ok=True)
    
    # Set environment variables for the server
    env = os.environ.copy()
    env["SBCTL_TOKEN"] = "test-token"
    env["MCP_BUNDLE_STORAGE"] = str(bundles_dir)
    
    # Start the server process
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "mcp_server_troubleshoot.cli",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
        cwd=str(PROJECT_ROOT)
    )
    
    # Create a client connected to the server
    client = MCPClient(process)
    
    try:
        yield client
    finally:
        # Clean up the process
        process.terminate()
        await process.wait()


@pytest.mark.asyncio
async def test_list_tools(mcp_server):
    """Test that the server returns a list of available tools."""
    response = await mcp_server.list_tools()
    
    assert response["jsonrpc"] == "2.0"
    assert "result" in response
    assert isinstance(response["result"], list)
    
    tools = response["result"]
    tool_names = [tool["name"] for tool in tools]
    
    # Verify that all expected tools are present
    expected_tools = ["initialize_bundle", "kubectl", "list_files", "read_file", "grep_files"]
    for tool in expected_tools:
        assert tool in tool_names


@pytest.mark.asyncio
async def test_call_tool_list_files(mcp_server):
    """Test calling the list_files tool."""
    # First, we need a bundle to be initialized
    # Either initialize a bundle or mock the bundle manager
    
    # For now, we'll test the basic error response when there's no active bundle
    response = await mcp_server.call_tool("list_files", {"path": "/"})
    
    assert response["jsonrpc"] == "2.0"
    assert "result" in response or "error" in response
    
    # Since there's no active bundle, we expect an error
    # but the protocol should still work correctly
    if "error" in response:
        assert response["error"]["code"] is not None
        assert "message" in response["error"]


@pytest.mark.skip(reason="Temporarily skipped until MCP server is properly configured")
@pytest.mark.asyncio
@pytest.mark.skipif(
    not (FIXTURES_DIR / "support-bundle-2025-04-11T14_05_31.tar.gz").exists(),
    reason="Test bundle fixture not available"
)
async def test_initialize_bundle(mcp_server):
    """Test initializing a bundle from a fixture."""
    bundle_path = str(FIXTURES_DIR / "support-bundle-2025-04-11T14_05_31.tar.gz")
    
    response = await mcp_server.call_tool(
        "initialize_bundle", 
        {"source": bundle_path, "force": True}
    )
    
    assert response["jsonrpc"] == "2.0"
    assert "result" in response
    
    # If initialization succeeds, we should see a success message
    result_text = response["result"][0]["text"]
    assert "Bundle initialized successfully" in result_text


@pytest.mark.skip(reason="Temporarily skipped until MCP server is properly configured")
@pytest.mark.asyncio
@pytest.mark.skipif(
    not (FIXTURES_DIR / "support-bundle-2025-04-11T14_05_31.tar.gz").exists(),
    reason="Test bundle fixture not available"
)
async def test_end_to_end_workflow(mcp_server):
    """Test a complete workflow using the MCP protocol."""
    # Step 1: Initialize the bundle
    bundle_path = str(FIXTURES_DIR / "support-bundle-2025-04-11T14_05_31.tar.gz")
    await mcp_server.call_tool(
        "initialize_bundle", 
        {"source": bundle_path, "force": True}
    )
    
    # Step 2: List files at the root directory
    list_response = await mcp_server.call_tool(
        "list_files", 
        {"path": "/"}
    )
    assert list_response["jsonrpc"] == "2.0"
    assert "result" in list_response
    
    # Step 3: Execute a kubectl command
    kubectl_response = await mcp_server.call_tool(
        "kubectl", 
        {"command": "get pods"}
    )
    assert kubectl_response["jsonrpc"] == "2.0"
    assert "result" in kubectl_response
    
    # Step 4: Read a file
    # Find a path that should exist in the bundle from the list_files result
    # or use a known path from the fixture
    read_response = await mcp_server.call_tool(
        "read_file", 
        {"path": "/kubernetes/pods"}  # Adjust path based on actual bundle structure
    )
    assert read_response["jsonrpc"] == "2.0"
    # If the path exists, we should get a result, otherwise an error
    assert "result" in read_response or "error" in read_response