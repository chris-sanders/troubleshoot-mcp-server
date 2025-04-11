"""
MCP server implementation for Kubernetes support bundles.
"""

import logging

from mcp.server import FastMCP

logger = logging.getLogger(__name__)


class TroubleshootMCPServer:
    """
    MCP server for Kubernetes support bundles.

    This server allows AI models to interact with Kubernetes support bundles using
    the Model Context Protocol (MCP).
    """

    def __init__(self) -> None:
        """Initialize the MCP server."""
        self.server = FastMCP(name="troubleshoot-mcp-server")
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register all MCP protocol handlers."""

        @self.server.tool()
        async def dummy_tool() -> str:
            """
            A dummy tool that does nothing.
            Used to ensure the server returns at least one tool.
            """
            return "This is a dummy tool that does nothing."

    async def serve(self) -> None:
        """
        Start the MCP server using stdio transport.
        """
        try:
            await self.server.run_stdio_async()
        except Exception as e:
            logger.exception(f"Error while serving: {e}")
            raise
