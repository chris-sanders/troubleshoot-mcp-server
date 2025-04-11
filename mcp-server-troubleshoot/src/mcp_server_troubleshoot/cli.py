"""
CLI entry points for the MCP server.
"""

import asyncio
import logging
import sys
from pathlib import Path

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


async def serve_stdio(bundle_dir: Path = None, verbose: bool = False) -> None:
    """
    Serve the MCP server over stdio.

    Args:
        bundle_dir: Directory to store bundles
        verbose: Whether to enable verbose logging
    """
    setup_logging(verbose)

    logger.info("Starting MCP server for Kubernetes support bundles")
    server = TroubleshootMCPServer(bundle_dir=bundle_dir)

    # Create standard IO streams
    loop = asyncio.get_running_loop()
    
    # Create reader from stdin
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    
    # Create writer for stdout
    transport, protocol = await loop.connect_write_pipe(
        asyncio.streams.FlowControlMixin, sys.stdout
    )
    writer = asyncio.StreamWriter(transport, protocol, reader, loop)

    try:
        await server.serve(reader, writer)
    except Exception as e:
        logger.exception(f"Error while serving: {e}")
        sys.exit(1)
    finally:
        writer.close()
        await writer.wait_closed()


def serve():
    """
    Entry point for the serve command.
    """
    asyncio.run(serve_stdio())