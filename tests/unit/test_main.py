"""
Tests for the __main__ module.
"""

import pytest
from unittest.mock import patch
from mcp_server_troubleshoot import __main__ as cli_main

# Mark all tests in this file as unit tests
pytestmark = pytest.mark.unit


@patch("mcp_server_troubleshoot.__main__.logging")
def test_setup_logging(mock_logging):
    """Test that logging is configured correctly."""
    cli_main.setup_logging(verbose=True)
    mock_logging.basicConfig.assert_called_with(
        level=mock_logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=cli_main.sys.stderr,
    )

    cli_main.setup_logging(verbose=False)
    mock_logging.basicConfig.assert_called_with(
        level=mock_logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=cli_main.sys.stderr,
    )
