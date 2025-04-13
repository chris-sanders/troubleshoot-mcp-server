"""
Configuration utilities for MCP client integration.

This module provides tools to help with MCP client configuration, particularly
for containerized deployments. It enables simplified configurations with smart defaults
while maintaining full configurability for advanced use cases.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# Default configuration values
DEFAULT_IMAGE_NAME = "mcp-server-troubleshoot:latest"
DEFAULT_BUNDLE_STORAGE = "/data/bundles"
DEFAULT_ENTRYPOINT = "python"
DEFAULT_MODULE = "mcp_server_troubleshoot.cli"


def expand_client_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Expand a client configuration with smart defaults.

    This function takes a minimal MCP client configuration and expands it with
    sensible defaults for the troubleshoot server. This allows users to specify
    only the minimum required configuration in their client settings.

    Args:
        config: The original client configuration dictionary

    Returns:
        An expanded configuration with all required settings
    """
    if "mcpServers" not in config:
        logger.warning("Invalid MCP configuration: 'mcpServers' key missing")
        return config

    expanded_config = config.copy()

    for server_name, server_config in expanded_config["mcpServers"].items():
        # Skip non-troubleshoot servers
        if not _is_troubleshoot_server(server_config):
            continue

        # Apply our expansion logic
        expanded_config["mcpServers"][server_name] = _expand_server_config(server_config)

    return expanded_config


def _is_troubleshoot_server(server_config: Dict[str, Any]) -> bool:
    """Check if this is a troubleshoot MCP server configuration."""
    # Identify by command being docker and image name containing 'mcp-server-troubleshoot'
    if server_config.get("command") != "docker":
        return False

    # Check the args for the image name
    args = server_config.get("args", [])
    for arg in args:
        if isinstance(arg, str) and "mcp-server-troubleshoot" in arg:
            return True

    return False


def _expand_server_config(server_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Expand a server configuration with defaults.

    Args:
        server_config: The original server configuration

    Returns:
        The expanded server configuration
    """
    expanded_config = server_config.copy()

    # Get original args and extract useful information
    original_args = expanded_config.get("args", [])
    image_name = _extract_image_name(original_args) or DEFAULT_IMAGE_NAME

    # Get volume mount info
    bundle_dir = expanded_config.pop("bundleDir", None)
    if bundle_dir:
        volume_mount = f"{bundle_dir}:{DEFAULT_BUNDLE_STORAGE}"
    else:
        # Check if a volume mount already exists
        volume_mount = _extract_volume_mount(original_args) or None

    # Get environment variables
    env_dict = expanded_config.pop("env", {})
    existing_env_vars = _extract_env_vars(original_args)
    for key, value in existing_env_vars.items():
        if key not in env_dict:
            env_dict[key] = value

    # Ensure required environment variables
    if "MCP_BUNDLE_STORAGE" not in env_dict and DEFAULT_BUNDLE_STORAGE:
        env_dict["MCP_BUNDLE_STORAGE"] = DEFAULT_BUNDLE_STORAGE

    # If we have a keep_alive flag, use it, otherwise default to true
    if "MCP_KEEP_ALIVE" not in env_dict:
        env_dict["MCP_KEEP_ALIVE"] = "true"

    # Build new args list
    new_args = ["run", "-i"]

    # Add volume mount if we have one
    if volume_mount:
        new_args.extend(["-v", volume_mount])

    # Add environment variables
    for key, value in env_dict.items():
        new_args.extend(["-e", f"{key}={value}"])

    # Add standard Docker arguments
    new_args.append("--rm")

    # Add entrypoint if not already in original args
    if "--entrypoint" not in original_args:
        new_args.extend(["--entrypoint", DEFAULT_ENTRYPOINT])

    # Add the image name
    new_args.append(image_name)

    # Add the module invocation if not in original args
    if "-m" not in original_args:
        new_args.extend(["-m", DEFAULT_MODULE])

    # Update the server config
    expanded_config["args"] = new_args

    return expanded_config


def _extract_image_name(args: List[str]) -> Optional[str]:
    """Extract the image name from the args list."""
    # The image name is usually the last positional argument before any command
    # options, typically after "run", "-i", etc.
    for arg in args:
        if arg.startswith("mcp-server-troubleshoot"):
            return arg
    return None


def _extract_volume_mount(args: List[str]) -> Optional[str]:
    """Extract volume mount from the args list."""
    try:
        v_index = args.index("-v")
        if v_index + 1 < len(args):
            return args[v_index + 1]
    except ValueError:
        pass
    return None


def _extract_env_vars(args: List[str]) -> Dict[str, str]:
    """Extract environment variables from the args list."""
    env_vars = {}
    try:
        while True:
            e_index = args.index("-e")
            if e_index + 1 < len(args):
                env_var = args[e_index + 1]
                if "=" in env_var:
                    key, value = env_var.split("=", 1)
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    if value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    env_vars[key] = value
                args = args[e_index + 2 :]  # Continue search after this occurrence
            else:
                break
    except ValueError:
        pass  # No more -e flags
    return env_vars


def load_config_from_path(config_path: Union[str, Path]) -> Dict[str, Any]:
    """Load MCP configuration from a file path."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path, "r") as f:
        return json.load(f)


def load_config_from_env() -> Optional[Dict[str, Any]]:
    """Load MCP configuration from the MCP_CONFIG_PATH environment variable."""
    config_path = os.environ.get("MCP_CONFIG_PATH")
    if not config_path:
        return None

    try:
        return load_config_from_path(config_path)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load config from environment: {e}")
        return None
