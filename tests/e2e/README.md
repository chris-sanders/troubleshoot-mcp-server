# End-to-End Tests

This directory contains end-to-end tests that verify the full functionality of the MCP server, including the Podman container build and execution.

## Test Types

1. **Container Infrastructure Tests** (`test_podman.py`): Tests basic Podman functionality, container building, and verifies the container has all required components and tools.
2. **Container Application Tests** (`test_podman_container.py`): Tests the MCP server application running inside the container with features like bundle processing.
3. **Quick Checks** (`quick_check.py`): Fast tests with strict timeouts to verify basic functionality without running the full test suite.

## Setup

Before running the e2e tests, you need to prepare the environment:

```bash
# Install dependencies
uv pip install -e ".[dev]"

# Make sure Podman is installed
podman --version
```

The test suite supports both Docker and Podman, with Podman being the preferred container runtime.

## Running Tests

You can run the tests using the following commands:

```bash
# Run all e2e tests
uv run pytest -m e2e

# Run container-specific tests
uv run pytest -m container

# Run a specific test file
uv run pytest tests/e2e/test_podman_container.py

# Run a specific test function
uv run pytest tests/e2e/test_podman_container.py::test_bundle_processing -v
```

## Container Image Reuse

The test suite uses a session-scoped fixture that builds the container image once and reuses it across all tests. This significantly improves test performance by avoiding rebuilding the image for each test.

```python
@pytest.fixture(scope="session")
def docker_image():
    # This fixture builds the image once for all tests
    # ...
```

## Environment-Aware Testing

The tests are designed to work in different environments:

1. **Local Development**: Full tests with all features
2. **CI Environment**: Some tests may be skipped or modified depending on the CI capabilities

The tests automatically detect when they are running in CI environments like GitHub Actions and adjust accordingly.

## Troubleshooting

If tests are hanging or failing, check the following:

1. **Podman availability**: Make sure Podman is running
2. **Mock sbctl**: Ensure `mock_sbctl.py` is executable when needed
3. **Test image**: Verify the test image was built with `podman images`
4. **Debug mode**: Set `MCP_CLIENT_DEBUG=true` to see detailed logs

## Test Timeouts

Some tests use timeouts to prevent hanging indefinitely. You can adjust these timeouts:

- `MCP_CLIENT_TIMEOUT`: Set the client timeout for MCP communication
- Use the `pytest.mark.timeout` decorator to set a test-specific timeout

If a test is timing out too quickly, you can increase these values for debugging.