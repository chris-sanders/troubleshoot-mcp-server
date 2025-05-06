"""
Integration tests for the MCP server.
"""

import pytest

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_placeholder():
    """
    Placeholder test to ensure the file exists.

    This file was previously a symlink to a non-existent file,
    causing ruff to fail with an error. This placeholder ensures
    the file exists and passes linting checks.
    """
    assert True, "Placeholder test"
