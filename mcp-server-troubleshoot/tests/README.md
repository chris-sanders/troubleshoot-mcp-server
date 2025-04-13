# Tests Directory

This directory contains tests for the MCP server for Kubernetes support bundles.

## Test Structure

The tests are organized into the following directories:

- `unit/`: Unit tests for individual components (BundleManager, FileExplorer, KubectlExecutor, Server)
- `integration/`: Integration tests for multiple components working together, including real bundle tests
- `e2e/`: End-to-end tests for the full system, including container and Docker tests
- `fixtures/`: Test data and fixtures

## Running Tests

You can run tests using the provided script:

```bash
# Run all tests
./scripts/run_tests.sh

# Run specific test categories
./scripts/run_tests.sh unit
./scripts/run_tests.sh integration
./scripts/run_tests.sh e2e
```

Alternatively, you can run tests directly with pytest:

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run specific test files
pytest tests/unit/test_bundle.py

# Run with verbosity
pytest -v
```

## Test Categories

### Unit Tests

The unit tests test individual components in isolation:

- `test_bundle.py`: Tests for the BundleManager
- `test_files.py`: Tests for the FileExplorer
- `test_kubectl.py`: Tests for the KubectlExecutor
- `test_server.py`: Tests for the MCP server implementation

### Integration Tests

The integration tests test multiple components working together:

- `test_integration.py`: Tests the interaction between BundleManager, FileExplorer, and KubectlExecutor
- `test_real_bundle.py`: Tests using actual support bundles

### End-to-End Tests

The e2e tests test the full system:

- `test_container.py`: Tests the Docker container functionality
- `test_docker.py`: Tests Docker-specific functionality
- `test_mcp_protocol.py`: Tests the MCP protocol communication (planned implementation)

## Test Data

The test fixtures directory contains sample data for testing, including a small support bundle.

## Adding New Tests

When adding new tests:

1. Place them in the appropriate directory based on test scope:
   - Unit tests for individual components in `unit/`
   - Integration tests for component interactions in `integration/`
   - End-to-end tests in `e2e/`
2. Follow the naming convention of `test_*.py` for test files
3. Use pytest fixtures for test setup and teardown
4. Add documentation in docstrings for each test