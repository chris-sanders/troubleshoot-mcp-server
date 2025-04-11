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
