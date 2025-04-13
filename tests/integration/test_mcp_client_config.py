"""
Tests for MCP client configuration.
"""

import subprocess
import sys
import json
import pytest


@pytest.mark.integration
def test_cli_help():
    """Test that the CLI help works properly."""
    # Run the CLI with --help
    process = subprocess.run(
        [sys.executable, "-m", "mcp_server_troubleshoot", "--help"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    # Check that the command was successful
    assert process.returncode == 0, f"Command failed with stderr: {process.stderr}"

    # Verify the help output
    help_text = process.stdout.lower()
    assert "usage:" in help_text
    assert "bundle-dir" in help_text
    assert "show-config" in help_text


@pytest.mark.integration
def test_show_config():
    """Test that the show-config command works properly."""
    # Run the CLI with --show-config
    process = subprocess.run(
        [sys.executable, "-m", "mcp_server_troubleshoot", "--show-config"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    # Check that the command was successful
    assert process.returncode == 0, f"Command failed with stderr: {process.stderr}"

    # Verify the output is valid JSON
    config = json.loads(process.stdout)

    # Check for expected structure and values
    assert "mcpServers" in config
    assert "troubleshoot" in config["mcpServers"]
    assert config["mcpServers"]["troubleshoot"]["command"] == "docker"
    assert "--rm" in config["mcpServers"]["troubleshoot"]["args"]
    assert "MCP_BUNDLE_STORAGE=/data/bundles" in " ".join(
        config["mcpServers"]["troubleshoot"]["args"]
    )
