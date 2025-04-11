"""
Tests for the MCP server.
"""

import asyncio
import json
from typing import Any, Dict, List
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_troubleshoot.server import TroubleshootMCPServer


@pytest.mark.asyncio
async def test_server_initialization():
    """Test that the server can be initialized."""
    server = TroubleshootMCPServer()
    assert server is not None
    assert server.server is not None


@pytest.mark.asyncio
async def test_list_tools():
    """Test that the server returns an empty list of tools for now."""
    server = TroubleshootMCPServer()
    
    # Mock the MCP Server list_tools method to capture the handler
    list_tools_handler = None
    
    def list_tools_decorator(func):
        nonlocal list_tools_handler
        list_tools_handler = func
        return func
    
    with patch.object(server.server, 'list_tools', return_value=list_tools_decorator):
        server._register_handlers()
        
    # Call the captured handler
    assert list_tools_handler is not None
    tools = await list_tools_handler()
    
    # Verify that an empty list is returned
    assert isinstance(tools, list)
    assert len(tools) == 0


@pytest.mark.asyncio
async def test_call_tool():
    """Test that the server returns an error for non-existent tools."""
    server = TroubleshootMCPServer()
    
    # Mock the MCP Server call_tool method to capture the handler
    call_tool_handler = None
    
    def call_tool_decorator(func):
        nonlocal call_tool_handler
        call_tool_handler = func
        return func
    
    with patch.object(server.server, 'call_tool', return_value=call_tool_decorator):
        server._register_handlers()
        
    # Call the captured handler with a non-existent tool
    assert call_tool_handler is not None
    response = await call_tool_handler("nonexistent_tool", {})
    
    # Verify that an error message is returned
    assert len(response) == 1
    assert response[0].type == "text"
    assert "is not implemented yet" in response[0].text


@pytest.mark.asyncio
async def test_serve():
    """Test that the server can be served."""
    server = TroubleshootMCPServer()
    
    # Mock the MCP Server serve method
    server.server.serve = AsyncMock()
    
    # Create mock input and output streams
    input_stream = MagicMock(spec=asyncio.StreamReader)
    output_stream = MagicMock(spec=asyncio.StreamWriter)
    
    # Call serve with the mock streams
    await server.serve(input_stream, output_stream)
    
    # Verify that the MCP Server serve method was called with the mock streams
    server.server.serve.assert_awaited_once_with(input_stream, output_stream)