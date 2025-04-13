# End-to-End Tests

This directory contains end-to-end tests that verify the full functionality of the MCP server, including the Docker container build and execution.

## Test Types

1. **Docker Build Tests** (`test_docker.py`): Test that the Docker image builds correctly and contains all required components.
2. **Container Basic Tests** (`test_container.py`): Test basic functionality of the container like running commands and verifying Python is installed.
3. **MCP Protocol Tests** (`test_mcp_protocol.py`): Test the MCP protocol communication directly with the Python module.
4. **Container MCP Tests** (`test_container_mcp.py`): Test MCP protocol communication with the containerized server.

## Setup

Before running the e2e tests, you need to prepare the environment:

```bash
# Run the preparation script
./scripts/prepare_tests.sh
```

This script will:
1. Build the test Docker image with a mock version of sbctl
2. Prepare test fixtures and support bundles 
3. Create environment variables for testing

## Running Tests

After preparation, you can run the tests:

```bash
# Source the environment variables
source tests/fixtures/env.sh

# Run all e2e tests
python -m pytest tests/e2e/

# Run a specific test file
python -m pytest tests/e2e/test_docker.py

# Run a specific test function
python -m pytest tests/e2e/test_container.py::test_basic_container_functionality -v
```

## Troubleshooting

If tests are hanging or failing, check the following:

1. **Docker availability**: Make sure Docker is running
2. **Mock sbctl**: Ensure `mock_sbctl.py` is executable and working correctly
3. **Test image**: Verify the test image was built with `docker images`
4. **Debug mode**: Set `MCP_CLIENT_DEBUG=true` to see detailed logs

## Test Timeouts

Some tests use timeouts to prevent hanging indefinitely. You can adjust these timeouts:

- `MCP_CLIENT_TIMEOUT`: Set the client timeout for MCP communication
- Use the `pytest.mark.timeout` decorator to set a test-specific timeout

If a test is timing out too quickly, you can increase these values for debugging.