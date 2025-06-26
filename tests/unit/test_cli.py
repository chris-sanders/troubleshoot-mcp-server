import pytest
from unittest.mock import patch, MagicMock
from mcp_server_troubleshoot import __main__ as cli_main

# Mark all tests in this file as unit tests
pytestmark = pytest.mark.unit

@patch('mcp_server_troubleshoot.__main__.parse_args')
@patch('mcp_server_troubleshoot.__main__.handle_show_config')
def test_main_dispatch_show_config(mock_handle_show_config, mock_parse_args):
    """Test that main() calls handle_show_config when --show-config is used."""
    mock_args = MagicMock()
    mock_args.show_config = True
    mock_parse_args.return_value = mock_args

    cli_main.main()
    
    mock_handle_show_config.assert_called_once()

@patch('mcp_server_troubleshoot.__main__.parse_args')
@patch('mcp_server_troubleshoot.__main__.mcp.run')
@patch('mcp_server_troubleshoot.__main__.setup_logging')
@patch('mcp_server_troubleshoot.__main__.atexit.register')
@patch('mcp_server_troubleshoot.__main__.setup_signal_handlers')
def test_main_dispatch_mcp_run(mock_setup_signal_handlers, mock_atexit_register, mock_setup_logging, mock_mcp_run, mock_parse_args, tmp_path):
    """Test that main() calls mcp.run by default."""
    mock_args = MagicMock()
    mock_args.show_config = False
    mock_args.bundle_dir = str(tmp_path)
    mock_parse_args.return_value = mock_args

    cli_main.main()

    mock_mcp_run.assert_called_once()

@patch('mcp_server_troubleshoot.__main__.parse_args')
@patch('mcp_server_troubleshoot.__main__.mcp.run', side_effect=KeyboardInterrupt)
@patch('mcp_server_troubleshoot.__main__.shutdown')
@patch('sys.stderr')
@patch('sys.stdout')
def test_main_keyboard_interrupt(mock_stdout, mock_stderr, mock_shutdown, mock_mcp_run, mock_parse_args, tmp_path):
    """Test that main() calls shutdown on KeyboardInterrupt."""
    mock_args = MagicMock()
    mock_args.show_config = False
    mock_args.bundle_dir = str(tmp_path)
    mock_parse_args.return_value = mock_args

    cli_main.main()

    mock_shutdown.assert_called_once()
