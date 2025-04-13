"""
Tests for the MCP client configuration system.
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Path to the test fixtures
FIXTURES_DIR = Path(__file__).parents[1] / "fixtures"
TEST_BUNDLE = FIXTURES_DIR / "support-bundle-2025-04-11T14_05_31.tar.gz"

def create_client_config_json(bundle_dir: Path, minimal=False) -> dict:
    """Create a test client config JSON."""
    if minimal:
        # Minimal configuration that relies on defaults
        return {
            "mcpServers": {
                "troubleshoot": {
                    "command": "docker",
                    "args": [
                        "run",
                        "-i",
                        "mcp-server-troubleshoot:latest"
                    ]
                }
            }
        }
    else:
        # Full configuration with explicit settings
        return {
            "mcpServers": {
                "troubleshoot": {
                    "command": "docker",
                    "args": [
                        "run",
                        "-i",
                        "-v",
                        f"{bundle_dir}:/data/bundles",
                        "-e",
                        "MCP_BUNDLE_STORAGE=/data/bundles",
                        "-e", 
                        "MCP_KEEP_ALIVE='true'",
                        "--rm",
                        "--entrypoint",
                        "python", 
                        "mcp-server-troubleshoot:latest",
                        "-m",
                        "mcp_server_troubleshoot.cli"
                    ]
                }
            }
        }

@pytest.mark.integration
def test_minimal_config_expansion():
    """Test that minimal config gets properly expanded with defaults."""
    # Create a test config
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_bundle_dir = Path(temp_dir)
        
        # Create the minimal config
        minimal_config = create_client_config_json(temp_bundle_dir, minimal=True)
        
        # Write the minimal config to a file
        config_path = Path(temp_dir) / "minimal_config.json"
        with open(config_path, "w") as f:
            json.dump(minimal_config, f)
            
        # Create an environment for the test
        env = os.environ.copy()
        env["MCP_CONFIG_PATH"] = str(config_path)
        
        # Run the expand config command using the CLI
        process = subprocess.run(
            [sys.executable, "-m", "mcp_server_troubleshoot.cli", "--expand-config"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        # Check that the command was successful
        assert process.returncode == 0, f"Command failed with stderr: {process.stderr}"
        
        # Parse the output JSON
        expanded_config = json.loads(process.stdout)
        
        # Verify that defaults were added
        server_config = expanded_config["mcpServers"]["troubleshoot"]
        assert "--rm" in server_config["args"]
        assert "-e" in server_config["args"]
        assert "MCP_BUNDLE_STORAGE=/data/bundles" in server_config["args"]
        assert "-m" in server_config["args"]
        assert "mcp_server_troubleshoot.cli" in server_config["args"]
        
@pytest.mark.integration
def test_mount_config_expansion():
    """Test that mount paths get properly expanded."""
    # Create a test config
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_bundle_dir = Path(temp_dir)
        
        # Create config with mount path to expand
        config = {
            "mcpServers": {
                "troubleshoot": {
                    "command": "docker",
                    "args": [
                        "run",
                        "-i",
                        "mcp-server-troubleshoot:latest"
                    ],
                    "bundleDir": str(temp_bundle_dir)
                }
            }
        }
        
        # Write the config to a file
        config_path = Path(temp_dir) / "mount_config.json"
        with open(config_path, "w") as f:
            json.dump(config, f)
            
        # Create an environment for the test
        env = os.environ.copy()
        env["MCP_CONFIG_PATH"] = str(config_path)
        
        # Run the expand config command using the CLI
        process = subprocess.run(
            [sys.executable, "-m", "mcp_server_troubleshoot.cli", "--expand-config"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        # Check that the command was successful
        assert process.returncode == 0, f"Command failed with stderr: {process.stderr}"
        
        # Parse the output JSON
        expanded_config = json.loads(process.stdout)
        
        # Verify that the mount was added
        server_config = expanded_config["mcpServers"]["troubleshoot"]
        assert "-v" in server_config["args"]
        
        # Find the mount argument index
        try:
            mount_index = server_config["args"].index("-v")
            mount_path = server_config["args"][mount_index + 1]
            assert str(temp_bundle_dir) in mount_path
            assert "/data/bundles" in mount_path
        except ValueError:
            pytest.fail("Mount (-v) argument not found in expanded config")

@pytest.mark.integration
def test_environment_variable_expansion():
    """Test that environment variables get properly expanded."""
    # Create a test config
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_bundle_dir = Path(temp_dir)
        
        # Create config with environment variables
        config = {
            "mcpServers": {
                "troubleshoot": {
                    "command": "docker",
                    "args": [
                        "run",
                        "-i",
                        "mcp-server-troubleshoot:latest"
                    ],
                    "env": {
                        "SBCTL_TOKEN": "test-token"
                    }
                }
            }
        }
        
        # Write the config to a file
        config_path = Path(temp_dir) / "env_config.json"
        with open(config_path, "w") as f:
            json.dump(config, f)
            
        # Create an environment for the test
        env = os.environ.copy()
        env["MCP_CONFIG_PATH"] = str(config_path)
        
        # Run the expand config command using the CLI
        process = subprocess.run(
            [sys.executable, "-m", "mcp_server_troubleshoot.cli", "--expand-config"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        # Check that the command was successful
        assert process.returncode == 0, f"Command failed with stderr: {process.stderr}"
        
        # Parse the output JSON
        expanded_config = json.loads(process.stdout)
        
        # Verify that the environment variables were added
        server_config = expanded_config["mcpServers"]["troubleshoot"]
        
        # Find the environment variable arguments
        env_args = []
        for i, arg in enumerate(server_config["args"]):
            if arg == "-e" and i+1 < len(server_config["args"]):
                env_args.append(server_config["args"][i+1])
        
        # Check that the SBCTL_TOKEN environment variable is included
        assert any("SBCTL_TOKEN=test-token" in env for env in env_args), "Environment variable not properly added"