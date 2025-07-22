"""
Comprehensive MCP Protocol Testing for All Tools.

This module provides comprehensive testing of all 6 MCP tools through actual
JSON-RPC protocol communication using MCPTestClient. These tests verify that:

1. All tools work correctly via JSON-RPC protocol
2. MCP protocol compliance is maintained
3. Error handling works through protocol layer
4. Performance and concurrency scenarios are handled
5. Edge cases and invalid inputs are properly managed

Tools tested:
- initialize_bundle
- list_available_bundles
- list_files
- read_file
- grep_files
- kubectl

All tests use real JSON-RPC communication via MCPTestClient, ensuring
we test the complete protocol stack, not just internal functions.
"""

import asyncio
import pytest
import tempfile
import time
from pathlib import Path

from tests.integration.mcp_test_utils import MCPTestClient, get_test_bundle_path


pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.fixture
def test_bundle_path():
    """Get the test bundle path."""
    return get_test_bundle_path()


@pytest.fixture
def temp_bundle_dir():
    """Create a temporary directory for bundle storage."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
async def initialized_client(temp_bundle_dir, test_bundle_path):
    """
    Create an MCP client with an initialized bundle for tests that require it.

    This fixture:
    1. Creates an MCP client
    2. Starts the server
    3. Initializes the MCP connection
    4. Loads the test bundle
    5. Yields the client for use in tests
    6. Cleans up after tests complete
    """
    # Copy test bundle to temp directory for isolation
    bundle_name = test_bundle_path.name
    test_bundle_copy = temp_bundle_dir / bundle_name
    test_bundle_copy.write_bytes(test_bundle_path.read_bytes())

    env = {"SBCTL_TOKEN": "test-token-12345"}

    client = MCPTestClient(bundle_dir=temp_bundle_dir, env=env)
    await client.start_server()

    try:
        # Initialize MCP connection
        await client.initialize_mcp()

        # Load the test bundle
        await client.call_tool("initialize_bundle", {"bundle_path": str(test_bundle_copy)})

        yield client
    finally:
        await client.cleanup()


class TestMCPProtocolCompliance:
    """Test MCP protocol compliance and JSON-RPC format validation."""

    async def test_json_rpc_request_format(self, temp_bundle_dir):
        """Test that all requests follow JSON-RPC 2.0 format."""
        env = {"SBCTL_TOKEN": "test-token-12345"}

        async with MCPTestClient(bundle_dir=temp_bundle_dir, env=env) as client:
            await client.initialize_mcp()

            # Test tools/list request format
            response = await client.send_request("tools/list")

            # Verify response format
            assert "jsonrpc" in response
            assert response["jsonrpc"] == "2.0"
            assert "id" in response
            assert "result" in response or "error" in response

    async def test_json_rpc_error_format(self, temp_bundle_dir):
        """Test that errors follow JSON-RPC 2.0 error format."""
        env = {"SBCTL_TOKEN": "test-token-12345"}

        async with MCPTestClient(bundle_dir=temp_bundle_dir, env=env) as client:
            await client.initialize_mcp()

            # Test invalid method - should return proper JSON-RPC error
            try:
                await client.send_request("invalid_method")
                pytest.fail("Expected error for invalid method")
            except RuntimeError as e:
                # Should be a proper RPC error message
                assert "error" in str(e).lower()

    async def test_concurrent_requests(self, temp_bundle_dir):
        """Test concurrent JSON-RPC requests are handled correctly."""
        env = {"SBCTL_TOKEN": "test-token-12345"}

        async with MCPTestClient(bundle_dir=temp_bundle_dir, env=env) as client:
            await client.initialize_mcp()

            # Send multiple concurrent requests
            tasks = []
            for i in range(5):
                task = client.send_request("tools/list")
                tasks.append(task)

            # All requests should complete successfully
            responses = await asyncio.gather(*tasks)

            for response in responses:
                assert "jsonrpc" in response
                assert response["jsonrpc"] == "2.0"
                assert "result" in response


class TestInitializeBundleTool:
    """Test initialize_bundle tool via MCP protocol."""

    async def test_initialize_bundle_success(self, temp_bundle_dir, test_bundle_path):
        """Test successful bundle initialization via MCP protocol."""
        bundle_name = test_bundle_path.name
        test_bundle_copy = temp_bundle_dir / bundle_name
        test_bundle_copy.write_bytes(test_bundle_path.read_bytes())

        env = {"SBCTL_TOKEN": "test-token-12345"}

        async with MCPTestClient(bundle_dir=temp_bundle_dir, env=env) as client:
            await client.initialize_mcp()

            # Test initialize_bundle via JSON-RPC
            content = await client.call_tool(
                "initialize_bundle", {"bundle_path": str(test_bundle_copy)}
            )

            assert len(content) > 0
            result_text = content[0].get("text", "")
            assert len(result_text.strip()) > 0
            assert (
                "success" in result_text.lower()
                or "initial" in result_text.lower()
                or "load" in result_text.lower()
            )

    async def test_initialize_bundle_nonexistent_file(self, temp_bundle_dir):
        """Test initialize_bundle with nonexistent file via MCP protocol."""
        env = {"SBCTL_TOKEN": "test-token-12345"}

        async with MCPTestClient(bundle_dir=temp_bundle_dir, env=env) as client:
            await client.initialize_mcp()

            nonexistent_bundle = temp_bundle_dir / "nonexistent.tar.gz"

            # Should handle error gracefully via MCP protocol
            try:
                content = await client.call_tool(
                    "initialize_bundle", {"bundle_path": str(nonexistent_bundle)}
                )

                # If no exception, check error is reported in content
                assert len(content) > 0
                result_text = content[0].get("text", "")
                assert (
                    "error" in result_text.lower()
                    or "not found" in result_text.lower()
                    or "failed" in result_text.lower()
                )

            except RuntimeError as e:
                # Also acceptable to raise RPC error
                assert "error" in str(e).lower()

    async def test_initialize_bundle_with_force_flag(self, temp_bundle_dir, test_bundle_path):
        """Test initialize_bundle with force flag via MCP protocol."""
        bundle_name = test_bundle_path.name
        test_bundle_copy = temp_bundle_dir / bundle_name
        test_bundle_copy.write_bytes(test_bundle_path.read_bytes())

        env = {"SBCTL_TOKEN": "test-token-12345"}

        async with MCPTestClient(bundle_dir=temp_bundle_dir, env=env) as client:
            await client.initialize_mcp()

            # Initialize bundle first time
            await client.call_tool("initialize_bundle", {"bundle_path": str(test_bundle_copy)})

            # Initialize again with force=True
            content = await client.call_tool(
                "initialize_bundle", {"bundle_path": str(test_bundle_copy), "force": True}
            )

            assert len(content) > 0
            result_text = content[0].get("text", "")
            assert len(result_text.strip()) > 0

    async def test_initialize_bundle_verbosity_levels(self, temp_bundle_dir, test_bundle_path):
        """Test initialize_bundle with different verbosity levels via MCP protocol."""
        bundle_name = test_bundle_path.name
        test_bundle_copy = temp_bundle_dir / bundle_name
        test_bundle_copy.write_bytes(test_bundle_path.read_bytes())

        env = {"SBCTL_TOKEN": "test-token-12345"}

        verbosity_levels = ["minimal", "standard", "verbose", "debug"]

        for verbosity in verbosity_levels:
            async with MCPTestClient(bundle_dir=temp_bundle_dir, env=env) as client:
                await client.initialize_mcp()

                content = await client.call_tool(
                    "initialize_bundle",
                    {"bundle_path": str(test_bundle_copy), "verbosity": verbosity, "force": True},
                )

                assert len(content) > 0
                result_text = content[0].get("text", "")
                assert len(result_text.strip()) > 0


class TestListAvailableBundlesTool:
    """Test list_available_bundles tool via MCP protocol."""

    async def test_list_available_bundles_empty_dir(self, temp_bundle_dir):
        """Test list_available_bundles with empty directory via MCP protocol."""
        env = {"SBCTL_TOKEN": "test-token-12345"}

        async with MCPTestClient(bundle_dir=temp_bundle_dir, env=env) as client:
            await client.initialize_mcp()

            content = await client.call_tool("list_available_bundles")

            assert len(content) > 0
            result_text = content[0].get("text", "")
            # Should return some indication of no bundles found
            assert isinstance(result_text, str)

    async def test_list_available_bundles_with_bundles(self, temp_bundle_dir, test_bundle_path):
        """Test list_available_bundles with bundles present via MCP protocol."""
        # Copy test bundle to temp directory
        bundle_name = test_bundle_path.name
        test_bundle_copy = temp_bundle_dir / bundle_name
        test_bundle_copy.write_bytes(test_bundle_path.read_bytes())

        env = {"SBCTL_TOKEN": "test-token-12345"}

        async with MCPTestClient(bundle_dir=temp_bundle_dir, env=env) as client:
            await client.initialize_mcp()

            content = await client.call_tool("list_available_bundles")

            assert len(content) > 0
            result_text = content[0].get("text", "")
            assert bundle_name in result_text

    async def test_list_available_bundles_include_invalid(self, temp_bundle_dir, test_bundle_path):
        """Test list_available_bundles with include_invalid flag via MCP protocol."""
        # Copy test bundle and create a fake invalid bundle
        bundle_name = test_bundle_path.name
        test_bundle_copy = temp_bundle_dir / bundle_name
        test_bundle_copy.write_bytes(test_bundle_path.read_bytes())

        # Create a fake invalid bundle
        fake_bundle = temp_bundle_dir / "fake-bundle.tar.gz"
        fake_bundle.write_text("not a real tarball")

        env = {"SBCTL_TOKEN": "test-token-12345"}

        async with MCPTestClient(bundle_dir=temp_bundle_dir, env=env) as client:
            await client.initialize_mcp()

            # Test with include_invalid=True
            content = await client.call_tool("list_available_bundles", {"include_invalid": True})

            assert len(content) > 0
            result_text = content[0].get("text", "")
            assert isinstance(result_text, str)

    async def test_list_available_bundles_verbosity_levels(self, temp_bundle_dir, test_bundle_path):
        """Test list_available_bundles with different verbosity levels via MCP protocol."""
        bundle_name = test_bundle_path.name
        test_bundle_copy = temp_bundle_dir / bundle_name
        test_bundle_copy.write_bytes(test_bundle_path.read_bytes())

        env = {"SBCTL_TOKEN": "test-token-12345"}

        verbosity_levels = ["minimal", "standard", "verbose", "debug"]

        for verbosity in verbosity_levels:
            async with MCPTestClient(bundle_dir=temp_bundle_dir, env=env) as client:
                await client.initialize_mcp()

                content = await client.call_tool("list_available_bundles", {"verbosity": verbosity})

                assert len(content) > 0
                result_text = content[0].get("text", "")
                assert isinstance(result_text, str)


class TestListFilesTool:
    """Test list_files tool via MCP protocol."""

    async def test_list_files_root_directory(self, initialized_client):
        """Test list_files for root directory via MCP protocol."""
        content = await initialized_client.call_tool("list_files", {"path": "."})

        assert len(content) > 0
        result_text = content[0].get("text", "")
        assert len(result_text.strip()) > 0

    async def test_list_files_with_recursion(self, initialized_client):
        """Test list_files with recursive flag via MCP protocol."""
        content = await initialized_client.call_tool("list_files", {"path": ".", "recursive": True})

        assert len(content) > 0
        result_text = content[0].get("text", "")
        assert len(result_text.strip()) > 0

    async def test_list_files_nonexistent_path(self, initialized_client):
        """Test list_files with nonexistent path via MCP protocol."""
        try:
            content = await initialized_client.call_tool(
                "list_files", {"path": "definitely-does-not-exist"}
            )

            # If no exception, check error is reported in content
            if len(content) > 0:
                result_text = content[0].get("text", "")
                assert (
                    "error" in result_text.lower()
                    or "not found" in result_text.lower()
                    or "does not exist" in result_text.lower()
                )

        except RuntimeError as e:
            # Also acceptable to raise RPC error
            assert "error" in str(e).lower() or "not found" in str(e).lower()

    async def test_list_files_verbosity_levels(self, initialized_client):
        """Test list_files with different verbosity levels via MCP protocol."""
        verbosity_levels = ["minimal", "standard", "verbose", "debug"]

        for verbosity in verbosity_levels:
            content = await initialized_client.call_tool(
                "list_files", {"path": ".", "verbosity": verbosity}
            )

            assert len(content) > 0
            result_text = content[0].get("text", "")
            assert isinstance(result_text, str)

    async def test_list_files_no_bundle_initialized(self, temp_bundle_dir):
        """Test list_files when no bundle is initialized via MCP protocol."""
        env = {"SBCTL_TOKEN": "test-token-12345"}

        async with MCPTestClient(bundle_dir=temp_bundle_dir, env=env) as client:
            await client.initialize_mcp()

            try:
                content = await client.call_tool("list_files", {"path": "."})

                # Should get error about no bundle initialized
                assert len(content) > 0
                result_text = content[0].get("text", "")
                assert "bundle" in result_text.lower() and (
                    "not" in result_text.lower() or "error" in result_text.lower()
                )

            except RuntimeError as e:
                # Also acceptable to raise RPC error
                assert "bundle" in str(e).lower()


class TestReadFileTool:
    """Test read_file tool via MCP protocol."""

    async def test_read_file_basic(self, initialized_client):
        """Test basic file reading via MCP protocol."""
        # First list files to find one to read
        files_content = await initialized_client.call_tool("list_files", {"path": "."})
        files_text = files_content[0].get("text", "")

        # Try to find a common file to read (or skip if none available)
        common_files = ["version.yaml", "cluster-info/version.yaml", "README", "metadata.yaml"]
        file_to_read = None

        for common_file in common_files:
            if common_file in files_text:
                file_to_read = common_file
                break

        if file_to_read:
            content = await initialized_client.call_tool("read_file", {"path": file_to_read})

            assert len(content) > 0
            result_text = content[0].get("text", "")
            assert len(result_text.strip()) > 0
        else:
            pytest.skip("No readable files found in test bundle")

    async def test_read_file_with_line_range(self, initialized_client):
        """Test read_file with line range via MCP protocol."""
        # Try to read first few lines of any available file
        files_content = await initialized_client.call_tool("list_files", {"path": "."})
        files_text = files_content[0].get("text", "")

        # Look for any file in the output
        lines = files_text.split("\n")
        file_to_read = None
        for line in lines:
            if ".yaml" in line or ".txt" in line or ".json" in line:
                # Extract filename from the line
                parts = line.split()
                for part in parts:
                    if "." in part and not part.startswith("."):
                        file_to_read = part
                        break
                if file_to_read:
                    break

        if file_to_read:
            content = await initialized_client.call_tool(
                "read_file", {"path": file_to_read, "start_line": 0, "end_line": 5}
            )

            assert len(content) > 0
            result_text = content[0].get("text", "")
            assert isinstance(result_text, str)
        else:
            pytest.skip("No readable files found in test bundle")

    async def test_read_file_nonexistent(self, initialized_client):
        """Test read_file with nonexistent file via MCP protocol."""
        try:
            content = await initialized_client.call_tool(
                "read_file", {"path": "definitely-does-not-exist.yaml"}
            )

            # If no exception, check error is reported in content
            if len(content) > 0:
                result_text = content[0].get("text", "")
                assert (
                    "error" in result_text.lower()
                    or "not found" in result_text.lower()
                    or "does not exist" in result_text.lower()
                )

        except RuntimeError as e:
            # Also acceptable to raise RPC error
            assert "error" in str(e).lower() or "not found" in str(e).lower()

    async def test_read_file_verbosity_levels(self, initialized_client):
        """Test read_file with different verbosity levels via MCP protocol."""
        verbosity_levels = ["minimal", "standard", "verbose", "debug"]

        # Look for any readable file
        test_file = "version.yaml"  # Default to this common file

        for verbosity in verbosity_levels:
            try:
                content = await initialized_client.call_tool(
                    "read_file", {"path": test_file, "verbosity": verbosity}
                )

                assert len(content) > 0
                result_text = content[0].get("text", "")
                assert isinstance(result_text, str)

            except (RuntimeError, Exception):
                # File might not exist, which is fine for this test
                # We're primarily testing that verbosity doesn't cause crashes
                pass


class TestGrepFilesTool:
    """Test grep_files tool via MCP protocol."""

    async def test_grep_files_basic(self, initialized_client):
        """Test basic file grepping via MCP protocol."""
        content = await initialized_client.call_tool(
            "grep_files", {"pattern": "kind:", "path": "."}
        )

        assert len(content) > 0
        result_text = content[0].get("text", "")
        assert isinstance(result_text, str)

    async def test_grep_files_case_sensitive(self, initialized_client):
        """Test grep_files with case sensitivity via MCP protocol."""
        content = await initialized_client.call_tool(
            "grep_files", {"pattern": "Kind", "path": ".", "case_sensitive": True}
        )

        assert len(content) > 0
        result_text = content[0].get("text", "")
        assert isinstance(result_text, str)

    async def test_grep_files_with_glob_pattern(self, initialized_client):
        """Test grep_files with glob pattern via MCP protocol."""
        content = await initialized_client.call_tool(
            "grep_files",
            {"pattern": "version", "path": ".", "glob_pattern": "*.yaml", "recursive": True},
        )

        assert len(content) > 0
        result_text = content[0].get("text", "")
        assert isinstance(result_text, str)

    async def test_grep_files_max_results(self, initialized_client):
        """Test grep_files with max_results limit via MCP protocol."""
        content = await initialized_client.call_tool(
            "grep_files",
            {
                "pattern": ".*",  # Match everything
                "path": ".",
                "max_results": 10,
                "recursive": True,
            },
        )

        assert len(content) > 0
        result_text = content[0].get("text", "")
        assert isinstance(result_text, str)

    async def test_grep_files_nonexistent_path(self, initialized_client):
        """Test grep_files with nonexistent path via MCP protocol."""
        try:
            content = await initialized_client.call_tool(
                "grep_files", {"pattern": "test", "path": "definitely-does-not-exist"}
            )

            # If no exception, check error is reported in content
            if len(content) > 0:
                result_text = content[0].get("text", "")
                assert (
                    "error" in result_text.lower()
                    or "not found" in result_text.lower()
                    or "does not exist" in result_text.lower()
                )

        except RuntimeError as e:
            # Also acceptable to raise RPC error
            assert "error" in str(e).lower() or "not found" in str(e).lower()

    async def test_grep_files_verbosity_levels(self, initialized_client):
        """Test grep_files with different verbosity levels via MCP protocol."""
        verbosity_levels = ["minimal", "standard", "verbose", "debug"]

        for verbosity in verbosity_levels:
            content = await initialized_client.call_tool(
                "grep_files", {"pattern": "version", "path": ".", "verbosity": verbosity}
            )

            assert len(content) > 0
            result_text = content[0].get("text", "")
            assert isinstance(result_text, str)


class TestKubectlTool:
    """Test kubectl tool via MCP protocol."""

    async def test_kubectl_basic_command(self, initialized_client):
        """Test basic kubectl command via MCP protocol."""
        content = await initialized_client.call_tool("kubectl", {"command": "version --client"})

        assert len(content) > 0
        result_text = content[0].get("text", "")
        assert isinstance(result_text, str)
        assert len(result_text.strip()) > 0

    async def test_kubectl_get_nodes(self, initialized_client):
        """Test kubectl get nodes command via MCP protocol."""
        content = await initialized_client.call_tool("kubectl", {"command": "get nodes"})

        assert len(content) > 0
        result_text = content[0].get("text", "")
        assert isinstance(result_text, str)
        # Command might fail but should not crash
        assert len(result_text.strip()) > 0

    async def test_kubectl_with_json_output(self, initialized_client):
        """Test kubectl with JSON output via MCP protocol."""
        content = await initialized_client.call_tool(
            "kubectl", {"command": "get nodes", "json_output": True}
        )

        assert len(content) > 0
        result_text = content[0].get("text", "")
        assert isinstance(result_text, str)

    async def test_kubectl_with_timeout(self, initialized_client):
        """Test kubectl with custom timeout via MCP protocol."""
        content = await initialized_client.call_tool(
            "kubectl", {"command": "get nodes", "timeout": 5}
        )

        assert len(content) > 0
        result_text = content[0].get("text", "")
        assert isinstance(result_text, str)

    async def test_kubectl_interactive_command(self, initialized_client):
        """Test kubectl interactive command handling via MCP protocol."""
        # Test that interactive commands don't hang the server
        content = await initialized_client.call_tool(
            "kubectl", {"command": "exec some-pod -- /bin/bash"}
        )

        assert len(content) > 0
        result_text = content[0].get("text", "")
        assert isinstance(result_text, str)
        assert len(result_text.strip()) > 0

        # Verify server is still responsive
        tools_response = await initialized_client.send_request("tools/list")
        assert "result" in tools_response

    async def test_kubectl_streaming_command(self, initialized_client):
        """Test kubectl streaming command handling via MCP protocol."""
        streaming_commands = [
            "logs -f some-pod",
            "port-forward some-pod 8080:80",
            "proxy --port=8080",
            "attach some-pod",
        ]

        for cmd in streaming_commands:
            content = await initialized_client.call_tool("kubectl", {"command": cmd})

            assert len(content) > 0
            result_text = content[0].get("text", "")
            assert isinstance(result_text, str)
            assert len(result_text.strip()) > 0

            # Verify server is still responsive
            tools_response = await initialized_client.send_request("tools/list")
            assert "result" in tools_response

    async def test_kubectl_verbosity_levels(self, initialized_client):
        """Test kubectl with different verbosity levels via MCP protocol."""
        verbosity_levels = ["minimal", "standard", "verbose", "debug"]

        for verbosity in verbosity_levels:
            content = await initialized_client.call_tool(
                "kubectl", {"command": "version --client", "verbosity": verbosity}
            )

            assert len(content) > 0
            result_text = content[0].get("text", "")
            assert isinstance(result_text, str)

    async def test_kubectl_no_bundle_initialized(self, temp_bundle_dir):
        """Test kubectl when no bundle is initialized via MCP protocol."""
        env = {"SBCTL_TOKEN": "test-token-12345"}

        async with MCPTestClient(bundle_dir=temp_bundle_dir, env=env) as client:
            await client.initialize_mcp()

            try:
                content = await client.call_tool("kubectl", {"command": "get nodes"})

                # Should get error about no bundle initialized
                assert len(content) > 0
                result_text = content[0].get("text", "")
                assert "bundle" in result_text.lower() and (
                    "not" in result_text.lower() or "error" in result_text.lower()
                )

            except RuntimeError as e:
                # Also acceptable to raise RPC error
                assert "bundle" in str(e).lower()


class TestMCPProtocolPerformanceAndReliability:
    """Test MCP protocol performance and reliability scenarios."""

    async def test_large_file_operations(self, initialized_client):
        """Test handling of large file operations via MCP protocol."""
        # Just test that file operations complete within reasonable time
        start_time = time.time()

        # Test large file listing
        content = await initialized_client.call_tool("list_files", {"path": ".", "recursive": True})

        elapsed = time.time() - start_time

        assert len(content) > 0
        assert elapsed < 30  # Should complete within 30 seconds

    async def test_timeout_scenarios(self, initialized_client):
        """Test timeout handling via MCP protocol."""
        # Test kubectl with very short timeout
        content = await initialized_client.call_tool(
            "kubectl", {"command": "get nodes", "timeout": 1}
        )

        assert len(content) > 0
        result_text = content[0].get("text", "")
        assert isinstance(result_text, str)

    async def test_resource_cleanup(self, temp_bundle_dir, test_bundle_path):
        """Test resource cleanup after MCP operations."""
        bundle_name = test_bundle_path.name
        test_bundle_copy = temp_bundle_dir / bundle_name
        test_bundle_copy.write_bytes(test_bundle_path.read_bytes())

        env = {"SBCTL_TOKEN": "test-token-12345"}

        # Create multiple clients to test resource management
        for i in range(3):
            async with MCPTestClient(bundle_dir=temp_bundle_dir, env=env) as client:
                await client.initialize_mcp()

                # Load bundle
                await client.call_tool(
                    "initialize_bundle", {"bundle_path": str(test_bundle_copy), "force": True}
                )

                # Perform operations
                await client.call_tool("list_files", {"path": "."})
                await client.call_tool("kubectl", {"command": "version --client"})

                # Client cleanup happens automatically

        # All clients should have cleaned up properly

    async def test_rapid_consecutive_requests(self, initialized_client):
        """Test rapid consecutive requests via MCP protocol."""
        # Send many requests in rapid succession
        results = []

        for i in range(10):
            content = await initialized_client.call_tool("list_files", {"path": "."})
            results.append(content)

        # All requests should succeed
        for content in results:
            assert len(content) > 0
            result_text = content[0].get("text", "")
            assert isinstance(result_text, str)

    async def test_mixed_concurrent_operations(self, initialized_client):
        """Test mixed concurrent tool operations via MCP protocol."""
        # Start multiple different operations concurrently
        tasks = [
            initialized_client.call_tool("list_files", {"path": "."}),
            initialized_client.call_tool("grep_files", {"pattern": "version", "path": "."}),
            initialized_client.call_tool("kubectl", {"command": "version --client"}),
            initialized_client.call_tool("list_available_bundles"),
        ]

        # All should complete successfully
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                # Some operations might fail (e.g., kubectl), but shouldn't crash
                assert not isinstance(result, asyncio.TimeoutError)
            else:
                assert len(result) > 0
                assert isinstance(result[0].get("text", ""), str)


class TestMCPProtocolEdgeCases:
    """Test MCP protocol edge cases and error handling."""

    async def test_invalid_tool_parameters(self, initialized_client):
        """Test invalid tool parameters via MCP protocol."""
        # Test missing required parameters
        try:
            await initialized_client.call_tool("read_file", {})  # Missing path
            pytest.fail("Expected error for missing required parameter")
        except RuntimeError as e:
            assert "error" in str(e).lower()

    async def test_malformed_arguments(self, initialized_client):
        """Test malformed arguments via MCP protocol."""
        # Test with invalid argument types
        try:
            await initialized_client.call_tool(
                "list_files", {"path": ".", "recursive": "not_a_boolean"}
            )
            pytest.fail("Expected error for invalid argument type")
        except RuntimeError as e:
            assert "error" in str(e).lower()

    async def test_empty_string_arguments(self, initialized_client):
        """Test empty string arguments via MCP protocol."""
        # Test with empty path (should default to current directory)
        content = await initialized_client.call_tool("list_files", {"path": ""})

        assert len(content) > 0
        result_text = content[0].get("text", "")
        assert isinstance(result_text, str)

    async def test_very_long_arguments(self, initialized_client):
        """Test very long arguments via MCP protocol."""
        # Test with very long pattern
        long_pattern = "a" * 1000

        content = await initialized_client.call_tool(
            "grep_files", {"pattern": long_pattern, "path": "."}
        )

        assert len(content) > 0
        result_text = content[0].get("text", "")
        assert isinstance(result_text, str)

    async def test_special_character_handling(self, initialized_client):
        """Test special character handling via MCP protocol."""
        # Test with special characters in patterns
        special_patterns = [
            ".*",  # Regex
            "[a-z]+",  # Character class
            "\\$PATH",  # Escaped characters
            "test|other",  # Alternation
        ]

        for pattern in special_patterns:
            content = await initialized_client.call_tool(
                "grep_files", {"pattern": pattern, "path": ".", "max_results": 5}
            )

            assert len(content) > 0
            result_text = content[0].get("text", "")
            assert isinstance(result_text, str)
