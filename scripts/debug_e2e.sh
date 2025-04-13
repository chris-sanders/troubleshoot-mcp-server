#!/bin/bash

# Set debug variables
export MCP_CLIENT_DEBUG=true
export USE_MOCK_SBCTL=true
export MCP_LOG_LEVEL=DEBUG
export MCP_CLIENT_TIMEOUT=10.0

# Make mock_sbctl.py executable
chmod +x "$(pwd)/tests/fixtures/mock_sbctl.py"

# Add fixtures to PATH
export PATH="$(pwd)/tests/fixtures:$PATH"

# Run pytest with more verbose output
python -m pytest tests/e2e/test_container_mcp.py::test_tool_discovery -v