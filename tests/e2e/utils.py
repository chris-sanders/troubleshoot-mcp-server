"""
Utility functions for end-to-end tests.

These functions help with environment detection, resource cleanup,
and other common operations needed by e2e tests.
"""

import os
import platform
import subprocess
from pathlib import Path
from typing import Tuple, Dict, Any


# CI detection functions removed - tests should behave consistently regardless of environment


def get_container_runtime() -> Tuple[str, bool]:
    """
    Determine which container runtime is available.

    Returns:
        Tuple[str, bool]: A tuple of (runtime_name, is_available) where:
          - runtime_name is "podman" or "docker"
          - is_available is a boolean indicating if the runtime is available
    """
    # Check for Podman first (preferred)
    try:
        result = subprocess.run(
            ["podman", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return "podman", True
    except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fall back to Docker
    try:
        result = subprocess.run(
            ["docker", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return "docker", True
    except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # No container runtime available
    return "podman", False


def get_project_root() -> Path:
    """
    Get the absolute path to the project root directory.

    Returns:
        Path: The absolute path to the project root
    """
    # Go up two levels from this file (tests/e2e -> tests -> project root)
    return Path(__file__).parents[2].absolute()


def get_system_info() -> Dict[str, Any]:
    """
    Get information about the system running the tests.

    Returns:
        Dict[str, Any]: Dictionary with system information
    """
    info = {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
    }

    # Add container runtime info
    runtime, available = get_container_runtime()
    info["container_runtime"] = runtime
    info["container_available"] = available

    return info


# should_skip_in_ci function removed - tests should pass consistently everywhere


def sanitize_container_name(name: str) -> str:
    """
    Ensure container name is valid across different container runtimes.

    Args:
        name: The proposed container name

    Returns:
        str: A sanitized container name
    """
    # Replace any characters that might cause issues
    sanitized = name.replace(" ", "_").replace("/", "_").replace(":", "_")

    # Ensure it starts with a letter
    if not sanitized[0].isalpha():
        sanitized = "c_" + sanitized

    # Limit length (most container runtimes have length limits)
    if len(sanitized) > 63:
        sanitized = sanitized[:63]

    return sanitized
