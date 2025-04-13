#!/usr/bin/env python3
"""
FastMCP Stdio Lifecycle Example
Demonstrates how to implement lifecycle management with stdio communication in FastMCP
"""
import asyncio
import logging
import os
import signal
import sys
import time
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP

# Configure logging to stderr (critical for stdio mode)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,  # Must use stderr in stdio mode
)
logger = logging.getLogger("mcp-lifecycle")


@asynccontextmanager
async def app_lifespan(_server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """
    Lifecycle manager for the application
    This function handles:
    1. Resource initialization during startup
    2. Resource cleanup during shutdown
    """
    # === STARTUP PHASE ===
    logger.info("🚀 Server is starting up")
    start_time = time.time()
    
    # Initialize resources (example)
    temp_files = {}
    background_tasks = {}
    
    # Create a temp file to demonstrate resource tracking
    temp_file_path = "/app/temp_data.txt"  # Use absolute path for clarity
    with open(temp_file_path, "w") as f:
        f.write("Temporary data")
    temp_files["data"] = temp_file_path
    logger.info(f"Created temporary file: {temp_file_path}")
    
    # Start a background task
    cleanup_task = asyncio.create_task(periodic_cleanup())
    background_tasks["cleanup"] = cleanup_task
    logger.info("Started background cleanup task")
    
    # Create context to share with tools
    context = {
        "start_time": start_time,
        "temp_files": temp_files,
        "background_tasks": background_tasks,
    }
    
    try:
        # Yield context to FastMCP - execution pauses here until shutdown
        yield context
    finally:
        # === SHUTDOWN PHASE ===
        # This code runs when the server is stopping
        elapsed = time.time() - start_time
        logger.info(f"🛑 Server is shutting down after running for {elapsed:.2f} seconds")
        
        # Cancel background tasks
        for name, task in background_tasks.items():
            if not task.done():
                logger.info(f"Cancelling background task: {name}")
                task.cancel()
                try:
                    # Wait with timeout
                    await asyncio.wait_for(asyncio.shield(task), timeout=2.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    logger.info(f"Task {name} cancelled")
        
        # Clean up temp files
        for name, path in temp_files.items():
            if os.path.exists(path):
                logger.info(f"Removing temporary file: {path}")
                try:
                    os.remove(path)
                except OSError as e:
                    logger.error(f"Failed to remove temp file {path}: {e}")
        
        logger.info("✅ Cleanup completed")


async def periodic_cleanup():
    """Example background task that runs periodically"""
    logger.info("Starting periodic cleanup task")
    try:
        while True:
            await asyncio.sleep(60)  # Run every minute
            logger.info("Performing periodic cleanup")
    except asyncio.CancelledError:
        logger.info("Cleanup task cancelled")
        raise


# Create FastMCP server with lifespan context manager and stdio mode
mcp = FastMCP(
    "MCP Troubleshoot Server", 
    lifespan=app_lifespan,
    use_stdio=True  # Enable stdio communication
)


@mcp.tool()
def list_bundles(ctx: Context) -> List[str]:
    """Example tool that uses the lifespan context"""
    # Access the shared context
    lifespan_ctx = ctx.request_context.lifespan_context
    uptime = time.time() - lifespan_ctx["start_time"]
    
    logger.info(f"list_bundles called (uptime: {uptime:.2f}s)")
    return ["example-bundle-1.tar.gz", "example-bundle-2.tar.gz"]


@mcp.tool()
def echo(ctx: Context, message: str) -> str:
    """Simple echo tool for testing"""
    logger.info(f"Echo received: {message!r}")
    return f"ECHO: {message}"


def handle_signal(signum, frame):
    """Handle termination signals for graceful shutdown"""
    sig_name = signal.Signals(signum).name
    logger.info(f"Received signal {sig_name} ({signum}). Initiating shutdown...")
    sys.exit(0)  # This will trigger the finally block in the context manager


if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    
    logger.info("Starting MCP server with stdio communication...")
    
    try:
        # Run the FastMCP server
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.exception(f"Error running server: {e}")
    finally:
        logger.info("Server has fully shut down.")