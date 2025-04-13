"""
MCP server implementation for Kubernetes support bundles.
"""

import datetime
import json
import logging
from pathlib import Path
from typing import List, Optional

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

from .bundle import (
    BundleManager,
    BundleManagerError,
    InitializeBundleArgs,
    ListAvailableBundlesArgs,
)
from .kubectl import KubectlError, KubectlExecutor, KubectlCommandArgs
from .files import FileExplorer, FileSystemError, GrepFilesArgs, ListFilesArgs, ReadFileArgs

logger = logging.getLogger(__name__)

# Create FastMCP server
mcp = FastMCP("troubleshoot-mcp-server")

# Global instances for managers/executors
_bundle_manager = None
_kubectl_executor = None
_file_explorer = None


def get_bundle_manager(bundle_dir: Optional[Path] = None) -> BundleManager:
    """Get the bundle manager instance."""
    global _bundle_manager
    if _bundle_manager is None:
        _bundle_manager = BundleManager(bundle_dir)
    return _bundle_manager


def get_kubectl_executor() -> KubectlExecutor:
    """Get the kubectl executor instance."""
    global _kubectl_executor
    if _kubectl_executor is None:
        _kubectl_executor = KubectlExecutor(get_bundle_manager())
    return _kubectl_executor


def get_file_explorer() -> FileExplorer:
    """Get the file explorer instance."""
    global _file_explorer
    if _file_explorer is None:
        _file_explorer = FileExplorer(get_bundle_manager())
    return _file_explorer


@mcp.tool()
async def initialize_bundle(args: InitializeBundleArgs) -> List[TextContent]:
    """
    Initialize a Kubernetes support bundle for analysis. This tool loads a bundle
    and makes it available for exploration with other tools.

    Args:
        args: Arguments containing:
            source: (string, required) The source of the bundle (URL or local file path)
            force: (boolean, optional) Whether to force re-initialization if a bundle
                is already active. Defaults to False.

    Returns:
        Metadata about the initialized bundle including path and kubeconfig location.
        If the API server is not available, also returns diagnostic information.
    """
    bundle_manager = get_bundle_manager()

    try:
        # Check if sbctl is available before attempting to initialize
        sbctl_available = await bundle_manager._check_sbctl_available()
        if not sbctl_available:
            error_message = "sbctl is not available in the environment. This is required for bundle initialization."
            logger.error(error_message)
            return [TextContent(type="text", text=error_message)]

        # Initialize the bundle
        result = await bundle_manager.initialize_bundle(args.source, args.force)

        # Convert the metadata to a dictionary
        metadata_dict = json.loads(result.model_dump_json())

        # Format paths as strings
        metadata_dict["path"] = str(metadata_dict["path"])
        metadata_dict["kubeconfig_path"] = str(metadata_dict["kubeconfig_path"])

        # Check if the API server is available
        api_server_available = await bundle_manager.check_api_server_available()

        # Get diagnostic information
        diagnostics = await bundle_manager.get_diagnostic_info()

        # Format response based on API server status
        if api_server_available:
            response = f"Bundle initialized successfully:\n```json\n{json.dumps(metadata_dict, indent=2)}\n```"
        else:
            response = (
                f"Bundle initialized but API server is NOT available. kubectl commands may fail:\n"
                f"```json\n{json.dumps(metadata_dict, indent=2)}\n```\n\n"
                f"Diagnostic information:\n```json\n{json.dumps(diagnostics, indent=2)}\n```"
            )

        return [TextContent(type="text", text=response)]

    except BundleManagerError as e:
        error_message = f"Failed to initialize bundle: {str(e)}"
        logger.error(error_message)

        # Try to get diagnostic information even on failure
        try:
            diagnostics = await bundle_manager.get_diagnostic_info()
            diagnostic_info = (
                f"\n\nDiagnostic information:\n```json\n{json.dumps(diagnostics, indent=2)}\n```"
            )
            error_message += diagnostic_info
        except Exception as diag_error:
            logger.error(f"Failed to get diagnostics: {diag_error}")

        return [TextContent(type="text", text=error_message)]
    except Exception as e:
        error_message = f"Unexpected error initializing bundle: {str(e)}"
        logger.exception(error_message)

        # Try to get diagnostic information even on failure
        try:
            diagnostics = await bundle_manager.get_diagnostic_info()
            diagnostic_info = (
                f"\n\nDiagnostic information:\n```json\n{json.dumps(diagnostics, indent=2)}\n```"
            )
            error_message += diagnostic_info
        except Exception as diag_error:
            logger.error(f"Failed to get diagnostics: {diag_error}")

        return [TextContent(type="text", text=error_message)]


@mcp.tool()
async def list_available_bundles(args: ListAvailableBundlesArgs) -> List[TextContent]:
    """
    Scan the bundle storage directory to find available compressed bundle files and list them.
    This tool helps discover which bundles are available for initialization.

    Args:
        args: Arguments containing:
            include_invalid: (boolean, optional) Whether to include invalid or inaccessible
                bundles in the results. Defaults to False.

    Returns:
        A list of available bundle files with details including path, size, and modification time.
        Bundles are validated to ensure they have the expected support bundle structure.
    """
    bundle_manager = get_bundle_manager()

    try:
        # List available bundles
        bundles = await bundle_manager.list_available_bundles(args.include_invalid)

        if not bundles:
            return [
                TextContent(
                    type="text",
                    text="No support bundles found. You may need to download or transfer a bundle to the bundle storage directory.",
                )
            ]

        # Create structured JSON response for MCP clients
        bundle_list = []
        
        for bundle in bundles:
            # Format human-readable size
            size_str = ""
            if bundle.size_bytes < 1024:
                size_str = f"{bundle.size_bytes} B"
            elif bundle.size_bytes < 1024 * 1024:
                size_str = f"{bundle.size_bytes / 1024:.1f} KB"
            elif bundle.size_bytes < 1024 * 1024 * 1024:
                size_str = f"{bundle.size_bytes / (1024 * 1024):.1f} MB"
            else:
                size_str = f"{bundle.size_bytes / (1024 * 1024 * 1024):.1f} GB"

            # Format modification time for human readability
            modified_time_str = datetime.datetime.fromtimestamp(bundle.modified_time).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            
            # Add bundle entry
            bundle_entry = {
                "name": bundle.name,
                "source": bundle.relative_path,  # Use relative path for initializing
                "full_path": bundle.path,
                "size_bytes": bundle.size_bytes,
                "size": size_str,
                "modified_time": bundle.modified_time,
                "modified": modified_time_str,
                "valid": bundle.valid,
            }
            
            if not bundle.valid and bundle.validation_message:
                bundle_entry["validation_message"] = bundle.validation_message
                
            bundle_list.append(bundle_entry)
            
        # Create response object
        response_obj = {
            "bundles": bundle_list,
            "total": len(bundle_list)
        }
        
        # Get example bundle for usage instructions
        example_bundle = next((b for b in bundles if b.valid), bundles[0] if bundles else None)
        
        # Create response text with JSON result and usage instructions
        response = f"```json\n{json.dumps(response_obj, indent=2)}\n```\n\n"
        
        if example_bundle:
            response += "## Usage Instructions\n\n"
            response += "To use one of these bundles, initialize it with the `initialize_bundle` tool using the `source` value:\n\n"
            response += '```json\n{\n  "source": "' + example_bundle.relative_path + '"\n}\n```\n\n'
            response += "After initializing a bundle, you can explore its contents using the file exploration tools (`list_files`, `read_file`, `grep_files`) and run kubectl commands with the `kubectl` tool."

        return [TextContent(type="text", text=response)]

    except BundleManagerError as e:
        error_message = f"Failed to list bundles: {str(e)}"
        logger.error(error_message)
        return [TextContent(type="text", text=error_message)]
    except Exception as e:
        error_message = f"Unexpected error listing bundles: {str(e)}"
        logger.exception(error_message)
        return [TextContent(type="text", text=error_message)]


@mcp.tool()
async def kubectl(args: KubectlCommandArgs) -> List[TextContent]:
    """
    Execute kubectl commands against the initialized bundle's API server. Allows
    running Kubernetes CLI commands to explore resources in the support bundle.

    Args:
        args: Arguments containing:
            command: (string, required) The kubectl command to execute (e.g., "get pods",
                "get nodes -o wide", "describe deployment nginx")
            timeout: (integer, optional) Timeout in seconds for the command. Defaults to 30.
            json_output: (boolean, optional) Whether to format the output as JSON.
                Defaults to True. Set to False for plain text output.

    Returns:
        The formatted output from the kubectl command, along with execution metadata
        including exit code and execution time. Returns error and diagnostic
        information if the command fails or API server is not available.
    """
    bundle_manager = get_bundle_manager()

    try:
        # Check if the API server is available before attempting kubectl
        api_server_available = await bundle_manager.check_api_server_available()
        if not api_server_available:
            # Get diagnostic information
            diagnostics = await bundle_manager.get_diagnostic_info()
            error_message = (
                "Kubernetes API server is not available. kubectl commands cannot be executed.\n\n"
                f"Diagnostic information:\n```json\n{json.dumps(diagnostics, indent=2)}\n```\n\n"
                "Try reinitializing the bundle with the initialize_bundle tool."
            )
            logger.error("API server not available for kubectl command")
            return [TextContent(type="text", text=error_message)]

        # Execute the kubectl command
        result = await get_kubectl_executor().execute(args.command, args.timeout, args.json_output)

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

        # Try to get diagnostic information for the API server
        try:
            diagnostics = await bundle_manager.get_diagnostic_info()

            # Check if this is a connection issue
            if "connection refused" in str(e).lower() or "could not connect" in str(e).lower():
                error_message += (
                    "\n\nThis appears to be a connection issue with the Kubernetes API server. "
                    "The API server may not be running properly.\n\n"
                    f"Diagnostic information:\n```json\n{json.dumps(diagnostics, indent=2)}\n```\n\n"
                    "Try reinitializing the bundle with the initialize_bundle tool."
                )
            else:
                error_message += f"\n\nDiagnostic information:\n```json\n{json.dumps(diagnostics, indent=2)}\n```"
        except Exception as diag_error:
            logger.error(f"Failed to get diagnostics: {diag_error}")

        return [TextContent(type="text", text=error_message)]
    except BundleManagerError as e:
        error_message = f"Bundle error: {str(e)}"
        logger.error(error_message)

        # Try to get diagnostic information
        try:
            diagnostics = await bundle_manager.get_diagnostic_info()
            error_message += (
                f"\n\nDiagnostic information:\n```json\n{json.dumps(diagnostics, indent=2)}\n```"
            )
        except Exception as diag_error:
            logger.error(f"Failed to get diagnostics: {diag_error}")

        return [TextContent(type="text", text=error_message)]
    except Exception as e:
        error_message = f"Unexpected error executing kubectl command: {str(e)}"
        logger.exception(error_message)

        # Try to get diagnostic information
        try:
            diagnostics = await bundle_manager.get_diagnostic_info()
            error_message += (
                f"\n\nDiagnostic information:\n```json\n{json.dumps(diagnostics, indent=2)}\n```"
            )
        except Exception as diag_error:
            logger.error(f"Failed to get diagnostics: {diag_error}")

        return [TextContent(type="text", text=error_message)]


@mcp.tool()
async def list_files(args: ListFilesArgs) -> List[TextContent]:
    """
    List files and directories within the support bundle. This tool lets you
    explore the directory structure of the initialized bundle.

    IMPORTANT: This tool requires a bundle to be initialized first using the `initialize_bundle` tool.
    If no bundle is initialized, use the `list_available_bundles` tool to find available bundles.

    Args:
        args: Arguments containing:
            path: (string, required) The path within the bundle to list. Use "" or "/"
                for root directory. Path cannot contain directory traversal (e.g., "../").
            recursive: (boolean, optional) Whether to list files and directories recursively.
                Defaults to False. Set to True to show nested files.

    Returns:
        A JSON list of entries with file/directory information including name, path, type
        (file or dir), size, access time, modification time, and whether binary.
        Also returns metadata about the directory listing like total file and directory counts.
    """
    try:
        result = await get_file_explorer().list_files(args.path, args.recursive)

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


@mcp.tool()
async def read_file(args: ReadFileArgs) -> List[TextContent]:
    """
    Read a file within the support bundle with optional line range filtering.
    Displays file content with line numbers.

    IMPORTANT: This tool requires a bundle to be initialized first using the `initialize_bundle` tool.
    If no bundle is initialized, use the `list_available_bundles` tool to find available bundles.

    Args:
        args: Arguments containing:
            path: (string, required) The path to the file within the bundle to read.
                Path cannot contain directory traversal (e.g., "../").
            start_line: (integer, optional) The line number to start reading from (0-indexed).
                Defaults to 0 (the first line).
            end_line: (integer or null, optional) The line number to end reading at
                (0-indexed, inclusive). Defaults to null, which means read to the end of the file.

    Returns:
        The content of the file with line numbers. For text files, displays the
        specified line range with line numbers. For binary files, displays a hex dump.
    """
    try:
        result = await get_file_explorer().read_file(args.path, args.start_line, args.end_line)

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
                content_with_numbers += f"{line_number + 1:4d} | {line}\n"  # 1-indexed for display

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


@mcp.tool()
async def grep_files(args: GrepFilesArgs) -> List[TextContent]:
    """
    Search for patterns in files within the support bundle. Searches both file content
    and filenames, making it useful for finding keywords, error messages, or identifying files.

    IMPORTANT: This tool requires a bundle to be initialized first using the `initialize_bundle` tool.
    If no bundle is initialized, use the `list_available_bundles` tool to find available bundles.

    Args:
        args: Arguments containing:
            pattern: (string, required) The pattern to search for. Supports regex syntax.
            path: (string, required) The path within the bundle to search. Use "" or "/"
                to search from root. Path cannot contain directory traversal (e.g., "../").
            recursive: (boolean, optional) Whether to search recursively in subdirectories.
                Defaults to True.
            glob_pattern: (string or null, optional) File pattern to filter which files
                to search (e.g., "*.yaml", "*.{json,log}"). Defaults to null (search all files).
            case_sensitive: (boolean, optional) Whether the search is case-sensitive.
                Defaults to False (case-insensitive search).
            max_results: (integer, optional) Maximum number of results to return.
                Defaults to 1000.

    Returns:
        Matches found in file contents and filenames, grouped by file.
        Also includes search metadata such as the number of files searched
        and the total number of matches found.
    """
    try:
        result = await get_file_explorer().grep_files(
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


# Helper function to initialize the bundle manager with a specified directory
def initialize_with_bundle_dir(bundle_dir: Optional[Path] = None) -> None:
    """
    Initialize the bundle manager with a specific directory.

    Args:
        bundle_dir: The directory to use for bundle storage
    """
    get_bundle_manager(bundle_dir)
