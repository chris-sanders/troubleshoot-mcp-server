"""
Tests for the MCP server.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_troubleshoot.bundle import BundleMetadata
from mcp_server_troubleshoot.server import TroubleshootMCPServer


@pytest.mark.asyncio
async def test_server_initialization():
    """Test that the server can be initialized."""
    server = TroubleshootMCPServer()
    assert server is not None
    assert server.server is not None
    assert server.bundle_manager is not None


@pytest.mark.asyncio
async def test_list_tools():
    """Test that the server returns the expected list of tools."""
    server = TroubleshootMCPServer()

    # Mock the MCP Server list_tools method to capture the handler
    list_tools_handler = None

    def list_tools_decorator(func):
        nonlocal list_tools_handler
        list_tools_handler = func
        return func

    with patch.object(server.server, "list_tools", return_value=list_tools_decorator):
        server._register_handlers()

    # Call the captured handler
    assert list_tools_handler is not None
    tools = await list_tools_handler()

    # Verify that the expected tools are returned
    assert isinstance(tools, list)
    assert len(tools) == 1
    assert tools[0].name == "initialize_bundle"


@pytest.mark.asyncio
async def test_call_tool_nonexistent():
    """Test that the server returns an error for non-existent tools."""
    server = TroubleshootMCPServer()

    # Mock the MCP Server call_tool method to capture the handler
    call_tool_handler = None

    def call_tool_decorator(func):
        nonlocal call_tool_handler
        call_tool_handler = func
        return func

    with patch.object(server.server, "call_tool", return_value=call_tool_decorator):
        server._register_handlers()

    # Call the captured handler with a non-existent tool
    assert call_tool_handler is not None
    response = await call_tool_handler("nonexistent_tool", {})

    # Verify that an error message is returned
    assert len(response) == 1
    assert response[0].type == "text"
    assert "is not implemented yet" in response[0].text


@pytest.mark.asyncio
async def test_call_tool_initialize_bundle():
    """Test that the server can handle the initialize_bundle tool."""
    server = TroubleshootMCPServer()

    # Create a test file that exists
    with tempfile.NamedTemporaryFile() as temp_file:
        # Mock the BundleManager.initialize_bundle method
        mock_metadata = BundleMetadata(
            id="test_bundle",
            source=temp_file.name,
            path=Path("/test/path"),
            kubeconfig_path=Path("/test/kubeconfig"),
            initialized=True,
        )
        server.bundle_manager.initialize_bundle = AsyncMock(return_value=mock_metadata)

        # Call the handler directly with a real file path
        response = await server._handle_initialize_bundle({"source": temp_file.name, "force": False})

        # Verify that the bundle manager was called
        server.bundle_manager.initialize_bundle.assert_awaited_once_with(temp_file.name, False)

    # Verify the response
    assert len(response) == 1
    assert response[0].type == "text"
    assert "Bundle initialized successfully" in response[0].text
    assert "test_bundle" in response[0].text


@pytest.mark.asyncio
async def test_serve():
    """Test that the server can be served."""
    server = TroubleshootMCPServer()

    # Mock the MCP Server serve method
    server.server.serve = AsyncMock()

    # Mock the BundleManager cleanup method
    server.bundle_manager.cleanup = AsyncMock()

    # Create mock input and output streams
    input_stream = MagicMock(spec=asyncio.StreamReader)
    output_stream = MagicMock(spec=asyncio.StreamWriter)

    # Mock the connect_read_pipe method which fails in tests
    mock_loop = AsyncMock()
    
    # Call serve with the mock streams
    with patch("asyncio.get_event_loop", return_value=mock_loop):
        await server.serve(input_stream, output_stream)

    # Verify that the MCP Server serve method was called with the mock streams
    server.server.serve.assert_awaited_once_with(input_stream, output_stream)

    # Verify that the bundle manager cleanup method was called
    server.bundle_manager.cleanup.assert_awaited_once()
