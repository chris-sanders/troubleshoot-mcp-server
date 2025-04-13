"""
Tests for the File Explorer.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from mcp_server_troubleshoot.bundle import BundleManager, BundleMetadata
from mcp_server_troubleshoot.files import (
    FileContentResult,
    FileExplorer,
    FileInfo,
    FileListResult,
    GrepFilesArgs,
    GrepResult,
    InvalidPathError,
    ListFilesArgs,
    PathNotFoundError,
    ReadFileArgs,
    ReadFileError,
)


def setup_test_bundle():
    """Create a test bundle directory with some files for testing."""
    bundle_dir = Path(tempfile.mkdtemp())

    # Create some test files and directories
    (bundle_dir / "dir1").mkdir()
    (bundle_dir / "dir1" / "file1.txt").write_text("This is file 1\nLine 2\nLine 3\n")
    (bundle_dir / "dir1" / "file2.txt").write_text("This is file 2\nWith some content\n")

    (bundle_dir / "dir2").mkdir()
    (bundle_dir / "dir2" / "subdir").mkdir()
    (bundle_dir / "dir2" / "subdir" / "file3.txt").write_text("This is file 3\nIn a subdirectory\n")

    # Create a binary file
    with open(bundle_dir / "binary_file", "wb") as f:
        f.write(b"\x00\x01\x02\x03\x04\x05")

    return bundle_dir


def test_file_explorer_initialization():
    """Test that the file explorer can be initialized."""
    bundle_manager = Mock(spec=BundleManager)
    explorer = FileExplorer(bundle_manager)
    assert explorer.bundle_manager == bundle_manager


def test_list_files_args_validation():
    """Test that ListFilesArgs validates paths correctly."""
    # Valid path
    args = ListFilesArgs(path="dir1")
    assert args.path == "dir1"
    assert args.recursive is False  # Default value

    # Empty path
    with pytest.raises(ValidationError):
        ListFilesArgs(path="")

    # Path with directory traversal
    with pytest.raises(ValidationError):
        ListFilesArgs(path="../outside")

    with pytest.raises(ValidationError):
        ListFilesArgs(path="dir1/../../../outside")


def test_read_file_args_validation():
    """Test that ReadFileArgs validates arguments correctly."""
    # Valid path and line range
    args = ReadFileArgs(path="dir1/file1.txt", start_line=0, end_line=10)
    assert args.path == "dir1/file1.txt"
    assert args.start_line == 0
    assert args.end_line == 10

    # Empty path
    with pytest.raises(ValidationError):
        ReadFileArgs(path="")

    # Path with directory traversal
    with pytest.raises(ValidationError):
        ReadFileArgs(path="../outside.txt")

    # Negative start_line
    with pytest.raises(ValidationError):
        ReadFileArgs(path="file.txt", start_line=-1)

    # Negative end_line
    with pytest.raises(ValidationError):
        ReadFileArgs(path="file.txt", end_line=-1)


def test_grep_files_args_validation():
    """Test that GrepFilesArgs validates arguments correctly."""
    # Valid arguments
    args = GrepFilesArgs(
        pattern="test",
        path="dir1",
        recursive=True,
        glob_pattern="*.txt",
        case_sensitive=False,
        max_results=100,
    )
    assert args.pattern == "test"
    assert args.path == "dir1"
    assert args.recursive is True
    assert args.glob_pattern == "*.txt"
    assert args.case_sensitive is False
    assert args.max_results == 100

    # Empty path
    with pytest.raises(ValidationError):
        GrepFilesArgs(pattern="test", path="")

    # Empty pattern
    with pytest.raises(ValidationError):
        GrepFilesArgs(pattern="", path="dir1")

    # Path with directory traversal
    with pytest.raises(ValidationError):
        GrepFilesArgs(pattern="test", path="../outside")

    # Non-positive max_results
    with pytest.raises(ValidationError):
        GrepFilesArgs(pattern="test", path="dir1", max_results=0)


@pytest.mark.asyncio
async def test_file_explorer_list_files():
    """Test that the file explorer can list files."""
    bundle_dir = setup_test_bundle()
    try:
        # Mock the bundle manager
        bundle_manager = Mock(spec=BundleManager)
        bundle = BundleMetadata(
            id="test",
            source="test",
            path=bundle_dir,
            kubeconfig_path=Path("/test/kubeconfig"),
            initialized=True,
        )
        bundle_manager.get_active_bundle.return_value = bundle

        # Create the explorer
        explorer = FileExplorer(bundle_manager)

        # Test listing the root directory non-recursively
        result = await explorer.list_files("", False)

        # Verify the result
        assert isinstance(result, FileListResult)
        assert result.path == ""
        assert result.recursive is False
        assert result.total_dirs == 2  # dir1 and dir2
        assert result.total_files == 1  # binary_file
        assert len(result.entries) == 3

        # Test listing a subdirectory recursively
        result = await explorer.list_files("dir1", True)

        # Verify the result
        assert isinstance(result, FileListResult)
        assert result.path == "dir1"
        assert result.recursive is True
        assert result.total_dirs == 0
        assert result.total_files == 2  # file1.txt and file2.txt
        assert len(result.entries) == 2

        # Verify all entry types have the right fields
        for entry in result.entries:
            assert isinstance(entry, FileInfo)
            assert isinstance(entry.name, str)
            assert isinstance(entry.path, str)
            assert entry.type in ["file", "dir"]
            assert isinstance(entry.size, int)
            assert isinstance(entry.access_time, float)
            assert isinstance(entry.modify_time, float)
            assert isinstance(entry.is_binary, bool)

    finally:
        # Clean up
        import shutil

        shutil.rmtree(bundle_dir)


@pytest.mark.asyncio
async def test_file_explorer_list_files_errors():
    """Test that the file explorer handles listing errors correctly."""
    bundle_dir = setup_test_bundle()
    try:
        # Mock the bundle manager
        bundle_manager = Mock(spec=BundleManager)
        bundle = BundleMetadata(
            id="test",
            source="test",
            path=bundle_dir,
            kubeconfig_path=Path("/test/kubeconfig"),
            initialized=True,
        )
        bundle_manager.get_active_bundle.return_value = bundle

        # Create the explorer
        explorer = FileExplorer(bundle_manager)

        # Test listing a non-existent path
        with pytest.raises(PathNotFoundError):
            await explorer.list_files("nonexistent", False)

        # Test listing a file (should be an error)
        with pytest.raises(Exception):
            await explorer.list_files("dir1/file1.txt", False)

        # Test with no active bundle
        bundle_manager.get_active_bundle.return_value = None
        with pytest.raises(Exception):
            await explorer.list_files("", False)

    finally:
        # Clean up
        import shutil

        shutil.rmtree(bundle_dir)


@pytest.mark.asyncio
async def test_file_explorer_read_file():
    """Test that the file explorer can read files."""
    bundle_dir = setup_test_bundle()
    try:
        # Mock the bundle manager
        bundle_manager = Mock(spec=BundleManager)
        bundle = BundleMetadata(
            id="test",
            source="test",
            path=bundle_dir,
            kubeconfig_path=Path("/test/kubeconfig"),
            initialized=True,
        )
        bundle_manager.get_active_bundle.return_value = bundle

        # Create the explorer
        explorer = FileExplorer(bundle_manager)

        # Test reading a text file
        result = await explorer.read_file("dir1/file1.txt")

        # Verify the result
        assert isinstance(result, FileContentResult)
        assert result.path == "dir1/file1.txt"
        assert result.content == "This is file 1\nLine 2\nLine 3\n"
        assert result.start_line == 0
        assert result.end_line == 2  # 3 lines, 0-indexed
        assert result.total_lines == 3
        assert result.binary is False

        # Test reading a line range
        result = await explorer.read_file("dir1/file1.txt", 1, 2)

        # Verify the result
        assert result.content == "Line 2\nLine 3\n"
        assert result.start_line == 1
        assert result.end_line == 2

        # Test reading the binary file
        result = await explorer.read_file("binary_file")

        # Verify the result
        assert result.path == "binary_file"
        assert result.binary is True

    finally:
        # Clean up
        import shutil

        shutil.rmtree(bundle_dir)


@pytest.mark.asyncio
async def test_file_explorer_read_file_errors():
    """Test that the file explorer handles read errors correctly."""
    bundle_dir = setup_test_bundle()
    try:
        # Mock the bundle manager
        bundle_manager = Mock(spec=BundleManager)
        bundle = BundleMetadata(
            id="test",
            source="test",
            path=bundle_dir,
            kubeconfig_path=Path("/test/kubeconfig"),
            initialized=True,
        )
        bundle_manager.get_active_bundle.return_value = bundle

        # Create the explorer
        explorer = FileExplorer(bundle_manager)

        # Test reading a non-existent file
        with pytest.raises(PathNotFoundError):
            await explorer.read_file("nonexistent.txt")

        # Test reading a directory
        with pytest.raises(ReadFileError):
            await explorer.read_file("dir1")

        # Test with no active bundle
        bundle_manager.get_active_bundle.return_value = None
        with pytest.raises(Exception):
            await explorer.read_file("dir1/file1.txt")

    finally:
        # Clean up
        import shutil

        shutil.rmtree(bundle_dir)


@pytest.mark.asyncio
async def test_file_explorer_grep_files():
    """Test that the file explorer can search files."""
    bundle_dir = setup_test_bundle()
    try:
        # Mock the bundle manager
        bundle_manager = Mock(spec=BundleManager)
        bundle = BundleMetadata(
            id="test",
            source="test",
            path=bundle_dir,
            kubeconfig_path=Path("/test/kubeconfig"),
            initialized=True,
        )
        bundle_manager.get_active_bundle.return_value = bundle

        # Create the explorer
        explorer = FileExplorer(bundle_manager)

        # Test searching for a pattern that matches
        result = await explorer.grep_files("This is", "", True)

        # Verify the result
        assert isinstance(result, GrepResult)
        assert result.pattern == "This is"
        assert result.path == ""
        assert result.total_matches == 3  # One in each text file
        assert result.files_searched > 0
        assert not result.truncated

        # Verify the matches
        assert len(result.matches) == 3
        for match in result.matches:
            assert "This is" in match.line
            assert match.match == "This is"
            assert isinstance(match.line_number, int)
            assert isinstance(match.offset, int)

        # Test searching with a glob pattern
        result = await explorer.grep_files("file", "dir1", True, "*.txt")

        # Verify the result
        assert result.pattern == "file"
        assert result.path == "dir1"
        assert result.glob_pattern == "*.txt"
        assert result.total_matches == 4  # Two from filenames + one in each file content

        # Test searching case-sensitively
        result = await explorer.grep_files("LINE", "dir1", True, None, True)

        # Verify the result
        assert result.pattern == "LINE"
        assert result.case_sensitive is True
        assert result.total_matches == 0  # No matches because "LINE" is all caps

        # Test searching case-insensitively
        result = await explorer.grep_files("LINE", "dir1", True, None, False)

        # Verify the result
        assert result.pattern == "LINE"
        assert result.case_sensitive is False
        assert result.total_matches == 2  # Matches "Line" in file1.txt

    finally:
        # Clean up
        import shutil

        shutil.rmtree(bundle_dir)


@pytest.mark.asyncio
async def test_file_explorer_grep_files_with_kubeconfig():
    """Test searching for kubeconfig patterns specifically."""
    bundle_dir = setup_test_bundle()
    try:
        # Create a kubeconfig file to search for
        kubeconfig_path = bundle_dir / "kubeconfig"
        kubeconfig_path.write_text("apiVersion: v1\nkind: Config\nclusters:\n- name: test-cluster\n")

        # Also create a file with the word "kubeconfig" in its contents
        kubeconfig_ref_file = bundle_dir / "dir1" / "reference.txt"
        kubeconfig_ref_file.write_text("This file refers to a kubeconfig file.\nIt contains the word multiple times.\nkubeconfig is important.")

        # Mock the bundle manager
        bundle_manager = Mock(spec=BundleManager)
        bundle = BundleMetadata(
            id="test",
            source="test",
            path=bundle_dir,
            kubeconfig_path=Path("/test/kubeconfig"),
            initialized=True,
        )
        bundle_manager.get_active_bundle.return_value = bundle

        # Create the explorer
        explorer = FileExplorer(bundle_manager)

        # Test searching for "kubeconfig" (case insensitive)
        result = await explorer.grep_files("kubeconfig", "", True, None, False)

        # Verify the result - should find matches in both file content and filenames
        assert isinstance(result, GrepResult)
        assert result.pattern == "kubeconfig"
        assert result.path == ""
        
        # Should find at least 3 matches - in the reference file and potentially in the kubeconfig file itself
        print(f"Matches found: {len(result.matches)}")
        for match in result.matches:
            print(f"Match in {match.path}: {match.line}")
            
        assert result.total_matches >= 3, f"Expected at least 3 matches but found {result.total_matches}"
        assert len(result.matches) >= 3
        
        # Make sure we actually searched the right files
        assert result.files_searched > 0
        
        # There should be at least one match in the reference file we created
        ref_file_matches = [m for m in result.matches if "reference.txt" in m.path]
        assert len(ref_file_matches) > 0, "Should find matches in reference.txt"

    finally:
        # Clean up
        import shutil
        shutil.rmtree(bundle_dir)


@pytest.mark.asyncio
async def test_file_explorer_grep_files_errors():
    """Test that the file explorer handles search errors correctly."""
    bundle_dir = setup_test_bundle()
    try:
        # Mock the bundle manager
        bundle_manager = Mock(spec=BundleManager)
        bundle = BundleMetadata(
            id="test",
            source="test",
            path=bundle_dir,
            kubeconfig_path=Path("/test/kubeconfig"),
            initialized=True,
        )
        bundle_manager.get_active_bundle.return_value = bundle

        # Create the explorer
        explorer = FileExplorer(bundle_manager)

        # Test searching a non-existent path
        with pytest.raises(PathNotFoundError):
            await explorer.grep_files("test", "nonexistent", True)

        # Test with no active bundle
        bundle_manager.get_active_bundle.return_value = None
        with pytest.raises(Exception):
            await explorer.grep_files("test", "", True)

    finally:
        # Clean up
        import shutil

        shutil.rmtree(bundle_dir)


def test_file_explorer_is_binary():
    """Test that the file explorer can detect binary files."""
    bundle_dir = setup_test_bundle()
    try:
        # Mock the bundle manager
        bundle_manager = Mock(spec=BundleManager)
        bundle = BundleMetadata(
            id="test",
            source="test",
            path=bundle_dir,
            kubeconfig_path=Path("/test/kubeconfig"),
            initialized=True,
        )
        bundle_manager.get_active_bundle.return_value = bundle

        # Create the explorer
        explorer = FileExplorer(bundle_manager)

        # Test with a text file
        assert not explorer._is_binary(bundle_dir / "dir1" / "file1.txt")

        # Test with a binary file
        assert explorer._is_binary(bundle_dir / "binary_file")

    finally:
        # Clean up
        import shutil

        shutil.rmtree(bundle_dir)


def test_file_explorer_normalize_path():
    """Test that the file explorer normalizes paths correctly."""
    bundle_dir = setup_test_bundle()
    try:
        # Mock the bundle manager
        bundle_manager = Mock(spec=BundleManager)
        bundle = BundleMetadata(
            id="test",
            source="test",
            path=bundle_dir,
            kubeconfig_path=Path("/test/kubeconfig"),
            initialized=True,
        )
        bundle_manager.get_active_bundle.return_value = bundle

        # Create the explorer
        explorer = FileExplorer(bundle_manager)

        # Test normalizing a relative path
        normalized = explorer._normalize_path("dir1")
        assert normalized == bundle_dir / "dir1"

        # Test normalizing a path with leading slashes
        normalized = explorer._normalize_path("/dir1")
        assert normalized == bundle_dir / "dir1"

        # Test normalizing a nested path
        normalized = explorer._normalize_path("dir2/subdir")
        assert normalized == bundle_dir / "dir2" / "subdir"

        # Test normalizing with directory traversal (should raise an error)
        with pytest.raises(InvalidPathError):
            explorer._normalize_path("../outside")

        with pytest.raises(InvalidPathError):
            explorer._normalize_path("dir1/../../../outside")

    finally:
        # Clean up
        import shutil

        shutil.rmtree(bundle_dir)
