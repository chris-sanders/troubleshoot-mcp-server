"""
Tests for the File Explorer.
"""

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

# Mark all tests in this file as unit tests
pytestmark = pytest.mark.unit


# We use the test_file_setup fixture from conftest.py instead of this function


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
async def test_file_explorer_list_files(test_file_setup):
    """
    Test that the file explorer can list files and directories.

    This test verifies the behavior:
    1. Root directory listing returns expected directories and files
    2. Recursive listing finds all nested files
    3. Result objects have the correct structure and attributes

    Args:
        test_file_setup: Fixture that creates test files for the test
    """
    # Mock the bundle manager
    bundle_manager = Mock(spec=BundleManager)
    bundle = BundleMetadata(
        id="test",
        source="test",
        path=test_file_setup,
        kubeconfig_path=Path("/test/kubeconfig"),
        initialized=True,
    )
    bundle_manager.get_active_bundle.return_value = bundle

    # Create the explorer
    explorer = FileExplorer(bundle_manager)

    # Test 1: List root directory non-recursively
    result = await explorer.list_files("", False)

    # Verify behavior expectations
    assert isinstance(result, FileListResult), "Result should be a FileListResult"
    assert result.path == "", "Path should be preserved in result"
    assert result.recursive is False, "Recursive flag should be preserved"
    assert result.total_dirs == 2, "Should find 2 directories (dir1 and dir2)"
    assert result.total_files == 1, "Should find 1 file (binary_file)"
    assert len(result.entries) == 3, "Should have 3 entries total"

    # Test 2: List subdirectory recursively
    result = await explorer.list_files("dir1", True)

    # Verify behavior expectations for recursive listing
    assert result.path == "dir1", "Path should match requested directory"
    assert result.recursive is True, "Recursive flag should be preserved"
    assert result.total_files >= 3, "Should find at least 3 files in dir1"

    # Test 3: Verify result structure is correct (behavior contracts)
    for entry in result.entries:
        assert isinstance(entry, FileInfo), "Each entry should be a FileInfo"
        assert hasattr(entry, "name"), "Entry should have a name"
        assert hasattr(entry, "path"), "Entry should have a path"
        assert hasattr(entry, "type"), "Entry should have a type"
        assert hasattr(entry, "size"), "Entry should have a size"
        assert entry.type in ["file", "dir"], "Type should be file or dir"


@pytest.mark.asyncio
async def test_file_explorer_list_files_errors(test_file_setup):
    """
    Test that the file explorer handles listing errors correctly.

    This test verifies the behavior when errors occur:
    1. Listing non-existent paths raises PathNotFoundError
    2. Trying to list a file raises an error
    3. Using the explorer without a bundle raises an error

    Args:
        test_file_setup: Fixture that provides a test directory with files
    """
    # Mock the bundle manager
    bundle_manager = Mock(spec=BundleManager)
    bundle = BundleMetadata(
        id="test",
        source="test",
        path=test_file_setup,
        kubeconfig_path=Path("/test/kubeconfig"),
        initialized=True,
    )
    bundle_manager.get_active_bundle.return_value = bundle

    # Create the explorer
    explorer = FileExplorer(bundle_manager)

    # Test 1: Listing a non-existent path raises an error
    with pytest.raises(PathNotFoundError):
        await explorer.list_files("nonexistent_path", False)

    # Test 2: Listing a file (should raise an error)
    # We know from the fixture that dir1/file1.txt exists
    with pytest.raises(Exception):
        await explorer.list_files("dir1/file1.txt", False)

    # Test 3: Without an active bundle should raise an error
    bundle_manager.get_active_bundle.return_value = None
    with pytest.raises(Exception):
        await explorer.list_files("", False)


@pytest.mark.asyncio
async def test_file_explorer_read_file(test_file_setup):
    """
    Test that the file explorer can read files correctly.

    This test verifies the behavior:
    1. Text files can be read with correct content
    2. Line ranges can be selected for reading
    3. Binary files are detected properly

    Args:
        test_file_setup: Fixture that provides a test directory with files
    """
    # Mock the bundle manager
    bundle_manager = Mock(spec=BundleManager)
    bundle = BundleMetadata(
        id="test",
        source="test",
        path=test_file_setup,
        kubeconfig_path=Path("/test/kubeconfig"),
        initialized=True,
    )
    bundle_manager.get_active_bundle.return_value = bundle

    # Create the explorer
    explorer = FileExplorer(bundle_manager)

    # Test 1: Reading a text file
    result = await explorer.read_file("dir1/file1.txt")

    # Verify behavior expectations
    assert isinstance(result, FileContentResult), "Result should be a FileContentResult"
    assert result.path == "dir1/file1.txt", "Path should be preserved in result"
    assert "file 1" in result.content, "Content should match expected text"
    assert result.binary is False, "Text file should not be marked as binary"
    assert result.total_lines > 0, "Line count should be available"

    # Test 2: Reading a line range
    result = await explorer.read_file("dir1/file1.txt", 1, 2)

    # Verify behavior expectations for line ranges
    assert result.start_line == 1, "Start line should match requested value"
    assert result.end_line >= 1, "End line should be at least start line"

    # Test 3: Reading binary file
    result = await explorer.read_file("binary_file")

    # Verify behavior expectations for binary files
    assert result.path == "binary_file", "Path should be preserved in result"
    assert result.binary is True, "Binary file should be marked as binary"


@pytest.mark.asyncio
async def test_file_explorer_read_file_errors(test_file_setup):
    """
    Test that the file explorer handles read errors correctly.

    This test verifies the behavior:
    1. Reading non-existent files raises appropriate errors
    2. Reading directories raises appropriate errors
    3. Using file explorer without a bundle raises an error

    Args:
        test_file_setup: Fixture that provides a test directory with files
    """
    # Mock the bundle manager
    bundle_manager = Mock(spec=BundleManager)
    bundle = BundleMetadata(
        id="test",
        source="test",
        path=test_file_setup,
        kubeconfig_path=Path("/test/kubeconfig"),
        initialized=True,
    )
    bundle_manager.get_active_bundle.return_value = bundle

    # Create the explorer
    explorer = FileExplorer(bundle_manager)

    # Test 1: Reading a non-existent file raises PathNotFoundError
    with pytest.raises(PathNotFoundError):
        await explorer.read_file("nonexistent.txt")

    # Test 2: Reading a directory raises ReadFileError
    with pytest.raises(ReadFileError):
        await explorer.read_file("dir1")

    # Test 3: Without an active bundle should raise an error
    bundle_manager.get_active_bundle.return_value = None
    with pytest.raises(Exception):
        await explorer.read_file("dir1/file1.txt")


@pytest.mark.asyncio
async def test_file_explorer_grep_files(test_file_setup):
    """
    Test that the file explorer can search files with different patterns.

    This test verifies the behavior:
    1. Global search finds matches across all files
    2. Path-restricted search only looks in specific directories
    3. Glob patterns filter which files are searched
    4. Case sensitivity works as expected

    Args:
        test_file_setup: Fixture that creates test files for the test
    """
    # Mock the bundle manager
    bundle_manager = Mock(spec=BundleManager)
    bundle = BundleMetadata(
        id="test",
        source="test",
        path=test_file_setup,
        kubeconfig_path=Path("/test/kubeconfig"),
        initialized=True,
    )
    bundle_manager.get_active_bundle.return_value = bundle

    # Create the explorer
    explorer = FileExplorer(bundle_manager)

    # Test 1: Global search for common pattern
    result = await explorer.grep_files("This is", "", True)

    # Verify behavior expectations
    assert isinstance(result, GrepResult), "Result should be a GrepResult"
    assert result.pattern == "This is", "Pattern should be preserved in result"
    assert result.path == "", "Path should be preserved in result"
    assert result.total_matches >= 3, "Should find matches in all text files"
    assert result.files_searched > 0, "Should report number of files searched"
    assert not result.truncated, "Result should not be truncated"

    # Verify match objects structure (behavior contract)
    for match in result.matches:
        assert "This is" in match.line, "Line should contain the pattern"
        assert match.match == "This is", "Match should be the exact pattern"
        assert hasattr(match, "line_number"), "Match should have line number"
        assert hasattr(match, "offset"), "Match should have offset"
        assert hasattr(match, "path"), "Match should have path"

    # Test 2: Directory-restricted search with glob pattern
    result = await explorer.grep_files("file", "dir1", True, "*.txt")

    # Verify behavior expectations
    assert result.pattern == "file", "Pattern should be preserved"
    assert result.path == "dir1", "Path should be preserved"
    assert result.glob_pattern == "*.txt", "Glob pattern should be preserved"
    assert result.total_matches > 0, "Should find matches in dir1"

    # Test 3: Case sensitivity behavior
    # Our test file specifically has patterns for case sensitivity testing
    # First test with case sensitive search
    case_sensitive = await explorer.grep_files("UPPERCASE", "", True, None, True)

    # Now test with case insensitive search
    case_insensitive = await explorer.grep_files("uppercase", "", True, None, False)

    # Verify behavior expectations for case sensitivity
    assert case_sensitive.total_matches > 0, "Should find exact case matches"
    assert case_insensitive.total_matches > 0, "Should find case-insensitive matches"
    assert case_insensitive.case_sensitive is False, "Should preserve case sensitivity flag"


@pytest.mark.asyncio
async def test_file_explorer_grep_files_with_kubeconfig(test_file_setup):
    """
    Test searching for specific patterns across multiple files.

    This test verifies the behavior:
    1. Grep can find patterns in both file content and filenames
    2. Multiple matches in the same file are found correctly
    3. Results contain the expected number of matches

    Args:
        test_file_setup: Fixture that provides a test directory with files
    """
    # Create additional test files for this specific test
    kubeconfig_path = test_file_setup / "kubeconfig"
    kubeconfig_path.write_text("apiVersion: v1\nkind: Config\nclusters:\n- name: test-cluster\n")

    # Create a file with repeating specific patterns
    ref_file = test_file_setup / "dir1" / "reference.txt"
    ref_file.write_text(
        "This file refers to a specific pattern.\n"
        "It contains the word multiple times.\n"
        "specific is important.\n"
        "Very specific indeed.\n"
    )

    # Mock the bundle manager
    bundle_manager = Mock(spec=BundleManager)
    bundle = BundleMetadata(
        id="test",
        source="test",
        path=test_file_setup,
        kubeconfig_path=kubeconfig_path,
        initialized=True,
    )
    bundle_manager.get_active_bundle.return_value = bundle

    # Create the explorer
    explorer = FileExplorer(bundle_manager)

    # Test searching for "specific" pattern
    result = await explorer.grep_files("specific", "", True, None, False)

    # Verify behavior expectations
    assert isinstance(result, GrepResult), "Result should be a GrepResult"
    assert result.pattern == "specific", "Pattern should be preserved"
    assert result.path == "", "Root path should be preserved"

    # Should find multiple matches in the reference file
    assert result.total_matches >= 3, "Should find multiple pattern instances"
    assert result.files_searched > 0, "Should report number of files searched"

    # There should be matches in our reference file
    ref_file_matches = [m for m in result.matches if "reference.txt" in m.path]
    assert len(ref_file_matches) > 0, "Should find matches in reference.txt"


@pytest.mark.asyncio
async def test_file_explorer_grep_files_errors(test_file_setup):
    """
    Test that the file explorer handles search errors correctly.

    This test verifies the behavior:
    1. Searching non-existent paths raises appropriate errors
    2. Using the explorer without a bundle raises an error

    Args:
        test_file_setup: Fixture that provides a test directory with files
    """
    # Mock the bundle manager
    bundle_manager = Mock(spec=BundleManager)
    bundle = BundleMetadata(
        id="test",
        source="test",
        path=test_file_setup,
        kubeconfig_path=Path("/test/kubeconfig"),
        initialized=True,
    )
    bundle_manager.get_active_bundle.return_value = bundle

    # Create the explorer
    explorer = FileExplorer(bundle_manager)

    # Test 1: Searching a non-existent path raises an error
    with pytest.raises(PathNotFoundError):
        await explorer.grep_files("test", "nonexistent_path", True)

    # Test 2: Without an active bundle should raise an error
    bundle_manager.get_active_bundle.return_value = None
    with pytest.raises(Exception):
        await explorer.grep_files("test", "", True)


def test_file_explorer_is_binary(test_file_setup):
    """
    Test that the file explorer can detect binary files correctly.

    This test verifies the behavior of the binary file detection:
    1. Text files are correctly identified as non-binary
    2. Binary files are correctly identified as binary

    Args:
        test_file_setup: Fixture that provides a test directory with files
    """
    # Mock the bundle manager
    bundle_manager = Mock(spec=BundleManager)
    bundle = BundleMetadata(
        id="test",
        source="test",
        path=test_file_setup,
        kubeconfig_path=Path("/test/kubeconfig"),
        initialized=True,
    )
    bundle_manager.get_active_bundle.return_value = bundle

    # Create the explorer
    explorer = FileExplorer(bundle_manager)

    # Test 1: Text file should not be marked as binary
    assert not explorer._is_binary(
        test_file_setup / "dir1" / "file1.txt"
    ), "Text file should not be detected as binary"

    # Test 2: Binary file should be marked as binary
    assert explorer._is_binary(
        test_file_setup / "binary_file"
    ), "Binary file should be detected as binary"


def test_file_explorer_normalize_path(test_file_setup):
    """
    Test that the file explorer normalizes paths correctly and securely.

    This test verifies the behavior of path normalization:
    1. Relative paths are resolved correctly to absolute paths
    2. Paths with leading slashes are handled properly
    3. Nested paths are resolved correctly
    4. Directory traversal attempts are blocked for security

    Args:
        test_file_setup: Fixture that provides a test directory with files
    """
    # Mock the bundle manager
    bundle_manager = Mock(spec=BundleManager)
    bundle = BundleMetadata(
        id="test",
        source="test",
        path=test_file_setup,
        kubeconfig_path=Path("/test/kubeconfig"),
        initialized=True,
    )
    bundle_manager.get_active_bundle.return_value = bundle

    # Create the explorer
    explorer = FileExplorer(bundle_manager)

    # Test 1: Normalizing a relative path
    normalized = explorer._normalize_path("dir1")
    assert (
        normalized == test_file_setup / "dir1"
    ), "Relative path should be resolved to absolute path"

    # Test 2: Normalizing a path with leading slashes
    normalized = explorer._normalize_path("/dir1")
    assert normalized == test_file_setup / "dir1", "Leading slashes should be handled properly"

    # Test 3: Normalizing a nested path
    normalized = explorer._normalize_path("dir2/subdir")
    assert (
        normalized == test_file_setup / "dir2" / "subdir"
    ), "Nested paths should be resolved correctly"

    # Test 4: Security check - block directory traversal attempts
    with pytest.raises(InvalidPathError):
        explorer._normalize_path("../outside")

    with pytest.raises(InvalidPathError):
        explorer._normalize_path("dir1/../../../outside")
