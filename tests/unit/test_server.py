"""
Tests for the MCP server.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from mcp.types import TextContent

# Mark all tests in this file as unit tests and quick tests
pytestmark = [pytest.mark.unit, pytest.mark.quick]

from mcp_server_troubleshoot.bundle import BundleMetadata
from mcp_server_troubleshoot.files import (
    FileContentResult,
    FileInfo,
    FileListResult,
    GrepMatch,
    GrepResult,
)
from mcp_server_troubleshoot.kubectl import KubectlResult
from mcp_server_troubleshoot.server import (
    get_bundle_manager,
    get_file_explorer,
    get_kubectl_executor,
    initialize_bundle,
    kubectl,
    list_files,
    mcp,
    read_file,
    grep_files,
)


def test_global_instances():
    """Test that the global instances are properly initialized."""
    # Reset the global instances first
    import mcp_server_troubleshoot.server

    mcp_server_troubleshoot.server._bundle_manager = None
    mcp_server_troubleshoot.server._kubectl_executor = None
    mcp_server_troubleshoot.server._file_explorer = None

    # Now get instances and check they're created
    bundle_manager = get_bundle_manager()
    assert bundle_manager is not None

    kubectl_executor = get_kubectl_executor()
    assert kubectl_executor is not None
    assert kubectl_executor.bundle_manager is bundle_manager

    file_explorer = get_file_explorer()
    assert file_explorer is not None
    assert file_explorer.bundle_manager is bundle_manager


@pytest.mark.asyncio
async def test_initialize_bundle_tool():
    """Test that the initialize_bundle tool works correctly."""
    # Create a test file that exists
    with tempfile.NamedTemporaryFile() as temp_file:
        # Mock the BundleManager.initialize_bundle method
        mock_metadata = BundleMetadata(
            id="test_bundle",
            source=temp_file.name,
            path=Path("/test/path"),
            kubeconfig_path=Path("/test/kubeconfig"),
            initialized=True,
        )

        # Patch get_bundle_manager to return a mock with all necessary methods
        with patch("mcp_server_troubleshoot.server.get_bundle_manager") as mock_get_manager:
            mock_manager = Mock()
            # Mock all the async methods we need
            mock_manager._check_sbctl_available = AsyncMock(return_value=True)
            mock_manager.initialize_bundle = AsyncMock(return_value=mock_metadata)
            mock_manager.check_api_server_available = AsyncMock(return_value=True)
            mock_manager.get_diagnostic_info = AsyncMock(return_value={})
            mock_get_manager.return_value = mock_manager

            # Create InitializeBundleArgs instance
            from mcp_server_troubleshoot.bundle import InitializeBundleArgs

            args = InitializeBundleArgs(source=temp_file.name, force=False)

            # Call the tool function directly
            response = await initialize_bundle(args)

            # Verify the bundle manager methods were called
            mock_manager._check_sbctl_available.assert_awaited_once()
            mock_manager.initialize_bundle.assert_awaited_once_with(temp_file.name, False)
            mock_manager.check_api_server_available.assert_awaited_once()

            # Verify the response
            assert isinstance(response, list)
            assert len(response) == 1
            assert isinstance(response[0], TextContent)
            assert response[0].type == "text"
            assert "Bundle initialized successfully" in response[0].text
            assert "test_bundle" in response[0].text


@pytest.mark.asyncio
async def test_kubectl_tool():
    """Test that the kubectl tool works correctly."""
    # Mock the KubectlExecutor.execute method
    mock_result = KubectlResult(
        command="get pods",
        exit_code=0,
        stdout='{"items": []}',
        stderr="",
        output={"items": []},
        is_json=True,
        duration_ms=100,
    )

    # We need to mock both the bundle manager and kubectl executor
    with patch("mcp_server_troubleshoot.server.get_bundle_manager") as mock_get_manager:
        mock_manager = Mock()
        # Mock the bundle manager's check_api_server_available method
        mock_manager.check_api_server_available = AsyncMock(return_value=True)
        mock_get_manager.return_value = mock_manager
        
        # And then mock the kubectl executor
        with patch("mcp_server_troubleshoot.server.get_kubectl_executor") as mock_get_executor:
            mock_executor = Mock()
            mock_executor.execute = AsyncMock(return_value=mock_result)
            mock_get_executor.return_value = mock_executor

            # Create KubectlCommandArgs instance
            from mcp_server_troubleshoot.kubectl import KubectlCommandArgs

            args = KubectlCommandArgs(command="get pods", timeout=30, json_output=True)

            # Call the tool function directly
            response = await kubectl(args)

            # Verify the API server check was called
            mock_manager.check_api_server_available.assert_awaited_once()
            # Verify the kubectl executor was called
            mock_executor.execute.assert_awaited_once_with("get pods", 30, True)

        # Verify the response
        assert isinstance(response, list)
        assert len(response) == 1
        assert isinstance(response[0], TextContent)
        assert response[0].type == "text"
        assert "kubectl command executed successfully" in response[0].text
        assert "items" in response[0].text
        assert "Command metadata" in response[0].text


@pytest.mark.asyncio
async def test_file_operations():
    """Test the file operation tools."""
    # Set up mock for FileExplorer
    with patch("mcp_server_troubleshoot.server.get_file_explorer") as mock_get_explorer:
        mock_explorer = Mock()
        mock_get_explorer.return_value = mock_explorer

        # 1. Test list_files
        mock_file_info = FileInfo(
            name="file1.txt",
            path="dir1/file1.txt",
            type="file",
            size=100,
            access_time=123456789.0,
            modify_time=123456789.0,
            is_binary=False,
        )

        mock_list_result = FileListResult(
            path="dir1", entries=[mock_file_info], recursive=False, total_files=1, total_dirs=0
        )

        mock_explorer.list_files = AsyncMock(return_value=mock_list_result)

        # Create ListFilesArgs instance
        from mcp_server_troubleshoot.files import ListFilesArgs

        list_args = ListFilesArgs(path="dir1", recursive=False)

        # Call the tool function
        list_response = await list_files(list_args)

        # Verify the file explorer was called
        mock_explorer.list_files.assert_awaited_once_with("dir1", False)

        # Verify the response
        assert len(list_response) == 1
        assert list_response[0].type == "text"
        assert "Listed files" in list_response[0].text
        assert "file1.txt" in list_response[0].text

        # 2. Test read_file
        mock_content_result = FileContentResult(
            path="dir1/file1.txt",
            content="This is the file content",
            start_line=0,
            end_line=0,
            total_lines=1,
            binary=False,
        )

        mock_explorer.read_file = AsyncMock(return_value=mock_content_result)

        # Create ReadFileArgs instance
        from mcp_server_troubleshoot.files import ReadFileArgs

        read_args = ReadFileArgs(path="dir1/file1.txt", start_line=0, end_line=0)

        # Call the tool function
        read_response = await read_file(read_args)

        # Verify the file explorer was called
        mock_explorer.read_file.assert_awaited_once_with("dir1/file1.txt", 0, 0)

        # Verify the response
        assert len(read_response) == 1
        assert read_response[0].type == "text"
        assert "Read text file" in read_response[0].text
        assert "This is the file content" in read_response[0].text

        # 3. Test grep_files
        mock_grep_match = GrepMatch(
            path="dir1/file1.txt",
            line_number=0,
            line="This contains pattern",
            match="pattern",
            offset=13,
        )

        mock_grep_result = GrepResult(
            pattern="pattern",
            path="dir1",
            glob_pattern="*.txt",
            matches=[mock_grep_match],
            total_matches=1,
            files_searched=1,
            case_sensitive=False,
            truncated=False,
        )

        mock_explorer.grep_files = AsyncMock(return_value=mock_grep_result)

        # Create GrepFilesArgs instance
        from mcp_server_troubleshoot.files import GrepFilesArgs

        grep_args = GrepFilesArgs(
            pattern="pattern",
            path="dir1",
            recursive=True,
            glob_pattern="*.txt",
            case_sensitive=False,
            max_results=100,
        )

        # Call the tool function
        grep_response = await grep_files(grep_args)

        # Verify the file explorer was called
        mock_explorer.grep_files.assert_awaited_once_with(
            "pattern", "dir1", True, "*.txt", False, 100
        )

        # Verify the response
        assert len(grep_response) == 1
        assert grep_response[0].type == "text"
        assert "Found 1 matches" in grep_response[0].text
        assert "This contains pattern" in grep_response[0].text


def test_mcp_configuration():
    """Test that the FastMCP server is properly configured."""
    # Check that the server has been created correctly
    assert mcp is not None

    # For FastMCP, we can just verify that our functions exist in the module
    # The @mcp.tool() decorator registers the functions with the FastMCP instance
    from mcp_server_troubleshoot.server import (
        initialize_bundle,
        kubectl,
        list_files,
        read_file,
        grep_files,
    )

    assert callable(initialize_bundle)
    assert callable(kubectl)
    assert callable(list_files)
    assert callable(read_file)
    assert callable(grep_files)
