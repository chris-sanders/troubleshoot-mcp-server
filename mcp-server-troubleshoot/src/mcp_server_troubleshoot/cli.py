"""
CLI entry points for the MCP server.
"""

import asyncio
import logging
import sys
from pathlib import Path
import argparse
import os

from .server import TroubleshootMCPServer

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False, mcp_mode: bool = False) -> None:
    """
    Set up logging configuration.

    Args:
        verbose: Whether to enable verbose logging
        mcp_mode: Whether the server is running in MCP mode
    """
    # Set log level based on environment, verbose flag, and mode
    if mcp_mode and not verbose:
        # In MCP mode, use ERROR or the level from env var
        env_log_level = os.environ.get("MCP_LOG_LEVEL", "ERROR").upper()
        log_levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO, 
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        log_level = log_levels.get(env_log_level, logging.ERROR)
    else:
        # In normal mode or verbose mode, use normal levels
        log_level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )
    
    # When in MCP mode, ensure all loggers use stderr
    if mcp_mode:
        # Configure root logger to use stderr
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            handler.stream = sys.stderr


async def serve_stdio(bundle_dir: Path = None, verbose: bool = False, mcp_mode: bool = True) -> None:
    """
    Serve the MCP server over stdio.

    Args:
        bundle_dir: Directory to store bundles
        verbose: Whether to enable verbose logging
        mcp_mode: Whether the server is running in MCP mode (default True)
    """
    setup_logging(verbose, mcp_mode)

    # Initialize the server
    logger.info("Starting MCP server for Kubernetes support bundles")
    if bundle_dir:
        logger.info(f"Using bundle directory: {bundle_dir}")

    try:
        # Create the server with the specified bundle directory
        server = TroubleshootMCPServer(bundle_dir=bundle_dir)

        # Start the server using stdio for communication
        await server.serve(mcp_mode=mcp_mode)

    except Exception as e:
        logger.exception(f"Error while serving: {e}")
        sys.exit(1)


def parse_args():
    """Parse command-line arguments for the MCP server."""
    parser = argparse.ArgumentParser(description="MCP server for Kubernetes support bundles")
    parser.add_argument("--bundle-dir", type=Path, help="Directory to store bundles")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    return parser.parse_args()


def serve_main(mcp_mode: bool = False):
    """
    Entry point for the serve command.
    
    Args:
        mcp_mode: Whether the server is running in MCP mode
    """
    args = parse_args()

    # Use the specified bundle directory or the default from environment
    bundle_dir = args.bundle_dir
    if not bundle_dir:
        env_bundle_dir = os.environ.get("MCP_BUNDLE_STORAGE")
        if env_bundle_dir:
            bundle_dir = Path(env_bundle_dir)

    # If still no bundle directory, use the default /data/bundles in container
    if not bundle_dir and os.path.exists("/data/bundles"):
        bundle_dir = Path("/data/bundles")

    # Start the server
    try:
        asyncio.run(serve_stdio(bundle_dir=bundle_dir, verbose=args.verbose, mcp_mode=mcp_mode))
    except KeyboardInterrupt:
        logger.info("Server interrupted, shutting down")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)


def main():
    """
    Main entry point that adapts based on how it's called.
    This allows the module to be used both as a direct CLI and
    as an MCP server that responds to JSON-RPC over stdio.
    """
    # Check if stdin has data (which means it's being piped to)
    if not sys.stdin.isatty():
        # Run in MCP server mode to handle the piped input
        serve_main(mcp_mode=True)
    else:
        # Run in normal CLI mode
        # It's okay to log to stdout in non-MCP mode
        setup_logging(verbose=False, mcp_mode=False)
        logger.info("Starting MCP server in interactive mode...")
        serve_main(mcp_mode=False)


# Entry point when run as a module
if __name__ == "__main__":
    main()
