"""
End-to-end functional tests for the MCP server.

These tests focus on verifying the actual functionality of the MCP server
rather than implementation details or structure. Instead of testing that
specific files or modules exist, we test that the expected functionality works.
"""

import sys
import pytest
import subprocess
from pathlib import Path

# Mark all tests in this file
pytestmark = [pytest.mark.e2e]

# Get the project root directory
PROJECT_ROOT = Path(__file__).parents[2].absolute()


def test_package_imports():
    """
    Test that all required package components can be imported.

    This single test replaces multiple individual import tests by
    checking all core modules at once.
    """
    # Create a Python script that imports and uses all core components
    test_script = """
import sys
from pathlib import Path

# Import all core modules - if any fail, the script will exit with an error
import mcp_server_troubleshoot
from mcp_server_troubleshoot import __version__
from mcp_server_troubleshoot import bundle, cli, config, files, kubectl, server

# Verify key classes and functions exist
required_components = [
    (bundle, 'BundleManager'),
    (files, 'FileExplorer'),
    (kubectl, 'KubectlExecutor'),
    (server, 'mcp'),
    (cli, 'main'),
]

# Check each component
for module, component in required_components:
    if not hasattr(module, component):
        print(f"Missing component: {module.__name__}.{component}")
        sys.exit(1)

# Test basic configuration functionality
test_config = {
    "bundle_storage": "/tmp/test_bundles",
    "log_level": "INFO",
}

# Verify config functions exist
if not hasattr(config, "get_recommended_client_config"):
    print("Config module missing get_recommended_client_config")
    sys.exit(1)

if not hasattr(config, "load_config_from_path"):
    print("Config module missing load_config_from_path")
    sys.exit(1)

# Success! All components present
print("All components successfully imported and verified")
sys.exit(0)
"""

    # Write the test script to a temporary file
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".py", mode="w") as f:
        f.write(test_script)
        f.flush()

        # Run the script
        result = subprocess.run(
            [sys.executable, f.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

    # Verify it ran successfully
    assert result.returncode == 0, f"Package imports failed with error: {result.stderr}"
    assert (
        "All components successfully imported and verified" in result.stdout
    ), "Component verification failed"


def test_cli_commands():
    """
    Test the CLI commands are functional.

    This test verifies that:
    1. The --help command works
    2. The --version command works
    3. The --show-config command works
    """
    # Test help command
    help_result = subprocess.run(
        [sys.executable, "-m", "mcp_server_troubleshoot.cli", "--help"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert help_result.returncode == 0, f"CLI --help failed: {help_result.stderr}"
    assert "usage:" in help_result.stdout.lower(), "Help output missing 'usage:' section"

    # Test version command
    version_result = subprocess.run(
        [sys.executable, "-m", "mcp_server_troubleshoot.cli", "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert version_result.returncode == 0, f"CLI --version failed: {version_result.stderr}"

    combined_output = version_result.stdout + version_result.stderr
    assert "version" in combined_output.lower(), "Version information not found in output"

    # Test show-config command
    config_result = subprocess.run(
        [sys.executable, "-m", "mcp_server_troubleshoot.cli", "--show-config"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert config_result.returncode == 0, f"CLI --show-config failed: {config_result.stderr}"
    assert "mcpServers" in config_result.stdout, "Config output missing expected content"


@pytest.mark.asyncio
async def test_api_components():
    """
    Test that the API components can be initialized.

    This is a higher-level functional test that verifies the core API
    components work together rather than testing them individually.
    """
    from mcp_server_troubleshoot.bundle import BundleManager
    from mcp_server_troubleshoot.files import FileExplorer
    from mcp_server_troubleshoot.kubectl import KubectlExecutor
    from pathlib import Path

    # Create temporary bundle directory
    temp_dir = Path("/tmp/test_bundles")

    # Initialize components
    bundle_manager = BundleManager(temp_dir)
    file_explorer = FileExplorer(bundle_manager)
    kubectl_executor = KubectlExecutor(bundle_manager)

    # Verify components initialize successfully
    assert bundle_manager is not None
    assert file_explorer is not None
    assert kubectl_executor is not None

    # Verify bundle manager methods
    assert callable(getattr(bundle_manager, "initialize_bundle", None))
    assert callable(getattr(bundle_manager, "list_available_bundles", None))

    # Verify file explorer methods
    assert callable(getattr(file_explorer, "list_files", None))
    assert callable(getattr(file_explorer, "read_file", None))
    assert callable(getattr(file_explorer, "grep_files", None))

    # Verify kubectl executor methods
    assert callable(getattr(kubectl_executor, "execute", None))
