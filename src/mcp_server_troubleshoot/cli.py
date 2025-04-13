"""
CLI entry points for the MCP server.
"""

import json
import logging
import sys
from pathlib import Path
import argparse
import os

from .server import mcp, initialize_with_bundle_dir
from .config import expand_client_config, load_config_from_env

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
            "CRITICAL": logging.CRITICAL,
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


def parse_args():
    """Parse command-line arguments for the MCP server."""
    parser = argparse.ArgumentParser(description="MCP server for Kubernetes support bundles")
    parser.add_argument("--bundle-dir", type=Path, help="Directory to store bundles")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--expand-config",
        action="store_true",
        help="Expand MCP client config with defaults and print to stdout",
    )

    return parser.parse_args()


def handle_expand_config():
    """Handle the expand-config command by reading from env and printing expanded config."""
    config = load_config_from_env()
    if not config:
        logger.error("No config found to expand. Set MCP_CONFIG_PATH environment variable.")
        sys.exit(1)

    expanded_config = expand_client_config(config)

    # Print the expanded config to stdout for the client to consume
    json.dump(expanded_config, sys.stdout)
    sys.exit(0)


def main():
    """
    Main entry point that adapts based on how it's called.
    This allows the module to be used both as a direct CLI and
    as an MCP server that responds to JSON-RPC over stdio.
    """
    args = parse_args()

    # Handle special commands first
    if args.expand_config:
        handle_expand_config()
        return  # This should never be reached as handle_expand_config exits

    # Set up logging based on whether we're in MCP mode
    mcp_mode = not sys.stdin.isatty()
    setup_logging(verbose=args.verbose, mcp_mode=mcp_mode)

    # Log information about startup
    if not mcp_mode:
        logger.info("Starting MCP server for Kubernetes support bundles")
    else:
        logger.debug("Starting MCP server for Kubernetes support bundles")

    # Use the specified bundle directory or the default from environment
    bundle_dir = args.bundle_dir
    if not bundle_dir:
        env_bundle_dir = os.environ.get("MCP_BUNDLE_STORAGE")
        if env_bundle_dir:
            bundle_dir = Path(env_bundle_dir)

    # If still no bundle directory, use the default /data/bundles in container
    if not bundle_dir and os.path.exists("/data/bundles"):
        bundle_dir = Path("/data/bundles")

    if bundle_dir:
        if not mcp_mode:
            logger.info(f"Using bundle directory: {bundle_dir}")
        else:
            logger.debug(f"Using bundle directory: {bundle_dir}")

    # Initialize bundle manager with the bundle directory
    initialize_with_bundle_dir(bundle_dir)

    # Run the FastMCP server - this handles stdin/stdout automatically
    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server interrupted, shutting down")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)


# Entry point when run as a module
if __name__ == "__main__":
    main()
