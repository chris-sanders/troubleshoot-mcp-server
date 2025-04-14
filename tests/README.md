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
- `test_lifecycle.py`: Tests for lifecycle management
- `test_grep_fix.py`: Tests for grep functionality

#### Parameterized Unit Tests

These tests use pytest parameterization to test multiple input combinations:

- `test_files_parametrized.py`: Comprehensive tests for FileExplorer with multiple scenarios
- `test_kubectl_parametrized.py`: Tests kubectl command execution with various inputs
- `test_server_parametrized.py`: Tests MCP server tools with different input combinations

### Integration Tests

The integration tests test multiple components working together:

- `test_real_bundle.py`: Tests using actual support bundles
- `test_mcp_client_config.py`: Tests for MCP client configuration
- `test_stdio_lifecycle.py`: Documentation on lifecycle tests (now in e2e tests)

### End-to-End Tests

The e2e tests test the full system:

- `test_container.py`: Tests the Docker container functionality
- `test_docker.py`: Tests Docker-specific functionality
- `quick_check.py`: Fast tests for basic functionality checks

## Test Implementation Patterns

The test suite uses several patterns to improve quality and maintainability:

### 1. Parameterized Tests

Parameterized tests provide several benefits:
- More comprehensive coverage with less code duplication
- Clear documentation of valid/invalid inputs
- Easier to add new test cases
- Improved test readability

### 2. Test Assertion Helpers

The `TestAssertions` class provides:
- Consistent assertion patterns across tests
- Improved failure messages
- Reduced boilerplate in test methods
- Specialized assertions for API responses

### 3. Test Object Factories

The `TestFactory` class generates test objects with sensible defaults:
- Reduces boilerplate for creating common test objects
- Ensures consistency in test objects across test files
- Simplifies test setup by focusing only on relevant properties
- Makes tests more maintainable when object structures change

### 4. Fixtures for Common Scenarios

Several fixtures provide standardized test environments:

- `test_file_setup`: Creates a consistent file environment for testing
- `mock_bundle_manager`: Provides a pre-configured mock bundle manager
- `mock_command_environment`: Sets up isolated command testing environment
- `error_setup`: Provides standard error scenarios for testing

## Best Practices

Follow these guidelines when writing tests:

### 1. Focus on Behavior, Not Implementation

- Test what the function *does*, not how it *does it*
- Define clear functional contracts for components
- Avoid asserting on implementation specifics
- Test the public API rather than internal methods

### 2. Use Proper Test Isolation

- Each test should be independent
- Use fixtures for common setup
- Properly clean up resources
- Avoid test interdependence

### 3. Mock at the Right Level

- Mock external dependencies, not internal implementations
- When testing async code, use `AsyncMock` appropriately
- Create proper test doubles with the right interfaces
- Use patch with side_effect rather than monkeypatching

### 4. Asyncio Testing Best Practices

- Always use `@pytest.mark.asyncio` for async tests
- Use proper fixtures for event loop management
- Ensure all resources are cleaned up
- Handle asyncio-specific cleanup issues properly

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
7. Consider using parameterized tests for comprehensive coverage
8. Focus on testing behavior rather than implementation details

## Warning Handling

The test suite handles warnings in a targeted way:

1. **Asyncio-related warnings**: These are handled with specific filters in pytest.ini
   and conftest.py.

2. **Unix Pipe Transport Warning**: Filtered due to a Python standard library issue
   with `_UnixReadPipeTransport.__del__`.

3. **Event Loop Closed Warning**: Filtered because it occurs during normal asyncio cleanup
   when the event loop is closing.

When adding new warning filters:
- Never use blanket suppressions
- Document each suppressed warning with reasons
- Try to fix root causes rather than suppressing