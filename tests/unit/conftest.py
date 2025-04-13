"""
Configuration for unit tests including async test support.
"""

import os
import tempfile
import pytest
import pytest_asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock

# Helper functions for async tests are defined in the main conftest.py


@pytest.fixture
def fixtures_dir() -> Path:
    """
    Returns the path to the test fixtures directory.
    """
    return Path(__file__).parent.parent / "fixtures"


@pytest_asyncio.fixture
async def mock_command_environment(fixtures_dir):
    """
    Creates a test environment with mock sbctl and kubectl binaries.

    This fixture:
    1. Creates a temporary directory for the environment
    2. Sets up mock sbctl and kubectl scripts
    3. Adds the mock binaries to PATH
    4. Yields the temp directory and restores PATH after test

    Args:
        fixtures_dir: Path to the test fixtures directory (pytest fixture)

    Returns:
        A tuple of (temp_dir, old_path) for use in tests
    """
    # Create a temporary directory for the environment
    temp_dir = Path(tempfile.mkdtemp())

    # Set up mock sbctl and kubectl
    mock_sbctl_path = fixtures_dir / "mock_sbctl.py"
    mock_kubectl_path = fixtures_dir / "mock_kubectl.py"
    temp_bin_dir = temp_dir / "bin"
    temp_bin_dir.mkdir(exist_ok=True)

    # Create sbctl mock
    sbctl_link = temp_bin_dir / "sbctl"
    with open(sbctl_link, "w") as f:
        f.write(
            f"""#!/bin/bash
python "{mock_sbctl_path}" "$@"
"""
        )
    os.chmod(sbctl_link, 0o755)

    # Create kubectl mock
    kubectl_link = temp_bin_dir / "kubectl"
    with open(kubectl_link, "w") as f:
        f.write(
            f"""#!/bin/bash
python "{mock_kubectl_path}" "$@"
"""
        )
    os.chmod(kubectl_link, 0o755)

    # Add mock tools to PATH
    old_path = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{temp_bin_dir}:{old_path}"

    try:
        yield temp_dir
    finally:
        # Restore the PATH
        os.environ["PATH"] = old_path
        # Cleanup is handled automatically by tempfile.mkdtemp()


@pytest_asyncio.fixture
async def mock_bundle_manager(fixtures_dir):
    """
    Creates a mock BundleManager with controlled behavior.

    This fixture provides a consistent mock for tests that need
    a BundleManager but don't need to test its real functionality.

    Args:
        fixtures_dir: Path to the test fixtures directory (pytest fixture)

    Returns:
        A Mock object with the BundleManager interface
    """
    from mcp_server_troubleshoot.bundle import BundleManager, BundleMetadata

    # Create a mock bundle manager
    mock_manager = Mock(spec=BundleManager)

    # Set up common attributes
    temp_dir = Path(tempfile.mkdtemp())
    mock_bundle = BundleMetadata(
        id="test_bundle",
        source="test_source",
        path=temp_dir,
        kubeconfig_path=temp_dir / "kubeconfig",
        initialized=True,
    )

    # Create a mock kubeconfig
    with open(mock_bundle.kubeconfig_path, "w") as f:
        f.write(
            '{"apiVersion": "v1", "clusters": [{"cluster": {"server": "http://localhost:8001"}}]}'
        )

    # Set up mock methods
    mock_manager.get_active_bundle.return_value = mock_bundle
    mock_manager.is_initialized.return_value = True
    mock_manager.check_api_server_available = AsyncMock(return_value=True)
    mock_manager.get_diagnostic_info = AsyncMock(
        return_value={
            "api_server_available": True,
            "bundle_initialized": True,
            "sbctl_available": True,
            "sbctl_process_running": True,
        }
    )

    try:
        yield mock_manager
    finally:
        # Clean up temporary directory
        import shutil

        shutil.rmtree(temp_dir)


@pytest.fixture
def test_file_setup():
    """
    Creates a test directory with a variety of files for testing file operations.

    This fixture:
    1. Creates a temporary directory with subdirectories
    2. Populates it with different types of files (text, binary)
    3. Cleans up automatically after the test

    Returns:
        Path to the test directory
    """
    # Create a test directory
    test_dir = Path(tempfile.mkdtemp())

    try:
        # Create subdirectories
        dir1 = test_dir / "dir1"
        dir1.mkdir()

        dir2 = test_dir / "dir2"
        dir2.mkdir()
        subdir = dir2 / "subdir"
        subdir.mkdir()

        # Create text files
        file1 = dir1 / "file1.txt"
        file1.write_text("This is file 1\nLine 2\nLine 3\n")

        file2 = dir1 / "file2.txt"
        file2.write_text("This is file 2\nWith some content\n")

        file3 = subdir / "file3.txt"
        file3.write_text("This is file 3\nIn a subdirectory\n")

        # Create a file with specific search patterns
        search_file = dir1 / "search.txt"
        search_file.write_text(
            "This file contains search patterns\n"
            "UPPERCASE text for case sensitivity tests\n"
            "lowercase text for the same\n"
            "Multiple instances of the word pattern\n"
            "pattern appears again here\n"
        )

        # Create a binary file
        binary_file = test_dir / "binary_file"
        with open(binary_file, "wb") as f:
            f.write(b"\x00\x01\x02\x03\x04\x05")

        # Return the test directory
        yield test_dir
    finally:
        # Clean up
        import shutil

        shutil.rmtree(test_dir)
