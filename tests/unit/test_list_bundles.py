"""
Tests for the list_available_bundles method in BundleManager.
"""

import tarfile
import tempfile
from pathlib import Path

import pytest

from mcp_server_troubleshoot.bundle import BundleManager


@pytest.fixture
def temp_bundle_dir():
    """Create a temporary directory for test bundles."""
    temp_dir = tempfile.mkdtemp(prefix="test_bundle_dir_")
    yield Path(temp_dir)
    # Cleanup
    import shutil

    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_valid_bundle(temp_bundle_dir):
    """Create a mock valid support bundle file."""
    # Create a tar.gz file with the expected structure
    bundle_path = temp_bundle_dir / "valid_bundle.tar.gz"
    with tarfile.open(bundle_path, "w:gz") as tar:
        # Add a cluster-resources directory
        info = tarfile.TarInfo("support-bundle-2023/cluster-resources/pods.json")
        info.size = 0
        tar.addfile(info)
    return bundle_path


@pytest.fixture
def mock_invalid_bundle(temp_bundle_dir):
    """Create a mock invalid bundle file."""
    # Create a tar.gz file without the expected structure
    bundle_path = temp_bundle_dir / "invalid_bundle.tar.gz"
    with tarfile.open(bundle_path, "w:gz") as tar:
        # Add a file but not the expected structure
        info = tarfile.TarInfo("some_file.txt")
        info.size = 0
        tar.addfile(info)
    return bundle_path


@pytest.fixture
def mock_non_tar_file(temp_bundle_dir):
    """Create a mock file that is not a tar.gz."""
    # Create a file that is not a tar.gz
    file_path = temp_bundle_dir / "not_a_bundle.txt"
    with open(file_path, "w") as f:
        f.write("This is not a tar.gz file")
    return file_path


@pytest.mark.asyncio
async def test_list_available_bundles_empty_dir(temp_bundle_dir):
    """Test listing bundles with an empty directory."""
    bundle_manager = BundleManager(temp_bundle_dir)
    bundles = await bundle_manager.list_available_bundles()

    assert len(bundles) == 0


@pytest.mark.asyncio
async def test_list_available_bundles_valid_bundle(temp_bundle_dir, mock_valid_bundle):
    """Test listing bundles with a valid bundle."""
    bundle_manager = BundleManager(temp_bundle_dir)
    bundles = await bundle_manager.list_available_bundles()

    assert len(bundles) == 1
    assert bundles[0].name == "valid_bundle.tar.gz"
    assert bundles[0].path == str(mock_valid_bundle)
    assert bundles[0].valid is True
    assert bundles[0].validation_message is None


@pytest.mark.asyncio
async def test_list_available_bundles_invalid_bundle(temp_bundle_dir, mock_invalid_bundle):
    """Test listing bundles with an invalid bundle."""
    bundle_manager = BundleManager(temp_bundle_dir)

    # By default invalid bundles are excluded
    bundles = await bundle_manager.list_available_bundles()
    assert len(bundles) == 0

    # With include_invalid=True they should be included
    bundles = await bundle_manager.list_available_bundles(include_invalid=True)
    assert len(bundles) == 1
    assert bundles[0].name == "invalid_bundle.tar.gz"
    assert bundles[0].path == str(mock_invalid_bundle)
    assert bundles[0].valid is False
    assert bundles[0].validation_message is not None


@pytest.mark.asyncio
async def test_list_available_bundles_mixed(
    temp_bundle_dir, mock_valid_bundle, mock_invalid_bundle
):
    """Test listing bundles with both valid and invalid bundles."""
    bundle_manager = BundleManager(temp_bundle_dir)

    # By default only valid bundles should be included
    bundles = await bundle_manager.list_available_bundles()
    assert len(bundles) == 1
    assert bundles[0].name == "valid_bundle.tar.gz"

    # With include_invalid=True, both should be included
    bundles = await bundle_manager.list_available_bundles(include_invalid=True)
    assert len(bundles) == 2

    # They should be sorted by modification time (newest first)
    # Since we created them in order, the invalid one should be newer
    assert bundles[0].name == "invalid_bundle.tar.gz"
    assert bundles[1].name == "valid_bundle.tar.gz"


@pytest.mark.asyncio
async def test_list_available_bundles_non_existing_dir(temp_bundle_dir):
    """Test listing bundles with a non-existing directory."""
    non_existing_dir = temp_bundle_dir / "non_existent_subdir"
    # Don't create the directory, but it's in a valid parent
    bundle_manager = BundleManager(non_existing_dir)
    bundles = await bundle_manager.list_available_bundles()

    assert len(bundles) == 0


@pytest.mark.asyncio
async def test_bundle_validity_checker(
    temp_bundle_dir, mock_valid_bundle, mock_invalid_bundle, mock_non_tar_file
):
    """Test the bundle validity checker."""
    bundle_manager = BundleManager(temp_bundle_dir)

    # Valid bundle
    valid, message = bundle_manager._check_bundle_validity(mock_valid_bundle)
    assert valid is True
    assert message is None

    # Invalid bundle
    valid, message = bundle_manager._check_bundle_validity(mock_invalid_bundle)
    assert valid is False
    assert message is not None

    # Non-tar file
    valid, message = bundle_manager._check_bundle_validity(mock_non_tar_file)
    assert valid is False
    assert message is not None

    # Non-existing file
    valid, message = bundle_manager._check_bundle_validity(Path("/non/existing/file.tar.gz"))
    assert valid is False
    assert message is not None
