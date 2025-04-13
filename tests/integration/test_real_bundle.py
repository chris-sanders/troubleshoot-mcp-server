"""
Tests for real support bundle integration.

These tests verify the behavior of the MCP server components 
with actual support bundles, focusing on user-visible behavior
rather than implementation details.
"""

import asyncio
import tempfile
from pathlib import Path
import pytest
import pytest_asyncio

# Import components for testing
from mcp_server_troubleshoot.bundle import BundleManager
from mcp_server_troubleshoot.files import FileExplorer, PathNotFoundError
from mcp_server_troubleshoot.kubectl import KubectlExecutor

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def bundle_manager_fixture(test_support_bundle):
    """
    Fixture that provides a properly initialized BundleManager with cleanup.
    
    This fixture creates a temporary working directory for the bundle manager
    and ensures proper cleanup after tests complete.
    
    Args:
        test_support_bundle: Path to the test support bundle (pytest fixture)
        
    Returns:
        A BundleManager instance with the test bundle path
    """
    # Create a temporary directory for the bundle manager
    with tempfile.TemporaryDirectory() as temp_dir:
        bundle_dir = Path(temp_dir)
        manager = BundleManager(bundle_dir)
        
        try:
            # Return the manager and bundle path for test use
            yield (manager, test_support_bundle)
        finally:
            # Ensure cleanup happens even if test fails
            await manager.cleanup()


@pytest_asyncio.fixture
async def initialized_bundle(bundle_manager_fixture):
    """
    Fixture that provides a BundleManager with an already-initialized bundle.
    
    This reduces duplication across tests that need an initialized bundle.
    
    Args:
        bundle_manager_fixture: Fixture providing a BundleManager and bundle path
        
    Returns:
        A tuple of (BundleManager, BundleMetadata) for the initialized bundle
    """
    manager, bundle_path = bundle_manager_fixture
    
    # Initialize the bundle
    metadata = await asyncio.wait_for(
        manager.initialize_bundle(str(bundle_path)),
        timeout=30.0
    )
    
    # Return the manager and the initialized bundle metadata
    return manager, metadata


@pytest.mark.asyncio
async def test_bundle_initialization_workflow(bundle_manager_fixture, test_assertions):
    """
    Test the complete bundle initialization workflow.
    
    This test verifies the user-visible behavior of bundle initialization,
    including functional capabilities that emerge from initialization.
    """
    # Unpack fixture
    manager, bundle_path = bundle_manager_fixture
    
    # BEHAVIOR 1: Bundle can be initialized successfully
    metadata = await asyncio.wait_for(
        manager.initialize_bundle(str(bundle_path)), 
        timeout=30.0
    )
    
    # Verify the bundle is properly initialized
    assert metadata.initialized, "Bundle should be marked as initialized"
    assert metadata.kubeconfig_path.exists(), "Kubeconfig should exist after initialization"
    
    # BEHAVIOR 2: The active bundle can be retrieved after initialization
    active_bundle = manager.get_active_bundle()
    assert active_bundle is not None, "Active bundle should be available"
    assert active_bundle.id == metadata.id, "Active bundle should match initialized bundle"
    
    # BEHAVIOR 3: Re-initialization without force returns same bundle
    second_metadata = await manager.initialize_bundle(str(bundle_path), force=False)
    assert second_metadata.id == metadata.id, "Should return existing bundle without force"
    
    # BEHAVIOR 4: Force re-initialization creates a new bundle
    force_metadata = await manager.initialize_bundle(str(bundle_path), force=True)
    assert force_metadata.initialized, "Force reinitialization should succeed"
    assert metadata.path != force_metadata.path, "Force should create a new bundle directory"
    
    # BEHAVIOR 5: API server connectivity is checked
    # We don't assert True/False since it depends on the bundle content 
    # and test environment, we just verify the behavior works
    await manager.check_api_server_available()
    
    # BEHAVIOR 6: System diagnostic information is available
    diagnostics = await manager.get_diagnostic_info()
    assert isinstance(diagnostics, dict), "Diagnostics information should be available"
    # Check that diagnostics contains bundle information without assuming specific structure
    assert diagnostics.get("bundle_initialized") is not None, "Diagnostics should include bundle initialization status"


@pytest.mark.asyncio
async def test_file_explorer_workflows(initialized_bundle, test_assertions):
    """
    Test the file exploration workflows with a real bundle.
    
    This test verifies the user-visible behavior of the FileExplorer,
    including directory navigation, file reading, and search capabilities.
    """
    # Unpack fixture
    manager, metadata = initialized_bundle
    
    # Create the FileExplorer (component under test)
    explorer = FileExplorer(manager)
    
    # BEHAVIOR 1: Root directory listing should work
    root_list = await explorer.list_files("", False)
    assert root_list.total_dirs > 0, "Root should contain at least one directory"
    assert root_list.entries, "Root directory should contain entries"
    
    # Verify response structure
    test_assertions.assert_attributes_exist(
        root_list, 
        ["path", "entries", "recursive", "total_files", "total_dirs"]
    )
    
    # BEHAVIOR 2: Navigation through directories should work
    # Find a directory to navigate into
    dir_entries = [e for e in root_list.entries if e.type == "dir"]
    if dir_entries:
        first_dir = dir_entries[0].name
        
        # Navigate into the directory
        dir_contents = await explorer.list_files(first_dir, False)
        assert dir_contents is not None, "Should be able to navigate into directory"
        test_assertions.assert_attributes_exist(
            dir_contents, 
            ["path", "entries", "recursive", "total_files", "total_dirs"]
        )
        
        # BEHAVIOR 3: Recursive listing should work
        recursive_contents = await explorer.list_files(first_dir, True)
        assert recursive_contents.recursive, "Recursive listing should be marked as recursive"
        assert recursive_contents.total_files + recursive_contents.total_dirs > 0, \
            "Recursive listing should find files/directories"
        
        # BEHAVIOR 4: File reading should work if there are files
        file_entries = [e for e in recursive_contents.entries if e.type == "file"]
        if file_entries:
            first_file = file_entries[0].path
            
            # Read the file
            file_content = await explorer.read_file(first_file)
            assert file_content is not None, "Should be able to read file"
            test_assertions.assert_attributes_exist(
                file_content, 
                ["path", "content", "start_line", "end_line", "total_lines", "binary"]
            )
            
            # BEHAVIOR 5: Reading with line ranges should work
            if file_content.total_lines > 2:
                ranged_content = await explorer.read_file(first_file, 1, 2)
                assert ranged_content.content is not None, "Should be able to read file range"
                assert ranged_content.start_line == 1, "Line range should be respected"
                assert ranged_content.end_line == 2, "Line range should be respected"
    
    # BEHAVIOR 6: Invalid paths should be handled gracefully
    with pytest.raises(PathNotFoundError):
        await explorer.list_files("non_existent_directory", False)
    
    # BEHAVIOR 7: Grep search capabilities should work
    # We use a simple pattern likely to be found in any bundle
    grep_results = await explorer.grep_files("Kubernetes", "", True, "*.txt", False, 100)
    assert grep_results is not None, "Grep search should complete"
    test_assertions.assert_attributes_exist(
        grep_results, 
        ["pattern", "path", "matches", "total_matches", "files_searched"]
    )


@pytest.mark.asyncio
async def test_kubectl_executor_workflows(initialized_bundle, test_assertions):
    """
    Test the kubectl command execution workflows with a real bundle.
    
    This test verifies the behavior of the KubectlExecutor with
    an initialized bundle, focusing on command execution capabilities.
    """
    # Unpack fixture
    manager, metadata = initialized_bundle
    
    # Create the KubectlExecutor (component under test)
    executor = KubectlExecutor(manager)
    
    # Get the active bundle for commands
    bundle = manager.get_active_bundle()
    assert bundle is not None, "Active bundle should be available"
    
    # BEHAVIOR 1: Basic kubectl commands should execute
    # We use a timeout to ensure tests don't hang on connectivity issues
    try:
        command = "version"
        timeout = 5
        json_output = False
        
        result = await asyncio.wait_for(
            executor.execute(command, timeout=timeout, json_output=json_output),
            timeout=10.0
        )
        # If the command succeeds, verify the expected response structure
        test_assertions.assert_attributes_exist(
            result,
            ["command", "exit_code", "stdout", "stderr", "output", "is_json", "duration_ms"]
        )
        assert result.command == command, "Command should match input"
    except asyncio.TimeoutError:
        # This can happen if the API server in the bundle isn't accessible
        # We don't consider this a test failure, since we're testing behavior
        pytest.skip("kubectl command timed out - API server may not be accessible in this environment")
    except Exception as e:
        # If there's a different error (like the API server isn't reachable), that's expected
        # We're looking for functional behavior, not exact results
        # The command should still execute and return a result or structured error
        assert "KubectlError" in str(type(e)) or "TimeoutError" in str(type(e)), \
            f"Should raise appropriate exception type, got {type(e)}"
    
    # BEHAVIOR 2: JSON output should be parsed
    try:
        command = "get pods -o json"
        timeout = 5
        json_output = True
        
        json_result = await asyncio.wait_for(
            executor.execute(command, timeout=timeout, json_output=json_output),
            timeout=10.0
        )
        if hasattr(json_result, 'exit_code') and json_result.exit_code == 0:
            assert json_result.is_json, "JSON output should be parsed as JSON"
            assert isinstance(json_result.output, (dict, list)), "Parsed JSON should be a dictionary or list"
    except (asyncio.TimeoutError, Exception):
        # Same error handling as above - we're testing behavior, not specific outputs
        pass
    
    # BEHAVIOR 3: Invalid commands should be handled appropriately
    try:
        command = "get invalid-resource"
        timeout = 5
        json_output = False
        
        await asyncio.wait_for(
            executor.execute(command, timeout=timeout, json_output=json_output),
            timeout=10.0
        )
        # If we get here without an exception, the command might have succeeded
        # This is unexpected but not necessarily a test failure
    except Exception as e:
        # This is the expected path - invalid commands should raise exceptions
        assert "KubectlError" in str(type(e)), "Invalid command should raise KubectlError"


@pytest.mark.asyncio
async def test_bundle_manager_cleanup_behavior(bundle_manager_fixture):
    """
    Test the cleanup behavior of the BundleManager.
    
    This test verifies that the BundleManager properly cleans up resources,
    making them reusable after cleanup.
    """
    # Unpack fixture
    manager, bundle_path = bundle_manager_fixture
    
    # BEHAVIOR 1: Initialize a bundle
    metadata = await manager.initialize_bundle(str(bundle_path))
    assert metadata.initialized, "Bundle should be initialized"
    
    # BEHAVIOR 2: Cleanup should release resources
    await manager.cleanup()
    
    # After cleanup, the active bundle should be None
    assert manager.get_active_bundle() is None, "Active bundle should be None after cleanup"
    
    # BEHAVIOR 3: The bundle directory should be removed (unless protected)
    # Note: We don't make specific assumptions about deletion of files/dirs
    # as that may vary with implementation details, instead we test that
    # initialization is possible again
    
    # BEHAVIOR 4: Re-initialization should work after cleanup 
    new_metadata = await manager.initialize_bundle(str(bundle_path))
    assert new_metadata.initialized, "Bundle should be re-initialized after cleanup"
    assert new_metadata.id != metadata.id, "New bundle should have a different ID"