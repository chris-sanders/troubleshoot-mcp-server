# Scripts Directory

This directory contains utility scripts for the MCP server for Kubernetes support bundles.

## Available Scripts

- `build.sh`: Builds the Docker container image
- `run.sh`: Runs the MCP server in a Docker container
- `run_tests.sh`: Runs all tests or a specific test suite

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
```

## Docker Support

The Docker scripts provide a convenient way to build and run the MCP server in a container environment.
For more detailed Docker usage instructions, please refer to [DOCKER.md](../DOCKER.md).