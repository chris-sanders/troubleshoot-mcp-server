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


def setup_logging(verbose: bool = False) -> None:
    """
    Set up logging configuration.

    Args:
        verbose: Whether to enable verbose logging
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )


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


async def run_server(args: argparse.Namespace) -> None:
    """
    Run the MCP server.

    Args:
        args: Command line arguments
    """
    setup_logging(args.verbose)

    bundle_dir = None
    if args.bundle_dir:
        from pathlib import Path

        bundle_dir = Path(args.bundle_dir)
        bundle_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using bundle directory: {bundle_dir}")

    logger.info("Starting MCP server for Kubernetes support bundles")
    server = TroubleshootMCPServer(bundle_dir=bundle_dir)
    await server.serve()


def main(args: Optional[List[str]] = None) -> None:
    """
    Main entry point for the application.

    Args:
        args: Command line arguments (defaults to sys.argv[1:])
    """
    parsed_args = parse_args(args)

    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_server(parsed_args))
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.exception(f"Error running server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
