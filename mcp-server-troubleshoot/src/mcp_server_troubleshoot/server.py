"""
MCP server implementation for Kubernetes support bundles.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp import Tool
from mcp.types import TextContent

from .bundle import BundleManager, BundleManagerError, InitializeBundleArgs
from .kubectl import KubectlError, KubectlExecutor, KubectlCommandArgs
from .files import FileExplorer, FileSystemError, GrepFilesArgs, ListFilesArgs, ReadFileArgs

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
        self.file_explorer = FileExplorer(self.bundle_manager)
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
                ),
                Tool(
                    name="list_files",
                    description="List files and directories within the support bundle",
                    inputSchema=ListFilesArgs.model_json_schema(),
                ),
                Tool(
                    name="read_file",
                    description="Read a file within the support bundle with optional line range filtering",
                    inputSchema=ReadFileArgs.model_json_schema(),
                ),
                Tool(
                    name="grep_files",
                    description="Search for patterns in files within the support bundle",
                    inputSchema=GrepFilesArgs.model_json_schema(),
                ),
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
            elif name == "list_files":
                return await self._handle_list_files(arguments)
            elif name == "read_file":
                return await self._handle_read_file(arguments)
            elif name == "grep_files":
                return await self._handle_grep_files(arguments)

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
                args.command, args.timeout, args.json_output
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
                "duration_ms": result.duration_ms,
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

    async def _handle_list_files(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """
        Handle the list_files tool call.

        Args:
            arguments: The arguments for the tool call

        Returns:
            A list of content items to return to the model
        """
        try:
            args = ListFilesArgs(**arguments)
            result = await self.file_explorer.list_files(args.path, args.recursive)

            # Format the response
            response = (
                f"Listed files in {result.path} "
                + ("recursively" if result.recursive else "non-recursively")
                + ":\n"
            )

            # Format the entries
            entries_data = [entry.model_dump() for entry in result.entries]
            entries_json = json.dumps(entries_data, indent=2)
            response += f"```json\n{entries_json}\n```\n"

            # Add metadata
            metadata = {
                "path": result.path,
                "recursive": result.recursive,
                "total_files": result.total_files,
                "total_dirs": result.total_dirs,
            }
            metadata_str = json.dumps(metadata, indent=2)
            response += f"Directory metadata:\n```json\n{metadata_str}\n```"

            return [TextContent(type="text", text=response)]

        except FileSystemError as e:
            error_message = f"File system error: {str(e)}"
            logger.error(error_message)
            return [TextContent(type="text", text=error_message)]
        except BundleManagerError as e:
            error_message = f"Bundle error: {str(e)}"
            logger.error(error_message)
            return [TextContent(type="text", text=error_message)]
        except Exception as e:
            error_message = f"Unexpected error listing files: {str(e)}"
            logger.exception(error_message)
            return [TextContent(type="text", text=error_message)]

    async def _handle_read_file(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """
        Handle the read_file tool call.

        Args:
            arguments: The arguments for the tool call

        Returns:
            A list of content items to return to the model
        """
        try:
            args = ReadFileArgs(**arguments)
            result = await self.file_explorer.read_file(args.path, args.start_line, args.end_line)

            # Format the response
            file_type = "binary" if result.binary else "text"

            # For text files, add line numbers
            if not result.binary:
                # Split the content into lines
                lines = result.content.splitlines()

                # Generate line numbers
                content_with_numbers = ""
                for i, line in enumerate(lines):
                    line_number = result.start_line + i
                    content_with_numbers += (
                        f"{line_number + 1:4d} | {line}\n"  # 1-indexed for display
                    )

                response = f"Read {file_type} file {result.path} (lines {result.start_line + 1}-{result.end_line + 1} of {result.total_lines}):\n"
                response += f"```\n{content_with_numbers}```"
            else:
                # For binary files, just show the hex dump
                response = f"Read {file_type} file {result.path} (binary data shown as hex):\n"
                response += f"```\n{result.content}\n```"

            return [TextContent(type="text", text=response)]

        except FileSystemError as e:
            error_message = f"File system error: {str(e)}"
            logger.error(error_message)
            return [TextContent(type="text", text=error_message)]
        except BundleManagerError as e:
            error_message = f"Bundle error: {str(e)}"
            logger.error(error_message)
            return [TextContent(type="text", text=error_message)]
        except Exception as e:
            error_message = f"Unexpected error reading file: {str(e)}"
            logger.exception(error_message)
            return [TextContent(type="text", text=error_message)]

    async def _handle_grep_files(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """
        Handle the grep_files tool call.

        Args:
            arguments: The arguments for the tool call

        Returns:
            A list of content items to return to the model
        """
        try:
            args = GrepFilesArgs(**arguments)
            result = await self.file_explorer.grep_files(
                args.pattern,
                args.path,
                args.recursive,
                args.glob_pattern,
                args.case_sensitive,
                args.max_results,
            )

            # Format the response
            pattern_type = "case-sensitive" if result.case_sensitive else "case-insensitive"
            path_desc = result.path + (
                f" (matching {result.glob_pattern})" if result.glob_pattern else ""
            )

            response = f"Found {result.total_matches} matches for {pattern_type} pattern '{result.pattern}' in {path_desc}:\n\n"

            # If we have matches, show them
            if result.matches:
                # Group matches by file
                matches_by_file = {}
                for match in result.matches:
                    if match.path not in matches_by_file:
                        matches_by_file[match.path] = []
                    matches_by_file[match.path].append(match)

                # Format the matches
                for file_path, matches in matches_by_file.items():
                    response += f"**File: {file_path}**\n```\n"
                    for match in matches:
                        response += (
                            f"{match.line_number + 1:4d} | {match.line}\n"  # 1-indexed for display
                        )
                    response += "```\n\n"

                # Add truncation notice if necessary
                if result.truncated:
                    response += f"_Note: Results truncated to {args.max_results} matches._\n\n"

            else:
                response += "No matches found.\n\n"

            # Add metadata
            metadata = {
                "pattern": result.pattern,
                "path": result.path,
                "glob_pattern": result.glob_pattern,
                "total_matches": result.total_matches,
                "files_searched": result.files_searched,
                "recursive": args.recursive,
                "case_sensitive": result.case_sensitive,
                "truncated": result.truncated,
            }
            metadata_str = json.dumps(metadata, indent=2)
            response += f"Search metadata:\n```json\n{metadata_str}\n```"

            return [TextContent(type="text", text=response)]

        except FileSystemError as e:
            error_message = f"File system error: {str(e)}"
            logger.error(error_message)
            return [TextContent(type="text", text=error_message)]
        except BundleManagerError as e:
            error_message = f"Bundle error: {str(e)}"
            logger.error(error_message)
            return [TextContent(type="text", text=error_message)]
        except Exception as e:
            error_message = f"Unexpected error searching files: {str(e)}"
            logger.exception(error_message)
            return [TextContent(type="text", text=error_message)]

    async def serve(self, mcp_mode: bool = False) -> None:
        """
        Start the MCP server using stdin/stdout for communication.

        Args:
            mcp_mode: Whether the server is running in MCP mode
        """
        logger.debug("Starting MCP server" + (" in MCP mode" if mcp_mode else ""))
        
        # Set up simplified streaming I/O directly with sys.stdin and sys.stdout
        input_stream = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(input_stream)
        loop = asyncio.get_event_loop()
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        
        # Create a StreamWriter for stdout
        transport, protocol = await loop.connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout
        )
        output_stream = asyncio.StreamWriter(transport, protocol, None, loop)
        
        # Check for keep-alive based on environment for MCP mode
        keep_alive = False
        if mcp_mode:
            keep_alive = os.environ.get("MCP_KEEP_ALIVE", "").lower() in ("true", "1", "yes")
            logger.debug(f"MCP mode keep_alive setting: {keep_alive}")
            
        try:
            # Process JSON-RPC requests in a loop
            while True:
                try:
                    # Read a line with appropriate timeout
                    timeout = 3600.0 if (mcp_mode and keep_alive) else 300.0
                    line = await asyncio.wait_for(input_stream.readline(), timeout=timeout)
                    
                    # Handle end of input
                    if not line:
                        logger.debug("End of input stream")
                        if mcp_mode and keep_alive:
                            logger.debug("Keep-alive active, waiting for reconnection")
                            await asyncio.sleep(5.0)
                            continue
                        break
                        
                except asyncio.TimeoutError:
                    logger.debug(f"Timeout reading from input stream (timeout={timeout}s)")
                    if mcp_mode and keep_alive:
                        logger.debug("Keep-alive active, continuing to wait")
                        continue
                    break

                try:
                    # Process the JSON-RPC request
                    request_str = line.decode("utf-8").strip()
                    logger.debug(f"Received: {request_str}")
                    request = json.loads(request_str)
                    
                    # Use our helper method to handle the request
                    response = await self._process_jsonrpc(request)
                    
                    # Write JSON-RPC to stdout and flush immediately
                    response_str = json.dumps(response) + "\n"
                    output_stream.write(response_str.encode("utf-8"))
                    await output_stream.drain()
                    logger.debug(f"Sent: {response_str.strip()}")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    # Send a properly formatted JSON-RPC error
                    error = {
                        "jsonrpc": "2.0",
                        "error": {"code": -32700, "message": "Parse error"},
                        "id": None
                    }
                    output_stream.write((json.dumps(error) + "\n").encode("utf-8"))
                    await output_stream.drain()
                    
                except Exception as e:
                    logger.exception(f"Error processing request: {e}")
                    # Send a properly formatted JSON-RPC error
                    error = {
                        "jsonrpc": "2.0",
                        "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
                        "id": None
                    }
                    output_stream.write((json.dumps(error) + "\n").encode("utf-8"))
                    await output_stream.drain()
                    
        except asyncio.CancelledError:
            logger.info("Server task cancelled")
        except Exception as e:
            logger.exception(f"Unexpected error in serve loop: {e}")
        finally:
            # Clean up resources
            logger.debug("Cleaning up resources")
            if output_stream:
                try:
                    output_stream.close()
                except Exception as e:
                    logger.debug(f"Error closing output stream: {e}")

            try:
                await self.bundle_manager.cleanup()
            except Exception as e:
                logger.exception(f"Error during bundle manager cleanup: {e}")
    
# The _serve_manual_stdio method has been removed since we simplified
# the implementation and moved it directly into the serve() method

    async def _process_jsonrpc(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a JSON-RPC request.

        Args:
            request: The JSON-RPC request object

        Returns:
            A JSON-RPC response object
        """
        # Extract request details
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})
        
        # Ensure request_id is a string, number, or null to ensure valid JSON-RPC
        if request_id is not None and not isinstance(request_id, (str, int, float)):
            request_id = str(request_id)
        
        if method == "initialize":
            # Handle the initialize message from MCP Inspector
            logger.debug(f"Received initialize request with params: {params}")
            # Return a successful initialization response
            capabilities = {
                "toolCallHistorySupport": True,
                "textProcessingSupport": False,
                "imageProcessingSupport": False
            }
            return {"jsonrpc": "2.0", "result": {"capabilities": capabilities}, "id": request_id}
            
        elif method == "initialized":
            # Client confirms initialization is complete
            logger.debug("Received initialized notification")
            # This is typically a notification without an ID that doesn't require a response
            # But we'll respond anyway to be safe
            return {"jsonrpc": "2.0", "result": None, "id": request_id}

        elif method == "get_tool_definitions":
            # Get list of available tools manually since we can't directly access
            # the tools decorator in the server object
            tools = [
                {
                    "name": "initialize_bundle",
                    "description": "Initialize a Kubernetes support bundle for analysis",
                },
                {
                    "name": "kubectl",
                    "description": "Execute kubectl commands against the initialized bundle's API server",
                },
                {
                    "name": "list_files",
                    "description": "List files and directories within the support bundle",
                },
                {
                    "name": "read_file",
                    "description": "Read a file within the support bundle with optional line range filtering",
                },
                {
                    "name": "grep_files",
                    "description": "Search for patterns in files within the support bundle",
                },
            ]

            return {"jsonrpc": "2.0", "result": tools, "id": request_id}

        elif method == "call_tool":
            # Extract tool name and arguments
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if not tool_name:
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32602, "message": "Missing required parameter 'name'"},
                    "id": request_id,
                }

            # Call the tool and get the result
            try:
                # Check if the tool name is valid
                valid_tools = [
                    "initialize_bundle",
                    "kubectl",
                    "list_files",
                    "read_file",
                    "grep_files",
                ]
                if tool_name not in valid_tools:
                    return {
                        "jsonrpc": "2.0",
                        "error": {"code": -32601, "message": f"Tool '{tool_name}' not found"},
                        "id": request_id,
                    }

                # Forward to the actual implementation based on tool name
                if tool_name == "initialize_bundle":
                    result = await self._handle_initialize_bundle(arguments)
                elif tool_name == "kubectl":
                    result = await self._handle_kubectl(arguments)
                elif tool_name == "list_files":
                    result = await self._handle_list_files(arguments)
                elif tool_name == "read_file":
                    result = await self._handle_read_file(arguments)
                elif tool_name == "grep_files":
                    result = await self._handle_grep_files(arguments)
                else:
                    return {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32601,
                            "message": f"Tool '{tool_name}' handler not implemented",
                        },
                        "id": request_id,
                    }

                # Convert TextContent objects to a serializable format
                serializable_result = []
                for item in result:
                    # Handle TextContent objects directly
                    if hasattr(item, "type") and hasattr(item, "text"):
                        serializable_result.append({"type": item.type, "text": item.text})
                    elif hasattr(item, "model_dump"):
                        # For Pydantic models
                        serializable_result.append(item.model_dump())
                    elif hasattr(item, "to_dict"):
                        # For objects with to_dict method
                        serializable_result.append(item.to_dict())
                    elif hasattr(item, "__dict__"):
                        # For generic objects
                        serializable_result.append(vars(item))
                    else:
                        # For primitive types
                        serializable_result.append(str(item))

                return {"jsonrpc": "2.0", "result": serializable_result, "id": request_id}
            except Exception as e:
                logger.exception(f"Error calling tool '{tool_name}': {e}")
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": f"Error calling tool: {str(e)}"},
                    "id": request_id,
                }

        elif method == "shutdown":
            # Client is requesting shutdown
            logger.debug("Received shutdown request")
            # We'll respond with a success but won't exit yet - the client should send an 'exit' notification
            return {"jsonrpc": "2.0", "result": None, "id": request_id}
            
        elif method == "exit":
            # Client is requesting exit after shutdown
            logger.debug("Received exit notification")
            # This typically doesn't need a response as it's a notification
            # We'd normally exit here, but will let the main loop handle it
            return {"jsonrpc": "2.0", "result": None, "id": request_id}
            
        else:
            # Unknown method
            logger.warning(f"Unknown method requested: {method}")
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Method '{method}' not found"},
                "id": request_id,
            }
