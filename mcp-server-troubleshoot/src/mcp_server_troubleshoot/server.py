"""
MCP server implementation for Kubernetes support bundles.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp import Tool
from mcp.types import TextContent

from .bundle import BundleManager, BundleManagerError, InitializeBundleArgs
from .kubectl import KubectlError, KubectlExecutor, KubectlCommandArgs

logger = logging.getLogger(__name__)


class TroubleshootMCPServer:
    """
    MCP server for Kubernetes support bundles.

    This server allows AI models to interact with Kubernetes support bundles using
    the Model Context Protocol (MCP).
    """

    def __init__(self, bundle_dir: Optional[Path] = None) -> None:
        """
        Initialize the MCP server.

        Args:
            bundle_dir: The directory where bundles will be stored. If not provided,
                a temporary directory will be used.
        """
        self.server = Server(name="troubleshoot-mcp-server")
        self.bundle_manager = BundleManager(bundle_dir)
        self.kubectl_executor = KubectlExecutor(self.bundle_manager)
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register all MCP protocol handlers."""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """Return a list of available tools."""
            return [
                Tool(
                    name="initialize_bundle",
                    description="Initialize a Kubernetes support bundle for analysis",
                    inputSchema=InitializeBundleArgs.model_json_schema(),
                ),
                Tool(
                    name="kubectl",
                    description="Execute kubectl commands against the initialized bundle's API server",
                    inputSchema=KubectlCommandArgs.model_json_schema(),
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """
            Handle tool calls.

            Args:
                name: The name of the tool to call
                arguments: The arguments to pass to the tool

            Returns:
                A list of content items to return to the model
            """
            if name == "initialize_bundle":
                return await self._handle_initialize_bundle(arguments)
            elif name == "kubectl":
                return await self._handle_kubectl(arguments)
            error_message = f"Tool '{name}' is not implemented yet."
            logger.error(error_message)
            return [TextContent(type="text", text=error_message)]

    async def _handle_initialize_bundle(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """
        Handle the initialize_bundle tool call.

        Args:
            arguments: The arguments for the tool call

        Returns:
            A list of content items to return to the model
        """
        try:
            args = InitializeBundleArgs(**arguments)
            result = await self.bundle_manager.initialize_bundle(args.source, args.force)

            # Convert the metadata to a dictionary
            metadata_dict = json.loads(result.model_dump_json())

            # Format paths as strings
            metadata_dict["path"] = str(metadata_dict["path"])
            metadata_dict["kubeconfig_path"] = str(metadata_dict["kubeconfig_path"])

            response = f"Bundle initialized successfully:\n```json\n{json.dumps(metadata_dict, indent=2)}\n```"
            return [TextContent(type="text", text=response)]

        except BundleManagerError as e:
            error_message = f"Failed to initialize bundle: {str(e)}"
            logger.error(error_message)
            return [TextContent(type="text", text=error_message)]
        except Exception as e:
            error_message = f"Unexpected error initializing bundle: {str(e)}"
            logger.exception(error_message)
            return [TextContent(type="text", text=error_message)]
            
    async def _handle_kubectl(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """
        Handle the kubectl tool call.
        
        Args:
            arguments: The arguments for the tool call
            
        Returns:
            A list of content items to return to the model
        """
        try:
            args = KubectlCommandArgs(**arguments)
            result = await self.kubectl_executor.execute(
                args.command, 
                args.timeout, 
                args.json_output
            )
            
            # Format the response based on the result
            if result.is_json:
                # Convert objects to JSON with nice formatting
                output_str = json.dumps(result.output, indent=2)
                response = f"kubectl command executed successfully:\n```json\n{output_str}\n```"
            else:
                # Use plain text for non-JSON output
                output_str = result.stdout
                response = f"kubectl command executed successfully:\n```\n{output_str}\n```"
                
            # Add metadata about the command execution
            metadata = {
                "command": result.command,
                "exit_code": result.exit_code,
                "duration_ms": result.duration_ms
            }
            
            metadata_str = json.dumps(metadata, indent=2)
            response += f"\nCommand metadata:\n```json\n{metadata_str}\n```"
            
            return [TextContent(type="text", text=response)]
            
        except KubectlError as e:
            error_message = f"kubectl command failed: {str(e)}"
            logger.error(error_message)
            return [TextContent(type="text", text=error_message)]
        except BundleManagerError as e:
            error_message = f"Bundle error: {str(e)}"
            logger.error(error_message)
            return [TextContent(type="text", text=error_message)]
        except Exception as e:
            error_message = f"Unexpected error executing kubectl command: {str(e)}"
            logger.exception(error_message)
            return [TextContent(type="text", text=error_message)]
    
    async def serve(
        self,
        input_stream: Optional[asyncio.StreamReader] = None,
        output_stream: Optional[asyncio.StreamWriter] = None,
    ) -> None:
        """
        Start the MCP server with the given input and output streams.

        Args:
            input_stream: The input stream to read from (defaults to stdin)
            output_stream: The output stream to write to (defaults to stdout)
        """
        input_stream = input_stream or asyncio.StreamReader()
        await asyncio.get_event_loop().connect_read_pipe(
            lambda: asyncio.StreamReaderProtocol(input_stream), sys.stdin
        )

        if output_stream is None:
            output_stream = asyncio.StreamWriter(sys.stdout.buffer, None, None, None)

        try:
            await self.server.serve(input_stream, output_stream)
        except Exception as e:
            logger.exception(f"Error while serving: {e}")
            raise
        finally:
            # Clean up resources when the server shuts down
            await self.bundle_manager.cleanup()
