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


def is_ci_environment() -> bool:
    """
    Detect if tests are running in a continuous integration environment.

    Returns:
        bool: True if running in a CI environment, False otherwise
    """
    # Check common CI environment variables
    ci_env_vars = [
        "GITHUB_ACTIONS",
        "GITLAB_CI",
        "CIRCLECI",
        "TRAVIS",
        "JENKINS_URL",
        "CI",
    ]

    return any(os.environ.get(var) for var in ci_env_vars)


def is_github_actions() -> bool:
    """
    Detect if tests are running in GitHub Actions.

    Returns:
        bool: True if running in GitHub Actions, False otherwise
    """
    return os.environ.get("GITHUB_ACTIONS") == "true"


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
        "in_ci": is_ci_environment(),
        "in_github_actions": is_github_actions(),
    }

    # Add container runtime info
    runtime, available = get_container_runtime()
    info["container_runtime"] = runtime
    info["container_available"] = available

    return info


def should_skip_in_ci(test_name: str) -> Tuple[bool, str]:
    """
    Determine if a test should be skipped in CI environments.

    Args:
        test_name: The name of the test function

    Returns:
        Tuple[bool, str]: A tuple of (should_skip, reason) where:
          - should_skip is a boolean indicating if the test should be skipped
          - reason is a string explaining why the test is skipped
    """
    # List of tests known to be problematic in CI
    problematic_tests = {
        # Tests that require volume mounting capabilities that may not be
        # available in all CI environments
        "test_volume_mounting": "Volume mounting tests are unreliable in CI environments",
        # Tests that are flaky in CI environments
        "test_mcp_server_startup": "Server startup tests can be flaky in CI due to resource constraints",
    }

    # Skip if in CI and test is in the problematic list
    if is_ci_environment() and test_name in problematic_tests:
        return True, problematic_tests[test_name]

    return False, ""


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
