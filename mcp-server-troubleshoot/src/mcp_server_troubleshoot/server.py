"""
MCP server implementation for Kubernetes support bundles.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

from .bundle import BundleManager, BundleManagerError, InitializeBundleArgs
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
    Initialize a Kubernetes support bundle for analysis.

    Args:
        args: The initialization arguments containing source and force flag

    Returns:
        A list of content items to return to the model
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
            response = (
                f"Bundle initialized successfully:\n```json\n{json.dumps(metadata_dict, indent=2)}\n```"
            )
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
            diagnostic_info = f"\n\nDiagnostic information:\n```json\n{json.dumps(diagnostics, indent=2)}\n```"
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
            diagnostic_info = f"\n\nDiagnostic information:\n```json\n{json.dumps(diagnostics, indent=2)}\n```"
            error_message += diagnostic_info
        except Exception as diag_error:
            logger.error(f"Failed to get diagnostics: {diag_error}")
            
        return [TextContent(type="text", text=error_message)]


@mcp.tool()
async def kubectl(args: KubectlCommandArgs) -> List[TextContent]:
    """
    Execute kubectl commands against the initialized bundle's API server.

    Args:
        args: The kubectl command arguments

    Returns:
        A list of content items to return to the model
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
            error_message += f"\n\nDiagnostic information:\n```json\n{json.dumps(diagnostics, indent=2)}\n```"
        except Exception as diag_error:
            logger.error(f"Failed to get diagnostics: {diag_error}")
            
        return [TextContent(type="text", text=error_message)]
    except Exception as e:
        error_message = f"Unexpected error executing kubectl command: {str(e)}"
        logger.exception(error_message)
        
        # Try to get diagnostic information
        try:
            diagnostics = await bundle_manager.get_diagnostic_info()
            error_message += f"\n\nDiagnostic information:\n```json\n{json.dumps(diagnostics, indent=2)}\n```"
        except Exception as diag_error:
            logger.error(f"Failed to get diagnostics: {diag_error}")
            
        return [TextContent(type="text", text=error_message)]


@mcp.tool()
async def list_files(args: ListFilesArgs) -> List[TextContent]:
    """
    List files and directories within the support bundle.

    Args:
        args: The list files arguments

    Returns:
        A list of content items to return to the model
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

    Args:
        args: The read file arguments

    Returns:
        A list of content items to return to the model
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
    Search for patterns in files within the support bundle.

    Args:
        args: The grep files arguments

    Returns:
        A list of content items to return to the model
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
