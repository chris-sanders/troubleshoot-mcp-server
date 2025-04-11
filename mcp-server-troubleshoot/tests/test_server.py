"""
Tests for the MCP server.
"""

from unittest.mock import AsyncMock, patch

import pytest

from mcp_server_troubleshoot.server import TroubleshootMCPServer


@pytest.mark.asyncio
async def test_server_initialization():
    """Test that the server can be initialized."""
    server = TroubleshootMCPServer()
    assert server is not None
    assert server.server is not None


@pytest.mark.asyncio
async def test_register_handlers():
    """Test that the server registers handlers."""
    server = TroubleshootMCPServer()

    # Mock the tool decorator to check if it's called
    with patch.object(server.server, "tool", wraps=server.server.tool) as mock_tool:
        # Re-register handlers
        server._register_handlers()

        # Verify that the tool decorator was called at least once
        assert mock_tool.call_count >= 1


@pytest.mark.asyncio
async def test_serve():
    """Test that the server can be served."""
    server = TroubleshootMCPServer()

    # Mock the run_stdio_async method
    with patch.object(server.server, "run_stdio_async", new_callable=AsyncMock) as mock_run_stdio:
        # Call serve
        await server.serve()

        # Verify that run_stdio_async was called
        mock_run_stdio.assert_awaited_once()
