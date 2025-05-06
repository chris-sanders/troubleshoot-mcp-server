"""
Integration tests for the stdio lifecycle functionality.

NOTE: The tests previously in this file were designed to verify stdio lifecycle
functionality directly. However, with the new lifecycle architecture that uses
FastMCP's lifespan context manager, these direct subprocess tests are no longer
compatible with the server's architecture.

The functionality is now properly tested in the e2e container tests which provide
a more appropriate environment for testing the full lifecycle:

1. test_container.py: Tests basic functionality of the container
2. test_mcp_protocol.py: Tests MCP protocol communication
3. test_docker.py: Tests Docker container lifecycle including proper cleanup

These tests have been removed as they were:
- Incompatible with the new lifecycle architecture using lifespan contexts
- Redundant with container-based tests that properly test the same functionality
- Creating maintenance overhead by requiring skip markers

For reference, the original tests verified:
- Basic startup and shutdown in stdio mode
- Bundle operations with stdio server
- Signal handling for termination
- Temporary directory cleanup on shutdown
"""

import pytest


@pytest.mark.asyncio
async def test_stdio_lifecycle_docstring():
    """
    This test exists to document why the stdio lifecycle tests were removed.

    The stdio lifecycle functionality is now properly tested in the e2e container
    tests which provide a more appropriate environment.
    """
    # This is a documentation test only - it doesn't actually test functionality
    # It exists to preserve the test file for documentation purposes and to show
    # in test collection that the stdio lifecycle tests were intentionally removed
    assert True, "This test exists only for documentation purposes"
