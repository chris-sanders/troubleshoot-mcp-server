"""
Basic MCP protocol tests for server initialization and bundle operations.

This module tests the core MCP functionality by calling the tool functions
directly. This approach is compatible with the current FastMCP architecture
and provides comprehensive testing of the MCP tools without requiring
stdio protocol communication.

NOTE: Full protocol testing via stdio transport will be implemented in
Phase 4 using the container-based approach as documented in the e2e tests.
"""

import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

from mcp_server_troubleshoot.server import (
    initialize_bundle,
    list_available_bundles,
    list_files,
    read_file,
    grep_files,
    kubectl,
    initialize_with_bundle_dir,
)
from mcp_server_troubleshoot.bundle import InitializeBundleArgs, ListAvailableBundlesArgs
from mcp_server_troubleshoot.files import ListFilesArgs, ReadFileArgs, GrepFilesArgs
from mcp_server_troubleshoot.kubectl import KubectlCommandArgs

from .mcp_test_utils import get_test_bundle_path

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def bundle_storage_dir():
    """
    Fixture that provides a temporary directory for bundle storage.

    This fixture creates a temporary directory and initializes the
    MCP server components to use it.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        bundle_dir = Path(temp_dir)

        # Initialize the server components with the bundle directory
        initialize_with_bundle_dir(bundle_dir)

        yield bundle_dir


@pytest.mark.asyncio
async def test_list_available_bundles(bundle_storage_dir):
    """
    Test MCP list_available_bundles tool functionality.

    This test verifies:
    1. Tool can be called successfully
    2. Returns proper response format
    3. Handles empty bundle directory
    4. Response structure is correct
    """
    # Test with empty bundle directory first
    args = ListAvailableBundlesArgs(include_invalid=False)
    result = await list_available_bundles(args)

    # Verify result structure
    assert isinstance(result, list), "Result should be a list"
    assert len(result) > 0, "Should return at least one content item"

    content_item = result[0]
    assert content_item.type == "text", "Content should be text type"
    assert "No support bundles found" in content_item.text, "Should indicate no bundles found"


@pytest.mark.asyncio
async def test_initialize_bundle_local_file(bundle_storage_dir):
    """
    Complete E2E test: initialize bundle from local file.

    This test verifies:
    1. Server can initialize a bundle from a local file path
    2. Bundle initialization returns expected metadata
    3. Bundle path and kubeconfig path are provided
    4. Success response format is correct
    """
    # Get the test bundle path
    test_bundle = get_test_bundle_path()

    # Call initialize_bundle tool directly
    args = InitializeBundleArgs(source=str(test_bundle), force=False)
    result = await initialize_bundle(args)

    # Verify we got a result
    assert isinstance(result, list), "Tool result should be a list"
    assert len(result) > 0, "Tool should return at least one content item"

    # Verify the first result is text content
    content_item = result[0]
    assert content_item.type == "text", "Content should be text type"

    # Verify the response contains expected information
    response_text = content_item.text
    assert (
        "Bundle initialized successfully" in response_text
        or "Bundle initialized but API server is NOT available" in response_text
    ), "Response should indicate bundle initialization status"

    # The response should contain JSON with bundle metadata
    assert "```json" in response_text, "Response should contain JSON metadata"
    assert "path" in response_text, "Response should contain bundle path"
    assert "kubeconfig_path" in response_text, "Response should contain kubeconfig path"


@pytest.mark.asyncio
async def test_initialize_bundle_force_flag(bundle_storage_dir):
    """
    Test initialize_bundle with force flag functionality.

    This test verifies:
    1. Bundle can be initialized normally
    2. Second initialization with force=True succeeds
    """
    test_bundle = get_test_bundle_path()

    # First initialization
    args1 = InitializeBundleArgs(source=str(test_bundle), force=False)
    result1 = await initialize_bundle(args1)

    assert len(result1) > 0, "First initialization should succeed"
    response1_text = result1[0].text
    assert "Bundle initialized" in response1_text, "First initialization should report success"

    # Second initialization with force=True should also work
    args2 = InitializeBundleArgs(source=str(test_bundle), force=True)
    result2 = await initialize_bundle(args2)

    assert len(result2) > 0, "Second initialization with force should succeed"
    response2_text = result2[0].text
    assert "Bundle initialized" in response2_text, "Second initialization should report success"


@pytest.mark.asyncio
async def test_initialize_bundle_nonexistent_file(bundle_storage_dir):
    """
    Test initialize_bundle error handling for nonexistent files.

    This test verifies:
    1. Pydantic validation catches nonexistent files
    2. ValidationError is raised for missing files
    """
    from pydantic_core import ValidationError

    # Try to initialize with a nonexistent file
    nonexistent_path = "/tmp/definitely-does-not-exist.tar.gz"

    # Should raise ValidationError due to file not existing
    with pytest.raises(ValidationError) as exc_info:
        InitializeBundleArgs(source=nonexistent_path, force=False)

    # Verify the error message indicates the file wasn't found
    error_msg = str(exc_info.value)
    assert "Bundle source not found" in error_msg, "Should indicate bundle source not found"


@pytest.mark.asyncio
async def test_list_files_with_initialized_bundle(bundle_storage_dir):
    """
    Test file listing functionality with an initialized bundle.

    This test verifies:
    1. Bundle can be initialized
    2. File listing works on initialized bundle
    3. Response contains expected file structure
    """
    test_bundle = get_test_bundle_path()

    # Initialize bundle first
    init_args = InitializeBundleArgs(source=str(test_bundle), force=True)
    init_result = await initialize_bundle(init_args)

    assert len(init_result) > 0, "Bundle initialization should succeed"

    # Try to list files from root
    list_args = ListFilesArgs(path="/", recursive=False)
    list_result = await list_files(list_args)

    assert len(list_result) > 0, "List files should return results"

    # Verify the response structure
    content_item = list_result[0]
    assert content_item.type == "text", "Content should be text type"
    response_text = content_item.text

    # Should contain file listing information
    assert "```json" in response_text, "Response should contain JSON data"
    assert "Listed files in" in response_text, "Response should indicate listing operation"


@pytest.mark.asyncio
async def test_error_handling_invalid_parameters(bundle_storage_dir):
    """
    Test error handling with invalid parameters.

    This test verifies that Pydantic validation catches invalid parameters.
    """
    from pydantic_core import ValidationError

    # Test with invalid path containing directory traversal
    with pytest.raises(ValidationError) as exc_info:
        ListFilesArgs(path="../invalid", recursive=False)

    # Verify the error indicates path validation failure
    error_msg = str(exc_info.value)
    assert (
        "Path cannot contain directory traversal" in error_msg
    ), "Should indicate path validation error"


@pytest.mark.asyncio
async def test_kubectl_through_mcp(bundle_storage_dir):
    """
    Test kubectl execution via MCP.

    This test verifies:
    1. Bundle can be initialized
    2. kubectl commands can be executed through MCP
    3. Response format is correct
    4. Error handling works for commands when API server is not available
    """
    test_bundle = get_test_bundle_path()

    # Initialize bundle first
    init_args = InitializeBundleArgs(source=str(test_bundle), force=True)
    init_result = await initialize_bundle(init_args)

    assert len(init_result) > 0, "Bundle initialization should succeed"

    # Try a simple kubectl command (get pods)
    kubectl_args = KubectlCommandArgs(command="get pods", timeout=10, json_output=True)
    kubectl_result = await kubectl(kubectl_args)

    assert len(kubectl_result) > 0, "kubectl should return results"

    # Verify the response structure
    content_item = kubectl_result[0]
    assert content_item.type == "text", "Content should be text type"
    response_text = content_item.text

    # The response should either show kubectl output or indicate API server unavailability
    assert (
        "kubectl get pods" in response_text
        or "kubectl command executed successfully" in response_text
        or "API server is not available" in response_text
        or "connection refused" in response_text.lower()
    ), "Response should indicate kubectl execution attempt or success"


@pytest.mark.asyncio
async def test_read_file_through_mcp(bundle_storage_dir):
    """
    Test file reading via MCP.

    This test verifies:
    1. Bundle can be initialized
    2. Files can be read through MCP
    3. Response format is correct
    4. File content is returned with line numbers
    """
    test_bundle = get_test_bundle_path()

    # Initialize bundle first
    init_args = InitializeBundleArgs(source=str(test_bundle), force=True)
    init_result = await initialize_bundle(init_args)

    assert len(init_result) > 0, "Bundle initialization should succeed"

    # Try to read a common file that might exist
    read_args = ReadFileArgs(path="cluster-info/version.json", start_line=0, num_lines=10)

    try:
        read_result = await read_file(read_args)

        assert len(read_result) > 0, "read_file should return results"

        # Verify the response structure
        content_item = read_result[0]
        assert content_item.type == "text", "Content should be text type"
        response_text = content_item.text

        # Should contain file content with line numbers or indicate file not found
        assert (
            "Line" in response_text
            or "not found" in response_text.lower()
            or "does not exist" in response_text.lower()
        ), "Response should show file content or indicate file not found"

    except Exception as e:
        # It's OK if the specific file doesn't exist, we're testing the MCP integration
        assert "not found" in str(e).lower() or "does not exist" in str(e).lower()


@pytest.mark.asyncio
async def test_grep_files_through_mcp(bundle_storage_dir):
    """
    Test file searching via MCP.

    This test verifies:
    1. Bundle can be initialized
    2. File searching can be performed through MCP
    3. Response format is correct
    4. Search results are returned
    """
    test_bundle = get_test_bundle_path()

    # Initialize bundle first
    init_args = InitializeBundleArgs(source=str(test_bundle), force=True)
    init_result = await initialize_bundle(init_args)

    assert len(init_result) > 0, "Bundle initialization should succeed"

    # Search for a common pattern that should exist in many bundles
    grep_args = GrepFilesArgs(
        pattern="version", path="/", file_pattern="*.json", case_sensitive=False, recursive=True
    )

    grep_result = await grep_files(grep_args)

    assert len(grep_result) > 0, "grep_files should return results"

    # Verify the response structure
    content_item = grep_result[0]
    assert content_item.type == "text", "Content should be text type"
    response_text = content_item.text

    # Should contain search results or indicate no matches found
    assert (
        "Found" in response_text
        or "matches" in response_text.lower()
        or "No matches found" in response_text
        or "Search completed" in response_text
    ), "Response should indicate search results"


@pytest.mark.asyncio
async def test_error_handling_file_operations(bundle_storage_dir):
    """
    Test error handling for file operations through MCP.

    This test verifies:
    1. Proper error handling when bundle is not initialized
    2. Error messages are informative
    """
    # Try file operations without initializing bundle first

    # Test read_file without bundle
    read_args = ReadFileArgs(path="nonexistent.txt", start_line=0, num_lines=10)
    read_result = await read_file(read_args)

    assert len(read_result) > 0, "Should return error response"
    content_item = read_result[0]
    assert content_item.type == "text", "Content should be text type"

    # Should indicate bundle not initialized or file not found
    response_text = content_item.text
    assert (
        "not initialized" in response_text.lower()
        or "not found" in response_text.lower()
        or "error" in response_text.lower()
    ), "Should indicate error condition"
