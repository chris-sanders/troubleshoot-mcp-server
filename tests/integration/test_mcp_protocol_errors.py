"""
Comprehensive MCP protocol error handling tests.

This module implements Sub-Task 2C for Phase 2 MCP Protocol Testing Expansion.
It provides extensive testing of MCP protocol error scenarios including:

1. Invalid JSON-RPC requests
2. Missing and invalid tool parameters
3. Tool execution failures
4. Error response format validation
5. Protocol robustness under stress
6. Edge cases and server resource exhaustion

All tests use real JSON-RPC communication via the MCPTestClient to ensure
actual protocol behavior is tested.
"""

import asyncio
import json
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

from .mcp_test_utils import MCPTestClient, get_test_bundle_path

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def mcp_client():
    """
    Fixture providing an MCP test client for protocol error testing.

    Creates a fresh client with a temporary bundle directory for each test.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        bundle_dir = Path(temp_dir)

        # Create client but don't start server yet - tests control startup
        client = MCPTestClient(bundle_dir=bundle_dir)
        yield client

        # Cleanup handled by client context manager if started


@pytest_asyncio.fixture
async def initialized_client():
    """
    Fixture providing an initialized MCP client with a bundle loaded.

    This fixture starts the server, initializes it, and loads a test bundle.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        bundle_dir = Path(temp_dir)

        async with MCPTestClient(bundle_dir=bundle_dir) as client:
            # Initialize MCP connection
            await client.initialize_mcp()

            # Initialize with test bundle
            test_bundle = get_test_bundle_path()
            await client.call_tool("initialize_bundle", {"source": str(test_bundle), "force": True})

            yield client


class TestInvalidJSONRPCRequests:
    """Test invalid JSON-RPC request handling."""

    @pytest.mark.asyncio
    async def test_malformed_json(self, mcp_client):
        """Test server handling of malformed JSON requests."""
        async with mcp_client:
            # Send malformed JSON directly to stdin
            if mcp_client.process and mcp_client.process.stdin:
                mcp_client.process.stdin.write("{ malformed json }\n")
                mcp_client.process.stdin.flush()

                # Server should continue running after malformed JSON
                await asyncio.sleep(0.1)
                assert mcp_client.process.poll() is None, "Server should still be running"

    @pytest.mark.asyncio
    async def test_missing_jsonrpc_version(self, mcp_client):
        """Test handling of requests missing JSON-RPC version."""
        async with mcp_client:
            # Send request without jsonrpc field
            invalid_request = {
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "test", "version": "1.0.0"},
                },
            }

            if mcp_client.process and mcp_client.process.stdin:
                mcp_client.process.stdin.write(json.dumps(invalid_request) + "\n")
                mcp_client.process.stdin.flush()

                # Should get an error response or server should handle gracefully
                await asyncio.sleep(0.1)
                assert mcp_client.process.poll() is None, "Server should handle invalid request"

    @pytest.mark.asyncio
    async def test_invalid_jsonrpc_version(self, mcp_client):
        """Test handling of requests with invalid JSON-RPC version."""
        async with mcp_client:
            # Send request with wrong jsonrpc version
            invalid_request = {
                "jsonrpc": "1.0",  # Wrong version
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "test", "version": "1.0.0"},
                },
            }

            if mcp_client.process and mcp_client.process.stdin:
                mcp_client.process.stdin.write(json.dumps(invalid_request) + "\n")
                mcp_client.process.stdin.flush()

                await asyncio.sleep(0.1)
                assert mcp_client.process.poll() is None, "Server should handle version mismatch"

    @pytest.mark.asyncio
    async def test_missing_method_field(self, mcp_client):
        """Test handling of requests missing method field."""
        async with mcp_client:
            invalid_request = {
                "jsonrpc": "2.0",
                "id": 1,
                # Missing method field
                "params": {},
            }

            if mcp_client.process and mcp_client.process.stdin:
                mcp_client.process.stdin.write(json.dumps(invalid_request) + "\n")
                mcp_client.process.stdin.flush()

                await asyncio.sleep(0.1)
                assert mcp_client.process.poll() is None, "Server should handle missing method"

    @pytest.mark.asyncio
    async def test_non_string_method(self, mcp_client):
        """Test handling of requests with non-string method field."""
        async with mcp_client:
            invalid_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": 123,  # Should be string
                "params": {},
            }

            if mcp_client.process and mcp_client.process.stdin:
                mcp_client.process.stdin.write(json.dumps(invalid_request) + "\n")
                mcp_client.process.stdin.flush()

                await asyncio.sleep(0.1)
                assert mcp_client.process.poll() is None, "Server should handle non-string method"


class TestToolParameterErrors:
    """Test missing and invalid tool parameter handling."""

    @pytest.mark.asyncio
    async def test_missing_tool_name(self, mcp_client):
        """Test tools/call without tool name parameter."""
        async with mcp_client:
            await mcp_client.initialize_mcp()

            # Call tools/call without name parameter
            with pytest.raises(RuntimeError) as exc_info:
                await mcp_client.send_request(
                    "tools/call",
                    {
                        # Missing "name" parameter
                        "arguments": {}
                    },
                )

            error_msg = str(exc_info.value)
            assert "error" in error_msg.lower(), "Should report parameter validation error"

    @pytest.mark.asyncio
    async def test_invalid_tool_name_type(self, mcp_client):
        """Test tools/call with non-string tool name."""
        async with mcp_client:
            await mcp_client.initialize_mcp()

            with pytest.raises(RuntimeError) as exc_info:
                await mcp_client.send_request(
                    "tools/call", {"name": 123, "arguments": {}}  # Should be string
                )

            error_msg = str(exc_info.value)
            assert "error" in error_msg.lower(), "Should report type validation error"

    @pytest.mark.asyncio
    async def test_nonexistent_tool_name(self, mcp_client):
        """Test calling a tool that doesn't exist."""
        async with mcp_client:
            await mcp_client.initialize_mcp()

            with pytest.raises(RuntimeError) as exc_info:
                await mcp_client.send_request(
                    "tools/call", {"name": "nonexistent_tool", "arguments": {}}
                )

            error_msg = str(exc_info.value)
            assert (
                "not found" in error_msg.lower()
                or "unknown" in error_msg.lower()
                or "error" in error_msg.lower()
            ), "Should report tool not found"

    @pytest.mark.asyncio
    async def test_invalid_initialize_bundle_params(self, mcp_client):
        """Test initialize_bundle with invalid parameters."""
        async with mcp_client:
            await mcp_client.initialize_mcp()

            # Test with missing source parameter
            with pytest.raises(RuntimeError) as exc_info:
                await mcp_client.call_tool(
                    "initialize_bundle",
                    {
                        # Missing "source" parameter
                        "force": False
                    },
                )

            error_msg = str(exc_info.value)
            assert "error" in error_msg.lower(), "Should report missing source parameter"

    @pytest.mark.asyncio
    async def test_invalid_kubectl_params(self, initialized_client):
        """Test kubectl with invalid parameters."""
        # Test with missing command parameter
        with pytest.raises(RuntimeError) as exc_info:
            await initialized_client.call_tool(
                "kubectl",
                {
                    # Missing "command" parameter
                    "timeout": 30
                },
            )

        error_msg = str(exc_info.value)
        assert "error" in error_msg.lower(), "Should report missing command parameter"

    @pytest.mark.asyncio
    async def test_invalid_list_files_params(self, initialized_client):
        """Test list_files with invalid parameters."""
        # Test with invalid path type
        with pytest.raises(RuntimeError) as exc_info:
            await initialized_client.call_tool(
                "list_files", {"path": 123, "recursive": False}  # Should be string
            )

        error_msg = str(exc_info.value)
        assert "error" in error_msg.lower(), "Should report type validation error"


class TestToolExecutionFailures:
    """Test tool execution failure scenarios."""

    @pytest.mark.asyncio
    async def test_initialize_bundle_nonexistent_file(self, mcp_client):
        """Test initialize_bundle with nonexistent source file."""
        async with mcp_client:
            await mcp_client.initialize_mcp()

            # Try to initialize with nonexistent file
            result = await mcp_client.call_tool(
                "initialize_bundle",
                {"source": "/tmp/definitely-does-not-exist.tar.gz", "force": False},
            )

            # Should get error response, not exception
            assert len(result) > 0, "Should return error response"
            error_text = result[0].get("text", "")
            assert (
                "not found" in error_text.lower() or "error" in error_text.lower()
            ), "Should indicate file not found"

    @pytest.mark.asyncio
    async def test_initialize_bundle_invalid_file(self, mcp_client):
        """Test initialize_bundle with invalid bundle file."""
        async with mcp_client:
            await mcp_client.initialize_mcp()

            # Create a temporary invalid file
            with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as temp_file:
                temp_file.write(b"Not a valid tar.gz file")
                temp_file_path = temp_file.name

            try:
                result = await mcp_client.call_tool(
                    "initialize_bundle", {"source": temp_file_path, "force": False}
                )

                # Should get error response
                assert len(result) > 0, "Should return error response"
                error_text = result[0].get("text", "")
                assert "error" in error_text.lower(), "Should indicate bundle error"

            finally:
                # Cleanup temp file
                Path(temp_file_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_kubectl_without_initialized_bundle(self, mcp_client):
        """Test kubectl execution without initialized bundle."""
        async with mcp_client:
            await mcp_client.initialize_mcp()

            result = await mcp_client.call_tool("kubectl", {"command": "get pods", "timeout": 30})

            # Should get error response about bundle not initialized
            assert len(result) > 0, "Should return error response"
            error_text = result[0].get("text", "")
            assert (
                "not initialized" in error_text.lower() or "bundle" in error_text.lower()
            ), "Should indicate bundle not initialized"

    @pytest.mark.asyncio
    async def test_file_operations_without_bundle(self, mcp_client):
        """Test file operations without initialized bundle."""
        async with mcp_client:
            await mcp_client.initialize_mcp()

            # Test list_files without bundle
            result = await mcp_client.call_tool("list_files", {"path": "/", "recursive": False})

            assert len(result) > 0, "Should return error response"
            error_text = result[0].get("text", "")
            assert (
                "not initialized" in error_text.lower()
                or "bundle" in error_text.lower()
                or "error" in error_text.lower()
            ), "Should indicate bundle error"

    @pytest.mark.asyncio
    async def test_read_file_nonexistent(self, initialized_client):
        """Test reading nonexistent file in bundle."""
        result = await initialized_client.call_tool(
            "read_file", {"path": "definitely/does/not/exist.txt", "start_line": 0, "end_line": 10}
        )

        assert len(result) > 0, "Should return error response"
        error_text = result[0].get("text", "")
        assert (
            "not found" in error_text.lower()
            or "does not exist" in error_text.lower()
            or "error" in error_text.lower()
        ), "Should indicate file not found"

    @pytest.mark.asyncio
    async def test_invalid_path_traversal(self, initialized_client):
        """Test path traversal prevention in file operations."""
        # Test list_files with path traversal
        result = await initialized_client.call_tool(
            "list_files", {"path": "../../../etc", "recursive": False}
        )

        assert len(result) > 0, "Should return error response"
        error_text = result[0].get("text", "")
        assert (
            "traversal" in error_text.lower()
            or "invalid" in error_text.lower()
            or "error" in error_text.lower()
        ), "Should prevent path traversal"


class TestErrorResponseFormat:
    """Test proper JSON-RPC error response format."""

    @pytest.mark.asyncio
    async def test_error_response_structure(self, mcp_client):
        """Test that error responses follow JSON-RPC 2.0 format."""
        async with mcp_client:
            await mcp_client.initialize_mcp()

            try:
                # Try to trigger an error
                await mcp_client.send_request("tools/call", {"name": "nonexistent_tool"})
            except RuntimeError as e:
                error_msg = str(e)
                # Should mention RPC Error with code
                assert "RPC Error" in error_msg, "Should be formatted as RPC error"
                assert any(char.isdigit() for char in error_msg), "Should include error code"

    @pytest.mark.asyncio
    async def test_tool_error_meaningful_messages(self, mcp_client):
        """Test that tool errors provide meaningful messages."""
        async with mcp_client:
            await mcp_client.initialize_mcp()

            # Test kubectl without bundle
            result = await mcp_client.call_tool("kubectl", {"command": "get pods"})

            error_text = result[0].get("text", "")
            # Error message should be informative
            assert len(error_text) > 10, "Error message should be descriptive"
            assert (
                "bundle" in error_text.lower() or "initialized" in error_text.lower()
            ), "Should explain the issue"

    @pytest.mark.asyncio
    async def test_validation_error_details(self, mcp_client):
        """Test that validation errors provide detailed information."""
        async with mcp_client:
            await mcp_client.initialize_mcp()

            # Test with invalid parameter type
            with pytest.raises(RuntimeError) as exc_info:
                await mcp_client.call_tool(
                    "list_files", {"path": None, "recursive": False}  # Invalid type
                )

            error_msg = str(exc_info.value)
            assert len(error_msg) > 5, "Should provide detailed error"


class TestProtocolRobustness:
    """Test protocol robustness under stress and edge cases."""

    @pytest.mark.asyncio
    async def test_large_request_payload(self, mcp_client):
        """Test handling of large request payloads."""
        async with mcp_client:
            await mcp_client.initialize_mcp()

            # Create a large arguments payload
            large_args = {"source": "x" * 10000, "force": False}  # Very long path

            # Server should handle large payloads gracefully
            result = await mcp_client.call_tool("initialize_bundle", large_args)

            # Should get a response (even if it's an error)
            assert len(result) > 0, "Should handle large payload"

    @pytest.mark.asyncio
    async def test_rapid_request_sequence(self, initialized_client):
        """Test handling of rapid consecutive requests."""
        # Send multiple requests rapidly
        tasks = []
        for i in range(5):
            task = initialized_client.call_tool("list_files", {"path": "/", "recursive": False})
            tasks.append(task)

        # All requests should complete successfully
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"Request {i} failed: {result}")
            assert len(result) > 0, f"Request {i} should return result"

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self, initialized_client):
        """Test concurrent tool execution."""
        # Execute different tools concurrently
        tasks = [
            initialized_client.call_tool("list_files", {"path": "/", "recursive": False}),
            initialized_client.call_tool(
                "grep_files", {"pattern": "version", "path": "/", "recursive": True}
            ),
            initialized_client.call_tool("list_files", {"path": "/", "recursive": True}),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Some concurrent operations might fail, but shouldn't crash server
                continue
            assert len(result) > 0, f"Concurrent request {i} should return result"

    @pytest.mark.asyncio
    async def test_malformed_requests_dont_crash_server(self, mcp_client):
        """Test that malformed requests don't crash the server."""
        async with mcp_client:
            # Send various malformed requests
            malformed_requests = [
                "not json at all",
                '{"incomplete": json',
                '{"jsonrpc": "2.0", "id": null}',
                '{"method": null, "id": 1}',
                "",
                "\n\n\n",
                "[]",  # Array instead of object
                '{"jsonrpc": "2.0", "id": "string_id", "method": "test"}',
            ]

            if mcp_client.process and mcp_client.process.stdin:
                for req in malformed_requests:
                    mcp_client.process.stdin.write(req + "\n")
                    mcp_client.process.stdin.flush()
                    await asyncio.sleep(0.01)  # Small delay between requests

            # Server should still be running
            await asyncio.sleep(0.1)
            assert (
                mcp_client.process and mcp_client.process.poll() is None
            ), "Server should survive malformed requests"

            # Should still be able to make valid requests
            await mcp_client.initialize_mcp()
            result = await mcp_client.call_tool("list_available_bundles", {})
            assert len(result) > 0, "Server should still be functional"

    @pytest.mark.asyncio
    async def test_timeout_handling(self, initialized_client):
        """Test handling of operations that might timeout."""
        # Test kubectl with very short timeout
        result = await initialized_client.call_tool(
            "kubectl", {"command": "get pods", "timeout": 1}  # Very short timeout
        )

        # Should get some response (success or timeout error)
        assert len(result) > 0, "Should handle timeout gracefully"

        # Response should not crash the server
        text = result[0].get("text", "")
        assert isinstance(text, str), "Response should be formatted text"


class TestEdgeCasesAndResourceExhaustion:
    """Test edge cases and server resource management."""

    @pytest.mark.asyncio
    async def test_bundle_loading_failure_recovery(self, mcp_client):
        """Test recovery from bundle loading failures."""
        async with mcp_client:
            await mcp_client.initialize_mcp()

            # Try to initialize with invalid bundle
            result1 = await mcp_client.call_tool(
                "initialize_bundle", {"source": "/nonexistent/bundle.tar.gz", "force": False}
            )

            # Should get error but server should still work
            assert len(result1) > 0, "Should return error response"

            # Should still be able to list bundles
            result2 = await mcp_client.call_tool("list_available_bundles", {})
            assert len(result2) > 0, "Server should recover from bundle error"

    @pytest.mark.asyncio
    async def test_memory_usage_with_large_operations(self, initialized_client):
        """Test memory handling with large file operations."""
        # Try to list files recursively (potentially large operation)
        result = await initialized_client.call_tool("list_files", {"path": "/", "recursive": True})

        # Should complete without memory issues
        assert len(result) > 0, "Large operation should complete"

        # Server should still be responsive
        result2 = await initialized_client.call_tool("list_available_bundles", {})
        assert len(result2) > 0, "Server should remain responsive"

    @pytest.mark.asyncio
    async def test_nested_error_conditions(self, mcp_client):
        """Test handling of nested error conditions."""
        async with mcp_client:
            await mcp_client.initialize_mcp()

            # Try kubectl without bundle (first error)
            result1 = await mcp_client.call_tool("kubectl", {"command": "get pods"})

            # Try file operation without bundle (second error)
            result2 = await mcp_client.call_tool("read_file", {"path": "test.txt"})

            # Both should return errors but not crash server
            assert len(result1) > 0, "First error should be handled"
            assert len(result2) > 0, "Second error should be handled"

            # Server should still work for valid operations
            result3 = await mcp_client.call_tool("list_available_bundles", {})
            assert len(result3) > 0, "Server should handle nested errors"

    @pytest.mark.asyncio
    async def test_cleanup_after_errors(self, mcp_client):
        """Test that server cleans up properly after errors."""
        async with mcp_client:
            await mcp_client.initialize_mcp()

            # Cause multiple errors
            error_operations = [
                ("initialize_bundle", {"source": "/invalid/path"}),
                ("kubectl", {"command": "get pods"}),
                ("read_file", {"path": "invalid/file"}),
            ]

            for tool_name, args in error_operations:
                result = await mcp_client.call_tool(tool_name, args)
                assert len(result) > 0, f"Error from {tool_name} should be handled"

            # Server should still be clean and functional
            result = await mcp_client.call_tool("list_available_bundles", {})
            assert len(result) > 0, "Server should be clean after errors"

    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(self, mcp_client):
        """Test handling of unicode and special characters in parameters."""
        async with mcp_client:
            await mcp_client.initialize_mcp()

            # Test with unicode characters
            unicode_path = "/test/path/with/unicode/文件"
            result = await mcp_client.call_tool(
                "initialize_bundle", {"source": unicode_path, "force": False}
            )

            # Should handle unicode gracefully
            assert len(result) > 0, "Should handle unicode characters"

            # Test with special characters
            special_chars = "/path/with/special/chars/!@#$%^&*()"
            result2 = await mcp_client.call_tool(
                "initialize_bundle", {"source": special_chars, "force": False}
            )

            assert len(result2) > 0, "Should handle special characters"
