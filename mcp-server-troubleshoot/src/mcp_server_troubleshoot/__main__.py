"""
Entry point for the MCP server.
"""

import argparse
import asyncio
import logging
import sys
from typing import List, Optional

from .server import TroubleshootMCPServer

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False, mcp_mode: bool = False) -> None:
    """
    Set up logging configuration.

    Args:
        verbose: Whether to enable verbose logging
        mcp_mode: Whether the server is running in MCP mode
    """
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


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command line arguments.

    Args:
        args: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="MCP server for Kubernetes support bundles")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--bundle-dir", type=str, help="Directory to store support bundles")
    return parser.parse_args(args)


async def run_server(args: argparse.Namespace, mcp_mode: bool = False) -> None:
    """
    Run the MCP server.

    Args:
        args: Command line arguments
        mcp_mode: Whether the server is running in MCP mode
    """
    setup_logging(args.verbose, mcp_mode)

    bundle_dir = None
    if args.bundle_dir:
        from pathlib import Path

        bundle_dir = Path(args.bundle_dir)
        bundle_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using bundle directory: {bundle_dir}")

    logger.info("Starting MCP server for Kubernetes support bundles")
    server = TroubleshootMCPServer(bundle_dir=bundle_dir)
    await server.serve(mcp_mode=mcp_mode)


def main(args: Optional[List[str]] = None) -> None:
    """
    Main entry point for the application.

    Args:
        args: Command line arguments (defaults to sys.argv[1:])
    """
    parsed_args = parse_args(args)
    
    # Detect if we're running in MCP mode (stdin is not a terminal)
    mcp_mode = not sys.stdin.isatty()

    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_server(parsed_args, mcp_mode=mcp_mode))
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.exception(f"Error running server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
