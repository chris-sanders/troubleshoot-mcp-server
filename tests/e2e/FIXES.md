# E2E Test Fixes

This document describes the changes made to fix the e2e tests after the project restructuring.

## Issues Identified

1. **Path Resolution**: After restructuring, the tests were unable to find necessary files due to path changes.
2. **sbctl Missing**: The tests rely on sbctl, which might not be installed in all environments.
3. **Hanging Tests**: The MCP protocol tests were hanging due to improper handling of timeouts and communication.
4. **Docker Build Issues**: The Docker build process was referencing incorrect paths.

## Solutions Implemented

### Mock sbctl Implementation

- Created a mock `sbctl` implementation in `tests/fixtures/mock_sbctl.py` that provides a simplified version of the real `sbctl` behavior.
- Modified the bundle manager to detect when it should use the mock sbctl implementation via the `USE_MOCK_SBCTL` environment variable.

### Test Docker Image

- Created a special `Dockerfile.test` specifically for testing that uses our mock sbctl implementation.
- Added a `build_test.sh` script to build the test image.
- Modified `conftest.py` to use the test build script for e2e tests.

### Improved Client Implementations

- Enhanced the `DockerMCPClient` and `MCPClient` classes with better error handling, timeouts, and debugging information.
- Added select-based I/O to avoid hanging when reading from processes.
- Added proper cleanup of resources to prevent orphaned processes.

### Path Resolution

- Made sure all fixtures and resources use absolute paths.
- Added diagnostic logging to track file path resolution.

### Testing Utilities

- Added scripts for test preparation and debugging:
  - `prepare_tests.sh`: Sets up the environment for running e2e tests
  - `debug_e2e.sh`: Runs tests with verbose debugging enabled
  - Environment variable settings in `tests/fixtures/env.sh`
  
### Documentation

- Added README.md to the e2e tests directory with instructions on running tests.
- Added this FIXES.md file to document the changes made.

## How to Run Tests

See the [README.md](./README.md) for detailed instructions on running the tests.