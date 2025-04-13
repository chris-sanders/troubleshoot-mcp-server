# Tests for MCP Server Troubleshoot

This directory contains tests for the MCP server for Kubernetes support bundles.

## Test Structure

The tests are organized into the following directories:

- `unit/`: Unit tests for individual components (BundleManager, FileExplorer, KubectlExecutor, Server)
- `integration/`: Integration tests for multiple components working together, including real bundle tests
- `e2e/`: End-to-end tests for the full system, including container and Docker tests
- `fixtures/`: Test data and fixtures
- `util/`: Utility scripts for testing

## Running Tests

You can run tests using the provided scripts:

```bash
# Run all tests
./scripts/run_tests.sh

# Run end-to-end tests with different levels
./scripts/run_e2e_tests.sh --level=basic    # Run basic tests only
./scripts/run_e2e_tests.sh --level=docker   # Run Docker build tests
./scripts/run_e2e_tests.sh --level=container # Run container tests
./scripts/run_e2e_tests.sh --level=all      # Run all tests
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

# Run with timeouts to prevent hanging tests
pytest --timeout=30
```

## Test Categories

### Unit Tests

The unit tests test individual components in isolation:

- `test_bundle.py`: Tests for the BundleManager
- `test_files.py`: Tests for the FileExplorer
- `test_kubectl.py`: Tests for the KubectlExecutor
- `test_server.py`: Tests for the MCP server implementation
- `test_bundle_path_resolution.py`: Tests for bundle path resolution
- `test_components.py`: Tests for component interactions
- `test_grep_fix.py`: Tests for grep functionality

### Integration Tests

The integration tests test multiple components working together:

- `test_integration.py`: Tests the interaction between BundleManager, FileExplorer, and KubectlExecutor
- `test_real_bundle.py`: Tests using actual support bundles
- `test_mcp_direct.py`: Tests direct MCP protocol communication
- `mcp_client_test.py`: Client for testing MCP protocol

### End-to-End Tests

The e2e tests test the full system:

- `test_container.py`: Tests the Docker container functionality
- `test_docker.py`: Tests Docker-specific functionality
- `test_mcp_protocol.py`: Tests the MCP protocol communication
- `test_container_mcp.py`: Tests MCP protocol with containers
- `quick_check.py`: Fast tests for basic functionality checks

## Test Data and Fixtures

The test fixtures directory contains:

- Sample data for testing, including a small support bundle
- Mock implementations for testing (mock_kubectl.py, mock_sbctl.py)

## Adding New Tests

When adding new tests:

1. Place them in the appropriate directory based on test scope:
   - Unit tests for individual components in `unit/`
   - Integration tests for component interactions in `integration/`
   - End-to-end tests in `e2e/`
2. Follow the naming convention of `test_*.py` for test files
3. Use pytest fixtures for test setup and teardown
4. Add documentation in docstrings for each test
5. Add appropriate timeout marks to prevent tests from hanging
6. Clean up resources in Docker and container tests