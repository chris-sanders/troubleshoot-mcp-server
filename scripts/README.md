# Scripts Directory

This directory contains utility scripts for the MCP server for Kubernetes support bundles.

## Available Scripts

### Docker Scripts
- `build.sh`: Builds the Docker container image
- `run.sh`: Runs the MCP server in a Docker container

### Test Scripts
- `run_tests.sh`: Runs all tests or a specific test suite
- `run_e2e_tests.sh`: Runs e2e tests with different levels of testing
- `build_test.sh`: Builds a test Docker image with mock sbctl
- `prepare_tests.sh`: Prepares the environment for running e2e tests
- `debug_e2e.sh`: Runs e2e tests with debug options enabled

## Usage

All scripts should be run from the project root directory:

```bash
# Build the Docker image
./scripts/build.sh

# Run the container
./scripts/run.sh

# Run all tests
./scripts/run_tests.sh

# Run specific test suites
./scripts/run_tests.sh unit
./scripts/run_tests.sh integration
./scripts/run_tests.sh e2e

# Run e2e tests with different levels
./scripts/run_e2e_tests.sh --level=basic    # Basic tests only
./scripts/run_e2e_tests.sh --level=docker   # Docker build tests
./scripts/run_e2e_tests.sh --level=container # Container tests
./scripts/run_e2e_tests.sh --level=all      # All tests

# Prepare environment for e2e tests
./scripts/prepare_tests.sh

# Run e2e tests with debugging
./scripts/debug_e2e.sh
```

## Docker Support

The Docker scripts provide a convenient way to build and run the MCP server in a container environment.
For more detailed Docker usage instructions, please refer to [DOCKER.md](../DOCKER.md).

## Test Docker Images

For testing purposes, we provide a special version of the Docker image that uses mock implementations:

```bash
# Build the test Docker image
./scripts/build_test.sh
```

This test image uses a mock version of sbctl that doesn't require external dependencies, making it suitable for automated testing environments.