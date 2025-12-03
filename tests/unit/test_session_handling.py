"""
Unit tests for session handling functionality.

This module tests the session ID extraction and management functions used for
concurrent bundle support. These tests verify:

1. get_session_id() correctly extracts session IDs from various contexts
2. is_stdio_session() correctly identifies the stdio default session
3. Backward compatibility is maintained for stdio mode
"""

from unittest.mock import Mock, patch
import pytest

from troubleshoot_mcp_server.server import (
    get_session_id,
    is_stdio_session,
    STDIO_DEFAULT_SESSION,
)

# Mark all tests in this file as unit tests
pytestmark = [pytest.mark.unit, pytest.mark.quick]


class TestGetSessionId:
    """Tests for the get_session_id() function."""

    def test_returns_stdio_default_when_no_context(self):
        """When no MCP context exists, should return STDIO_DEFAULT_SESSION."""
        # Mock mcp.get_context() to return None
        with patch("troubleshoot_mcp_server.server.mcp") as mock_mcp:
            mock_mcp.get_context.return_value = None
            result = get_session_id()
            assert result == STDIO_DEFAULT_SESSION

    def test_returns_stdio_default_when_context_has_no_request(self):
        """When MCP context exists but has no request, should return STDIO_DEFAULT_SESSION."""
        with patch("troubleshoot_mcp_server.server.mcp") as mock_mcp:
            mock_ctx = Mock()
            mock_ctx.request_context = None
            mock_mcp.get_context.return_value = mock_ctx
            result = get_session_id()
            assert result == STDIO_DEFAULT_SESSION

    def test_returns_session_id_from_query_param(self):
        """When session_id is in query params, should return it."""
        with patch("troubleshoot_mcp_server.server.mcp") as mock_mcp:
            mock_request = Mock()
            mock_request.query_params = {"session_id": "test-session-123"}
            mock_request.headers = {}

            mock_request_context = Mock()
            mock_request_context.request = mock_request

            mock_ctx = Mock()
            mock_ctx.request_context = mock_request_context
            mock_mcp.get_context.return_value = mock_ctx

            result = get_session_id()
            assert result == "test-session-123"

    def test_returns_session_id_from_header(self):
        """When session_id is in header but not query params, should return header value."""
        with patch("troubleshoot_mcp_server.server.mcp") as mock_mcp:
            mock_request = Mock()
            mock_request.query_params = {}  # No query param
            mock_request.headers = {"x-mcp-session-id": "header-session-456"}

            mock_request_context = Mock()
            mock_request_context.request = mock_request

            mock_ctx = Mock()
            mock_ctx.request_context = mock_request_context
            mock_mcp.get_context.return_value = mock_ctx

            result = get_session_id()
            assert result == "header-session-456"

    def test_prefers_header_over_query_param(self):
        """When both query param and header exist, should prefer header (stable workflow_id)."""
        with patch("troubleshoot_mcp_server.server.mcp") as mock_mcp:
            mock_request = Mock()
            mock_request.query_params = {"session_id": "query-session"}
            mock_request.headers = {"x-mcp-session-id": "header-session"}

            mock_request_context = Mock()
            mock_request_context.request = mock_request

            mock_ctx = Mock()
            mock_ctx.request_context = mock_request_context
            mock_mcp.get_context.return_value = mock_ctx

            result = get_session_id()
            # Header is preferred because it provides a stable workflow_id
            # vs query param which may be random from SSE client
            assert result == "header-session"

    def test_returns_stdio_default_when_no_session_id_found(self):
        """When context exists but no session_id in params or headers, return stdio default."""
        with patch("troubleshoot_mcp_server.server.mcp") as mock_mcp:
            mock_request = Mock()
            mock_request.query_params = {}  # No session_id
            mock_request.headers = {}  # No x-mcp-session-id

            mock_request_context = Mock()
            mock_request_context.request = mock_request

            mock_ctx = Mock()
            mock_ctx.request_context = mock_request_context
            mock_mcp.get_context.return_value = mock_ctx

            result = get_session_id()
            assert result == STDIO_DEFAULT_SESSION

    def test_handles_exception_gracefully(self):
        """When get_context raises an exception, should return STDIO_DEFAULT_SESSION."""
        with patch("troubleshoot_mcp_server.server.mcp") as mock_mcp:
            mock_mcp.get_context.side_effect = Exception("Context error")
            result = get_session_id()
            assert result == STDIO_DEFAULT_SESSION

    def test_always_returns_string(self):
        """get_session_id should always return a string, never None."""
        # Test various error scenarios
        test_scenarios = [
            lambda: None,  # Returns None
            lambda: (_ for _ in ()).throw(RuntimeError("test")),  # Raises exception
        ]

        with patch("troubleshoot_mcp_server.server.mcp") as mock_mcp:
            for scenario in test_scenarios:
                mock_mcp.get_context.side_effect = scenario
                result = get_session_id()
                assert isinstance(result, str)
                assert result == STDIO_DEFAULT_SESSION


class TestIsStdioSession:
    """Tests for the is_stdio_session() function."""

    def test_returns_true_for_stdio_default_session(self):
        """Should return True when session_id equals STDIO_DEFAULT_SESSION."""
        assert is_stdio_session(STDIO_DEFAULT_SESSION) is True

    def test_returns_false_for_other_session_ids(self):
        """Should return False for any other session ID."""
        assert is_stdio_session("some-other-session") is False
        assert is_stdio_session("test-session-123") is False
        assert is_stdio_session("") is False
        assert is_stdio_session("stdio") is False  # Similar but not exact match

    def test_case_sensitive(self):
        """Session ID comparison should be case-sensitive."""
        # These should all be False since they don't match exactly
        assert is_stdio_session(STDIO_DEFAULT_SESSION.upper()) is False
        assert is_stdio_session(STDIO_DEFAULT_SESSION.title()) is False

    def test_whitespace_sensitive(self):
        """Session ID comparison should not ignore whitespace."""
        assert is_stdio_session(f" {STDIO_DEFAULT_SESSION}") is False
        assert is_stdio_session(f"{STDIO_DEFAULT_SESSION} ") is False
        assert is_stdio_session(f" {STDIO_DEFAULT_SESSION} ") is False


class TestStdioModeCompatibility:
    """Tests for backward compatibility with stdio mode."""

    def test_stdio_default_session_constant_value(self):
        """Verify the constant value hasn't changed (breaking change protection)."""
        # This constant is part of the API contract for backward compatibility
        assert STDIO_DEFAULT_SESSION == "stdio-default-session"

    def test_stdio_mode_always_gets_default_session(self):
        """In stdio mode (no HTTP context), should always get default session."""
        # Simulate stdio mode - no MCP context available
        with patch("troubleshoot_mcp_server.server.mcp") as mock_mcp:
            mock_mcp.get_context.return_value = None
            session_id = get_session_id()

            # Verify it's the stdio session
            assert is_stdio_session(session_id) is True
            assert session_id == STDIO_DEFAULT_SESSION

    def test_http_mode_can_differentiate_sessions(self):
        """In HTTP/SSE mode with session_id, should get unique session."""
        with patch("troubleshoot_mcp_server.server.mcp") as mock_mcp:
            mock_request = Mock()
            mock_request.query_params = {"session_id": "unique-http-session"}
            mock_request.headers = {}

            mock_request_context = Mock()
            mock_request_context.request = mock_request

            mock_ctx = Mock()
            mock_ctx.request_context = mock_request_context
            mock_mcp.get_context.return_value = mock_ctx

            session_id = get_session_id()

            # Verify it's NOT the stdio session
            assert is_stdio_session(session_id) is False
            assert session_id == "unique-http-session"

    def test_concurrent_sessions_have_unique_ids(self):
        """Different HTTP sessions should get different session IDs."""
        with patch("troubleshoot_mcp_server.server.mcp") as mock_mcp:
            session_ids = []

            # Simulate multiple different sessions
            for i in range(3):
                mock_request = Mock()
                mock_request.query_params = {"session_id": f"session-{i}"}
                mock_request.headers = {}

                mock_request_context = Mock()
                mock_request_context.request = mock_request

                mock_ctx = Mock()
                mock_ctx.request_context = mock_request_context
                mock_mcp.get_context.return_value = mock_ctx

                session_ids.append(get_session_id())

            # All session IDs should be unique
            assert len(set(session_ids)) == 3
            assert session_ids == ["session-0", "session-1", "session-2"]

            # None should be the stdio default
            for sid in session_ids:
                assert is_stdio_session(sid) is False
