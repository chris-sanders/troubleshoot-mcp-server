"""
Parametrized tests for the MCP server.

This module tests the MCP server tools and handlers using parameterized tests that
verify different input combinations and edge cases in a systematic way.

Benefits of this testing approach:
1. Comprehensive coverage of multiple scenarios with concise code
2. Clear documentation of expected outputs for each input combination
3. Consistent testing patterns using the TestAssertions helper class
4. Better visualization of error cases and edge conditions

The tests focus on these key user workflows:
1. Bundle initialization with different sources and conditions
2. Kubectl command execution with various formats and error cases
3. File operations (listing, reading, searching) with different inputs
4. Resource cleanup and shutdown behavior
5. Signal handling and graceful termination

Each test verifies the behavior from the user's perspective, focusing on the
actual outputs users would see rather than implementation details, which
makes the tests more resilient to internal refactoring.
"""

import tempfile
from unittest.mock import AsyncMock, Mock, patch

import pytest

from mcp_server_troubleshoot.bundle import BundleManagerError
from mcp_server_troubleshoot.files import (
    FileContentResult,
    FileInfo,
    FileListResult,
    GrepMatch,
    GrepResult,
    FileSystemError,
    PathNotFoundError,
)
from mcp_server_troubleshoot.server import (
    initialize_bundle,
    kubectl,
    list_files,
    read_file,
    grep_files,
    list_available_bundles,
    cleanup_resources,
    register_signal_handlers,
    shutdown,
)

# Mark all tests in this file as unit tests and quick tests
pytestmark = [pytest.mark.unit, pytest.mark.quick]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source,force,api_available,expected_strings",
    [
        # Success case - all good
        ("test_bundle.tar.gz", False, True, ["Bundle initialized successfully", "test_bundle"]),
        # Success case - force initialization
        ("test_bundle.tar.gz", True, True, ["Bundle initialized successfully", "test_bundle"]),
        # Warning case - API server not available
        (
            "test_bundle.tar.gz",
            False,
            False,
            ["Bundle initialized but API server is NOT available", "kubectl commands may fail"],
        ),
    ],
    ids=[
        "success-normal",
        "success-force",
        "warning-api-unavailable",
    ],
)
async def test_initialize_bundle_tool_parametrized(
    source, force, api_available, expected_strings, test_assertions, test_factory
):
    """
    Test the initialize_bundle tool with different inputs.

    Args:
        source: Bundle source
        force: Whether to force initialization
        api_available: Whether the API server is available
        expected_strings: Strings expected in the response
        test_assertions: Assertions helper fixture
        test_factory: Factory for test objects
    """
    # Create a test file that exists
    with tempfile.NamedTemporaryFile() as temp_file:
        # Create a mock metadata object
        mock_metadata = test_factory.create_bundle_metadata(
            id="test_bundle",
            source=temp_file.name,
        )

        # Create a mock for the bundle manager
        with patch("mcp_server_troubleshoot.server.get_bundle_manager") as mock_get_manager:
            mock_manager = Mock()
            mock_manager._check_sbctl_available = AsyncMock(return_value=True)
            mock_manager.initialize_bundle = AsyncMock(return_value=mock_metadata)
            mock_manager.check_api_server_available = AsyncMock(return_value=api_available)
            mock_manager.get_diagnostic_info = AsyncMock(return_value={})
            mock_get_manager.return_value = mock_manager

            # Create InitializeBundleArgs instance
            from mcp_server_troubleshoot.bundle import InitializeBundleArgs

            args = InitializeBundleArgs(source=temp_file.name, force=force)

            # Call the tool function
            response = await initialize_bundle(args)

            # Verify method calls
            mock_manager._check_sbctl_available.assert_awaited_once()
            mock_manager.initialize_bundle.assert_awaited_once_with(temp_file.name, force)
            mock_manager.check_api_server_available.assert_awaited_once()

            # Use the test assertion helper to verify response
            test_assertions.assert_api_response_valid(response, "text", expected_strings)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "command,timeout,json_output,result_exit_code,result_stdout,expected_strings",
    [
        # Success case - JSON output
        (
            "get pods",
            30,
            True,
            0,
            '{"items": []}',
            ["kubectl command executed successfully", "items", "Command metadata"],
        ),
        # Success case - text output
        (
            "get pods",
            30,
            False,
            0,
            "NAME  READY  STATUS",
            ["kubectl command executed successfully", "NAME  READY  STATUS"],
        ),
        # Error case - command failed
        ("get invalid", 30, True, 1, "", ["kubectl command failed", "exit code 1"]),
    ],
    ids=[
        "success-json",
        "success-text",
        "error-command-failed",
    ],
)
async def test_kubectl_tool_parametrized(
    command,
    timeout,
    json_output,
    result_exit_code,
    result_stdout,
    expected_strings,
    test_assertions,
    test_factory,
):
    """
    Test the kubectl tool with different inputs.

    Args:
        command: kubectl command
        timeout: Command timeout
        json_output: Whether to use JSON output
        result_exit_code: Mock result exit code
        result_stdout: Mock result stdout
        expected_strings: Strings expected in the response
        test_assertions: Assertions helper fixture
        test_factory: Factory for test objects
    """
    # Create a mock result
    mock_result = test_factory.create_kubectl_result(
        command=command,
        exit_code=result_exit_code,
        stdout=result_stdout,
        stderr="",
        is_json=json_output and result_exit_code == 0,  # Only JSON for success cases
        duration_ms=100,
    )

    # Set up the mocks
    with patch("mcp_server_troubleshoot.server.get_bundle_manager") as mock_get_manager:
        mock_manager = Mock()
        # Mock an active bundle that's NOT host-only
        from mcp_server_troubleshoot.bundle import BundleMetadata
        from pathlib import Path

        mock_bundle = BundleMetadata(
            id="test",
            source="test",
            path=Path("/test"),
            kubeconfig_path=Path("/test/kubeconfig"),
            initialized=True,
            host_only_bundle=False,  # Not a host-only bundle
        )
        mock_manager.get_active_bundle = Mock(return_value=mock_bundle)
        mock_manager.check_api_server_available = AsyncMock(return_value=True)
        # Add diagnostic info mock to avoid diagnostics error
        mock_manager.get_diagnostic_info = AsyncMock(return_value={"api_server_available": True})
        mock_get_manager.return_value = mock_manager

        with patch("mcp_server_troubleshoot.server.get_kubectl_executor") as mock_get_executor:
            mock_executor = Mock()

            # For error cases, raise an exception
            if result_exit_code != 0:
                from mcp_server_troubleshoot.kubectl import KubectlError

                mock_executor.execute = AsyncMock(
                    side_effect=KubectlError(
                        f"kubectl command failed: {command}", result_exit_code, ""
                    )
                )
            else:
                # For success cases, return the mock result
                mock_executor.execute = AsyncMock(return_value=mock_result)

            mock_get_executor.return_value = mock_executor

            # Create KubectlCommandArgs instance
            from mcp_server_troubleshoot.kubectl import KubectlCommandArgs

            args = KubectlCommandArgs(command=command, timeout=timeout, json_output=json_output)

            # Call the tool function
            response = await kubectl(args)

            # Verify API check called
            mock_manager.check_api_server_available.assert_awaited_once()

            # For success cases, verify kubectl execution
            if result_exit_code == 0:
                mock_executor.execute.assert_awaited_once_with(command, timeout, json_output)

            # Use the test assertion helper to verify response
            test_assertions.assert_api_response_valid(response, "text", expected_strings)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "file_operation,args,result,expected_strings",
    [
        # Test 1: list_files
        (
            "list_files",
            {"path": "dir1", "recursive": False},
            FileListResult(
                path="dir1",
                entries=[
                    FileInfo(
                        name="file1.txt",
                        path="dir1/file1.txt",
                        type="file",
                        size=100,
                        access_time=123456789.0,
                        modify_time=123456789.0,
                        is_binary=False,
                    )
                ],
                recursive=False,
                total_files=1,
                total_dirs=0,
            ),
            ["Listed files", "file1.txt", "total_files", "total_dirs"],
        ),
        # Test 2: read_file
        (
            "read_file",
            {"path": "dir1/file1.txt", "start_line": 0, "end_line": 0},
            FileContentResult(
                path="dir1/file1.txt",
                content="This is the file content",
                start_line=0,
                end_line=0,
                total_lines=1,
                binary=False,
            ),
            ["Read text file", "This is the file content"],
        ),
        # Test 3: grep_files
        (
            "grep_files",
            {
                "pattern": "pattern",
                "path": "dir1",
                "recursive": True,
                "glob_pattern": "*.txt",
                "case_sensitive": False,
                "max_results": 100,
            },
            GrepResult(
                pattern="pattern",
                path="dir1",
                glob_pattern="*.txt",
                matches=[
                    GrepMatch(
                        path="dir1/file1.txt",
                        line_number=0,
                        line="This contains pattern",
                        match="pattern",
                        offset=13,
                    )
                ],
                total_matches=1,
                files_searched=1,
                case_sensitive=False,
                truncated=False,
            ),
            ["Found 1 matches", "This contains pattern", "total_matches"],
        ),
        # Test 4: grep_files (multiple matches)
        (
            "grep_files",
            {
                "pattern": "common",
                "path": ".",
                "recursive": True,
                "glob_pattern": "*.txt",
                "case_sensitive": False,
                "max_results": 100,
            },
            GrepResult(
                pattern="common",
                path=".",
                glob_pattern="*.txt",
                matches=[
                    GrepMatch(
                        path="dir1/file1.txt",
                        line_number=0,
                        line="This has common text",
                        match="common",
                        offset=9,
                    ),
                    GrepMatch(
                        path="dir2/file2.txt",
                        line_number=1,
                        line="More common text",
                        match="common",
                        offset=5,
                    ),
                ],
                total_matches=2,
                files_searched=3,
                case_sensitive=False,
                truncated=False,
            ),
            ["Found 2 matches", "This has common text", "More common text"],
        ),
    ],
    ids=[
        "list-files",
        "read-file",
        "grep-files-single-match",
        "grep-files-multiple-matches",
    ],
)
async def test_file_operations_parametrized(
    file_operation, args, result, expected_strings, test_assertions
):
    """
    Test file operation tools with different inputs and expected results.

    Args:
        file_operation: Operation to test (list_files, read_file, grep_files)
        args: Arguments for the operation
        result: Mock result to return
        expected_strings: Strings expected in the response
        test_assertions: Assertions helper fixture
    """
    # Set up mock for FileExplorer
    with patch("mcp_server_troubleshoot.server.get_file_explorer") as mock_get_explorer:
        mock_explorer = Mock()
        mock_get_explorer.return_value = mock_explorer

        # Set up the mock result based on the operation
        if file_operation == "list_files":
            mock_explorer.list_files = AsyncMock(return_value=result)
            from mcp_server_troubleshoot.files import ListFilesArgs

            operation_args = ListFilesArgs(**args)
            response = await list_files(operation_args)
            mock_explorer.list_files.assert_awaited_once_with(args["path"], args["recursive"])

        elif file_operation == "read_file":
            mock_explorer.read_file = AsyncMock(return_value=result)
            from mcp_server_troubleshoot.files import ReadFileArgs

            operation_args = ReadFileArgs(**args)
            response = await read_file(operation_args)
            mock_explorer.read_file.assert_awaited_once_with(
                args["path"], args["start_line"], args["end_line"]
            )

        elif file_operation == "grep_files":
            mock_explorer.grep_files = AsyncMock(return_value=result)
            from mcp_server_troubleshoot.files import GrepFilesArgs

            operation_args = GrepFilesArgs(**args)
            response = await grep_files(operation_args)
            mock_explorer.grep_files.assert_awaited_once_with(
                args["pattern"],
                args["path"],
                args["recursive"],
                args["glob_pattern"],
                args["case_sensitive"],
                args["max_results"],
            )

        # Use the test assertion helper to verify response
        test_assertions.assert_api_response_valid(response, "text", expected_strings)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_type,error_message,expected_strings",
    [
        # File system errors
        (
            FileSystemError,
            "File not found: test.txt",
            ["File system error", "File not found: test.txt"],
        ),
        # Path not found errors
        (
            PathNotFoundError,
            "Path /nonexistent does not exist",
            ["File system error", "Path /nonexistent does not exist"],
        ),
        # Bundle manager errors
        (
            BundleManagerError,
            "No active bundle initialized",
            ["Bundle error", "No active bundle initialized"],
        ),
    ],
    ids=[
        "filesystem-error",
        "path-not-found",
        "bundle-manager-error",
    ],
)
async def test_file_operations_error_handling(
    error_type, error_message, expected_strings, test_assertions
):
    """
    Test that file operation tools properly handle various error types.

    Args:
        error_type: Type of error to simulate
        error_message: Error message to include
        expected_strings: Strings expected in the response
        test_assertions: Assertions helper fixture
    """
    # Set up mock for FileExplorer that raises the specified error
    with patch("mcp_server_troubleshoot.server.get_file_explorer") as mock_get_explorer:
        mock_explorer = Mock()
        mock_explorer.list_files = AsyncMock(side_effect=error_type(error_message))
        mock_explorer.read_file = AsyncMock(side_effect=error_type(error_message))
        mock_explorer.grep_files = AsyncMock(side_effect=error_type(error_message))
        mock_get_explorer.return_value = mock_explorer

        # Test all three file operations with the same error
        from mcp_server_troubleshoot.files import ListFilesArgs, ReadFileArgs, GrepFilesArgs

        # 1. Test list_files
        list_args = ListFilesArgs(path="test/path")
        list_response = await list_files(list_args)
        test_assertions.assert_api_response_valid(list_response, "text", expected_strings)

        # 2. Test read_file
        read_args = ReadFileArgs(path="test/file.txt")
        read_response = await read_file(read_args)
        test_assertions.assert_api_response_valid(read_response, "text", expected_strings)

        # 3. Test grep_files
        grep_args = GrepFilesArgs(pattern="test", path="test/path")
        grep_response = await grep_files(grep_args)
        test_assertions.assert_api_response_valid(grep_response, "text", expected_strings)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "include_invalid,bundles_available,expected_strings",
    [
        # With bundles available
        (False, True, ["support-bundle-1.tar.gz", "Usage Instructions", "initialize_bundle"]),
        # No bundles available
        (False, False, ["No support bundles found", "download or transfer a bundle"]),
        # With invalid bundles included
        (True, True, ["support-bundle-1.tar.gz", "validation_message", "initialize_bundle"]),
    ],
    ids=[
        "with-bundles",
        "no-bundles",
        "with-invalid-bundles",
    ],
)
async def test_list_available_bundles_parametrized(
    include_invalid, bundles_available, expected_strings, test_assertions, test_factory
):
    """
    Test the list_available_bundles tool with different scenarios.

    Args:
        include_invalid: Whether to include invalid bundles
        bundles_available: Whether any bundles are available
        expected_strings: Strings expected in the response
        test_assertions: Assertions helper fixture
        test_factory: Factory for test objects
    """
    # Set up a custom class for testing
    from dataclasses import dataclass

    @dataclass
    class MockAvailableBundle:
        name: str
        path: str
        relative_path: str
        size_bytes: int
        modified_time: float
        valid: bool
        validation_message: str = None

    # Set up mock for BundleManager
    with patch("mcp_server_troubleshoot.server.get_bundle_manager") as mock_get_manager:
        bundle_manager = Mock()
        mock_get_manager.return_value = bundle_manager

        # Create test bundles
        if bundles_available:
            bundles = [
                MockAvailableBundle(
                    name="support-bundle-1.tar.gz",
                    path="/bundles/support-bundle-1.tar.gz",
                    relative_path="support-bundle-1.tar.gz",
                    size_bytes=1024 * 1024,  # 1 MB
                    modified_time=1617292800.0,  # 2021-04-01
                    valid=True,
                ),
            ]

            # Add an invalid bundle if include_invalid is True
            if include_invalid:
                bundles.append(
                    MockAvailableBundle(
                        name="invalid-bundle.txt",
                        path="/bundles/invalid-bundle.txt",
                        relative_path="invalid-bundle.txt",
                        size_bytes=512,
                        modified_time=1617292800.0,
                        valid=False,
                        validation_message="Not a valid support bundle format",
                    )
                )
        else:
            bundles = []

        # Set up the mock return value
        bundle_manager.list_available_bundles = AsyncMock(return_value=bundles)

        # Create ListAvailableBundlesArgs instance
        from mcp_server_troubleshoot.bundle import ListAvailableBundlesArgs

        args = ListAvailableBundlesArgs(include_invalid=include_invalid)

        # Call the tool function
        response = await list_available_bundles(args)

        # Verify method call
        bundle_manager.list_available_bundles.assert_awaited_once_with(include_invalid)

        # Use the test assertion helper to verify response
        test_assertions.assert_api_response_valid(response, "text", expected_strings)


@pytest.mark.asyncio
async def test_cleanup_resources(test_assertions):
    """
    Test that the cleanup_resources function properly cleans up bundle manager resources.

    This test verifies:
    1. The global shutdown flag is set
    2. The bundle manager cleanup method is called
    3. Multiple cleanup calls are handled correctly

    Args:
        test_assertions: Assertions helper fixture
    """
    # Mock both app_context and legacy bundle manager
    with (
        patch("mcp_server_troubleshoot.server.get_app_context") as mock_get_context,
        patch("mcp_server_troubleshoot.server.globals") as mock_globals,
    ):

        # Reset shutdown flag
        import mcp_server_troubleshoot.server

        mcp_server_troubleshoot.server._is_shutting_down = False

        # Setup app context mode
        mock_app_context = AsyncMock()
        mock_app_context.bundle_manager = AsyncMock()
        mock_app_context.bundle_manager.cleanup = AsyncMock()

        # Set return value for get_app_context
        mock_get_context.return_value = mock_app_context

        # Mock globals for legacy mode
        mock_globals.return_value = {
            "_bundle_manager": None  # Not used in this test since we test app_context mode
        }

        # Call cleanup_resources
        await cleanup_resources()

        # Verify cleanup was called on app context bundle manager
        mock_app_context.bundle_manager.cleanup.assert_awaited_once()

        # Verify shutdown flag was set
        assert mcp_server_troubleshoot.server._is_shutting_down is True

        # Reset mock
        mock_app_context.bundle_manager.cleanup.reset_mock()

        # Call cleanup_resources again (should not call cleanup again)
        await cleanup_resources()

        # Verify cleanup was not called again
        mock_app_context.bundle_manager.cleanup.assert_not_awaited()

    # Now test legacy mode
    with (
        patch("mcp_server_troubleshoot.server.get_app_context") as mock_get_context,
        patch("mcp_server_troubleshoot.server.globals") as mock_globals,
    ):

        # Reset shutdown flag
        mcp_server_troubleshoot.server._is_shutting_down = False

        # Setup legacy mode (no app context)
        mock_get_context.return_value = None

        # Setup legacy bundle manager
        mock_bundle_manager = AsyncMock()
        mock_bundle_manager.cleanup = AsyncMock()

        # Mock globals for legacy mode
        mock_globals.return_value = {"_bundle_manager": mock_bundle_manager}

        # Call cleanup_resources
        await cleanup_resources()

        # Verify cleanup was called on legacy bundle manager
        mock_bundle_manager.cleanup.assert_awaited_once()

        # Verify shutdown flag was set
        assert mcp_server_troubleshoot.server._is_shutting_down is True


@pytest.mark.asyncio
async def test_register_signal_handlers():
    """
    Test that the register_signal_handlers function properly sets up handlers for signals.

    This test verifies:
    1. Signal handlers are registered for SIGINT and SIGTERM
    2. The event loop's add_signal_handler method is called
    """
    # Mock the asyncio module
    with patch("asyncio.get_running_loop") as mock_get_loop:
        mock_loop = Mock()
        mock_get_loop.return_value = mock_loop
        mock_loop.is_closed.return_value = False
        mock_loop.add_signal_handler = Mock()

        # Call register_signal_handlers
        register_signal_handlers()

        # Verify add_signal_handler was called for each signal
        import signal

        if hasattr(signal, "SIGTERM"):  # Check for POSIX signals
            assert mock_loop.add_signal_handler.call_count >= 1
        else:  # Windows
            mock_loop.add_signal_handler.assert_called_once()


@pytest.mark.asyncio
async def test_shutdown_function():
    """
    Test that the shutdown function properly triggers cleanup process.

    This test verifies:
    1. In an async context, cleanup_resources is called as a task
    2. In a non-async context, a new event loop is created
    3. Cleanup is properly called in both cases
    """
    # Test case 1: With running loop (async context)
    with (
        patch("asyncio.get_running_loop") as mock_get_loop,
        patch("asyncio.create_task") as mock_create_task,
        patch("mcp_server_troubleshoot.server.cleanup_resources"),
    ):

        mock_loop = Mock()
        mock_get_loop.return_value = mock_loop
        mock_loop.is_closed.return_value = False

        # Call shutdown
        shutdown()

        # Verify create_task was called
        mock_create_task.assert_called_once()

    # Test case 2: Without running loop (non-async context)
    with (
        patch("asyncio.get_running_loop", side_effect=RuntimeError("No running loop")),
        patch("asyncio.new_event_loop") as mock_new_loop,
        patch("asyncio.set_event_loop") as mock_set_loop,
        patch("mcp_server_troubleshoot.server.cleanup_resources"),
    ):

        mock_loop = Mock()
        mock_new_loop.return_value = mock_loop

        # Call shutdown
        shutdown()

        # Verify new_event_loop and set_event_loop were called
        mock_new_loop.assert_called_once()
        mock_set_loop.assert_called_once_with(mock_loop)

        # Verify run_until_complete was called
        mock_loop.run_until_complete.assert_called_once()

        # Verify loop was closed
        mock_loop.close.assert_called_once()
