"""
Tests for the MCP server.
"""

import asyncio
import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_troubleshoot.bundle import BundleMetadata
from mcp_server_troubleshoot.kubectl import KubectlResult
from mcp_server_troubleshoot.files import (
    FileListResult,
    FileContentResult,
    GrepResult,
    FileInfo,
    GrepMatch,
)
from mcp_server_troubleshoot.server import TroubleshootMCPServer


@pytest.mark.asyncio
async def test_server_initialization():
    """Test that the server can be initialized."""
    server = TroubleshootMCPServer()
    assert server is not None
    assert server.server is not None
    assert server.bundle_manager is not None
    assert server.kubectl_executor is not None
    assert server.file_explorer is not None


@pytest.mark.asyncio
async def test_list_tools():
    """Test that the server returns the expected list of tools."""
    server = TroubleshootMCPServer()

    # Mock the MCP Server list_tools method to capture the handler
    list_tools_handler = None

    def list_tools_decorator(func):
        nonlocal list_tools_handler
        list_tools_handler = func
        return func

    with patch.object(server.server, "list_tools", return_value=list_tools_decorator):
        server._register_handlers()

    # Call the captured handler
    assert list_tools_handler is not None
    tools = await list_tools_handler()

    # Verify that the expected tools are returned
    assert isinstance(tools, list)
    assert len(tools) == 5  # Should include file operation tools now
    tool_names = [tool.name for tool in tools]
    assert "initialize_bundle" in tool_names
    assert "kubectl" in tool_names
    assert "list_files" in tool_names
    assert "read_file" in tool_names
    assert "grep_files" in tool_names


@pytest.mark.asyncio
async def test_call_tool_nonexistent():
    """Test that the server returns an error for non-existent tools."""
    server = TroubleshootMCPServer()

    # Mock the MCP Server call_tool method to capture the handler
    call_tool_handler = None

    def call_tool_decorator(func):
        nonlocal call_tool_handler
        call_tool_handler = func
        return func

    with patch.object(server.server, "call_tool", return_value=call_tool_decorator):
        server._register_handlers()

    # Call the captured handler with a non-existent tool
    assert call_tool_handler is not None
    response = await call_tool_handler("nonexistent_tool", {})

    # Verify that an error message is returned
    assert len(response) == 1
    assert response[0].type == "text"
    assert "is not implemented yet" in response[0].text


@pytest.mark.asyncio
async def test_call_tool_initialize_bundle():
    """Test that the server can handle the initialize_bundle tool."""
    server = TroubleshootMCPServer()

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
        server.bundle_manager.initialize_bundle = AsyncMock(return_value=mock_metadata)

        # Call the handler directly with a real file path
        response = await server._handle_initialize_bundle(
            {"source": temp_file.name, "force": False}
        )

        # Verify that the bundle manager was called
        server.bundle_manager.initialize_bundle.assert_awaited_once_with(temp_file.name, False)

    # Verify the response
    assert len(response) == 1
    assert response[0].type == "text"
    assert "Bundle initialized successfully" in response[0].text
    assert "test_bundle" in response[0].text


@pytest.mark.asyncio
async def test_call_tool_kubectl():
    """Test that the server can handle the kubectl tool."""
    server = TroubleshootMCPServer()

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
    server.kubectl_executor.execute = AsyncMock(return_value=mock_result)

    # Call the handler directly
    response = await server._handle_kubectl(
        {"command": "get pods", "timeout": 30, "json_output": True}
    )

    # Verify that the kubectl executor was called
    server.kubectl_executor.execute.assert_awaited_once_with("get pods", 30, True)

    # Verify the response
    assert len(response) == 1
    assert response[0].type == "text"
    assert "kubectl command executed successfully" in response[0].text
    assert "items" in response[0].text
    assert "Command metadata" in response[0].text


@pytest.mark.asyncio
async def test_server_file_operations():
    """Test that the server can handle file operations."""
    server = TroubleshootMCPServer()

    # Mock the FileExplorer methods

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

    server.file_explorer.list_files = AsyncMock(return_value=mock_list_result)

    # Call the handler directly
    list_response = await server._handle_list_files({"path": "dir1", "recursive": False})

    # Verify that the file explorer was called
    server.file_explorer.list_files.assert_awaited_once_with("dir1", False)

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

    server.file_explorer.read_file = AsyncMock(return_value=mock_content_result)

    # Call the handler directly
    read_response = await server._handle_read_file(
        {"path": "dir1/file1.txt", "start_line": 0, "end_line": 0}
    )

    # Verify that the file explorer was called
    server.file_explorer.read_file.assert_awaited_once_with("dir1/file1.txt", 0, 0)

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

    server.file_explorer.grep_files = AsyncMock(return_value=mock_grep_result)

    # Call the handler directly
    grep_response = await server._handle_grep_files(
        {
            "pattern": "pattern",
            "path": "dir1",
            "recursive": True,
            "glob_pattern": "*.txt",
            "case_sensitive": False,
            "max_results": 100,
        }
    )

    # Verify that the file explorer was called
    server.file_explorer.grep_files.assert_awaited_once_with(
        "pattern", "dir1", True, "*.txt", False, 100
    )

    # Verify the response
    assert len(grep_response) == 1
    assert grep_response[0].type == "text"
    assert "Found 1 matches" in grep_response[0].text
    assert "This contains pattern" in grep_response[0].text


@pytest.mark.asyncio
async def test_serve():
    """Test that the server can be served."""
    server = TroubleshootMCPServer()

    # Mock the readline method to return empty bytes after first call
    input_stream = MagicMock(spec=asyncio.StreamReader)
    input_stream.readline = AsyncMock(
        side_effect=[b'{"jsonrpc": "2.0", "method": "get_tool_definitions", "id": 1}', b""]
    )

    # Mock the output stream with all required methods
    output_stream = MagicMock(spec=asyncio.StreamWriter)
    output_stream.drain = AsyncMock()
    output_stream.wait_closed = AsyncMock()

    # Mock the bundle manager cleanup method with proper timeout handling
    server.bundle_manager.cleanup = AsyncMock()

    # Mock asyncio.wait_for to pass through the result
    original_wait_for = asyncio.wait_for

    async def mock_wait_for(coro, timeout):
        if isinstance(coro, AsyncMock) or coro is input_stream.readline:
            return await coro
        elif coro is output_stream.wait_closed:
            return None
        else:
            return await original_wait_for(coro, timeout)

    # Mock event loop methods that might fail in tests
    mock_loop = AsyncMock()

    # Call serve with the mock streams
    with (
        patch("asyncio.get_event_loop", return_value=mock_loop),
        patch("asyncio.wait_for", side_effect=mock_wait_for),
    ):
        await server.serve(input_stream, output_stream)

    # Verify that the output stream was written to
    assert output_stream.write.called

    # Verify that the bundle manager cleanup method was called
    server.bundle_manager.cleanup.assert_awaited_once()

    # Verify that output_stream.wait_closed was called (new behavior)
    output_stream.wait_closed.assert_awaited_once()


@pytest.mark.asyncio
async def test_clean_stdio_handling():
    """Test that the server correctly separates stdout and stderr when in MCP mode."""
    server = TroubleshootMCPServer()

    # Mock the readline method to return a valid JSON-RPC request followed by empty bytes
    input_stream = MagicMock(spec=asyncio.StreamReader)
    input_stream.readline = AsyncMock(
        side_effect=[b'{"jsonrpc": "2.0", "method": "get_tool_definitions", "id": 1}', b""]
    )

    # Mock the output stream to capture what's written to stdout
    output_stream = MagicMock(spec=asyncio.StreamWriter)
    output_stream.drain = AsyncMock()
    output_stream.wait_closed = AsyncMock()
    output_stream.write = MagicMock()  # We'll check what's written to stdout

    # Mock the bundle manager cleanup method with proper timeout handling
    server.bundle_manager.cleanup = AsyncMock()

    # Mock asyncio.wait_for to pass through the result
    original_wait_for = asyncio.wait_for

    async def mock_wait_for(coro, timeout):
        if isinstance(coro, AsyncMock) or coro is input_stream.readline:
            return await coro
        elif coro is output_stream.wait_closed:
            return None
        else:
            return await original_wait_for(coro, timeout)

    # Set up to capture logging messages
    log_messages = []
    
    class TestLogHandler(logging.Handler):
        def emit(self, record):
            log_messages.append(record.getMessage())
    
    handler = TestLogHandler()
    root_logger = logging.getLogger()
    
    # Store original settings to restore later
    original_level = root_logger.level
    original_handlers = root_logger.handlers.copy()
    
    # Set debug level to ensure logs are generated
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(handler)
    
    try:
        # Call serve with the mock streams and MCP mode enabled
        with (
            patch("asyncio.get_event_loop", return_value=AsyncMock()),
            patch("asyncio.wait_for", side_effect=mock_wait_for),
        ):
            await server.serve(input_stream, output_stream, mcp_mode=True)
        
        # Verify that the output stream received only valid JSON-RPC responses
        # and no log messages were sent to stdout
        for call in output_stream.write.call_args_list:
            args = call[0]
            written_bytes = args[0]
            written_text = written_bytes.decode('utf-8')
            
            # Check that it's valid JSON
            json_data = json.loads(written_text.strip())
            # Verify it contains required JSON-RPC fields
            assert "jsonrpc" in json_data
            assert json_data["jsonrpc"] == "2.0"
            assert "id" in json_data
            
            # Make sure common log message patterns aren't in stdout
            assert "Starting MCP server" not in written_text
            assert "DEBUG" not in written_text
            assert "INFO" not in written_text
            assert "WARNING" not in written_text
            assert "ERROR" not in written_text
        
        # Verify that logs were captured somewhere (stderr in real use)
        assert len(log_messages) > 0
        
        # Check specific log messages we know should be generated
        found_startup_log = False
        for message in log_messages:
            if "Starting MCP server in MCP mode" in message:
                found_startup_log = True
                break
        
        assert found_startup_log, "Expected startup log message wasn't found"
    
    finally:
        # Clean up logging handlers and restore original settings
        root_logger.handlers = original_handlers
        root_logger.setLevel(original_level)
