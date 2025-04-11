"""
MCP server implementation for Kubernetes support bundles.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server import FastMCP
from mcp import Tool
from mcp.types import TextContent

from .bundle import BundleManager, BundleManagerError, InitializeBundleArgs
from .kubectl import KubectlExecutor, KubectlCommandArgs, KubectlError

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
        self.server = FastMCP(name="troubleshoot-mcp-server")
        self.bundle_manager = BundleManager(bundle_dir)
        self.kubectl_executor = KubectlExecutor(self.bundle_manager)
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register all MCP protocol handlers."""

        # Use named decorators because lambda functions require names
        @self.server.tool(name="initialize_bundle")
        async def initialize_bundle(source: str, force: bool = False) -> str:
            """
            Initialize a Kubernetes support bundle for analysis.
            
            Args:
                source: The source of the bundle (URL or local path)
                force: Whether to force re-initialization if a bundle is already active
                
            Returns:
                A message with the bundle initialization status
            """
            return await _initialize_bundle(self, source, force)
                
        @self.server.tool(name="kubectl")
        async def kubectl(command: str, timeout: int = 30, json_output: bool = True) -> str:
            """
            Execute kubectl commands against the initialized bundle's API server.
            
            Args:
                command: The kubectl command to execute
                timeout: Timeout in seconds for the command
                json_output: Whether to format the output as JSON
                
            Returns:
                The result of the kubectl command execution
            """
            return await _kubectl(self, command, timeout, json_output)
                
        @self.server.tool()
        async def dummy_tool() -> str:
            """
            A dummy tool that does nothing.
            Used to ensure the server returns at least one tool.
            """
            return "This is a dummy tool that does nothing."


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
        try:
            await self.server.run_stdio_async()
        except Exception as e:
            logger.exception(f"Error while serving: {e}")
            raise
        finally:
            # Clean up resources when the server shuts down
            await self.bundle_manager.cleanup()
            
            
# Tool implementation functions exposed for testing

async def _initialize_bundle(server, source: str, force: bool = False) -> str:
    """
    Initialize a Kubernetes support bundle for analysis.
    
    Args:
        server: The server instance
        source: The source of the bundle (URL or local path)
        force: Whether to force re-initialization if a bundle is already active
        
    Returns:
        A message with the bundle initialization status
    """
    try:
        result = await server.bundle_manager.initialize_bundle(source, force)

        # Convert the metadata to a dictionary
        metadata_dict = json.loads(result.model_dump_json())

        # Format paths as strings
        metadata_dict["path"] = str(metadata_dict["path"])
        metadata_dict["kubeconfig_path"] = str(metadata_dict["kubeconfig_path"])

        return f"Bundle initialized successfully:\n```json\n{json.dumps(metadata_dict, indent=2)}\n```"

    except BundleManagerError as e:
        error_message = f"Failed to initialize bundle: {str(e)}"
        logger.error(error_message)
        return error_message
    except Exception as e:
        error_message = f"Unexpected error initializing bundle: {str(e)}"
        logger.exception(error_message)
        return error_message
        
async def _kubectl(server, command: str, timeout: int = 30, json_output: bool = True) -> str:
    """
    Execute kubectl commands against the initialized bundle's API server.
    
    Args:
        server: The server instance
        command: The kubectl command to execute
        timeout: Timeout in seconds for the command
        json_output: Whether to format the output as JSON
        
    Returns:
        The result of the kubectl command execution
    """
    try:
        result = await server.kubectl_executor.execute(command, timeout, json_output)
        
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
        
        return response
        
    except KubectlError as e:
        error_message = f"kubectl command failed: {str(e)}"
        logger.error(error_message)
        return error_message
    except BundleManagerError as e:
        error_message = f"Bundle error: {str(e)}"
        logger.error(error_message)
        return error_message
    except Exception as e:
        error_message = f"Unexpected error executing kubectl command: {str(e)}"
        logger.exception(error_message)
        return error_message
        
# Expose the tools for testing
initialize_bundle = lambda source, force=False: _initialize_bundle(None, source, force)
kubectl = lambda command, timeout=30, json_output=True: _kubectl(None, command, timeout, json_output)
dummy_tool = lambda: "This is a dummy tool that does nothing."
