# Test Utilities

This directory contains utility scripts for testing purposes.

## Available Utilities

- `debug_mcp.py`: A tool for debugging MCP server communication

## Usage

These utilities are primarily used by the test suite and can be imported by test files:

```python
from util.debug_mcp import debug_mcp_communication

# Example usage
debug_mcp_communication(process)
```

## Debug Utilities

The debug utilities help diagnose issues with MCP server communication, including:

- Checking MCP protocol messages
- Validating JSON-RPC responses
- Testing timeout and error handling

## Adding New Utilities

When adding new utilities:

1. Place them in this directory
2. Add appropriate documentation
3. Ensure they're properly imported by test files
4. Update this README with information about the new utility