# Docker Usage Instructions

This document provides instructions for building and running the MCP server for Kubernetes support bundles in a Docker container. The container includes all required dependencies, including Python, `kubectl`, and `sbctl` (from replicatedhq/sbctl).

## Building the Container

You can build the Docker container using the provided build script:

```bash
# Navigate to the project directory
cd mcp-server-troubleshoot

# Run the build script
./build.sh
```

This will create a Docker image named `mcp-server-troubleshoot:latest`.

Alternatively, you can build the container manually:

```bash
docker build -t mcp-server-troubleshoot:latest .
```

## Running the Container

You can run the container using the provided run script, which automatically sets up volume mounts and environment variables:

```bash
# Set the SBCTL_TOKEN environment variable if needed
export SBCTL_TOKEN="your_token_here"

# Run the container
./run.sh

# You can also pass command-line options
./run.sh --verbose
```

Alternatively, you can run the container manually:

```bash
# Create a directory for bundles
mkdir -p ./bundles

# Run the container
docker run -it --rm \
  -v "$(pwd)/bundles:/data/bundles" \
  -e SBCTL_TOKEN="your_token_here" \
  mcp-server-troubleshoot:latest
```

## Configuration

The container can be configured using the following:

### Volume Mounts

- `/data/bundles`: Mount a local directory to store and access support bundles.

### Environment Variables

- `SBCTL_TOKEN`: Authentication token for accessing protected bundles.

## Usage Examples

### Initialize a Bundle

```bash
# Using the MCP inspector to send a request to initialize a bundle
echo '{"jsonrpc":"2.0","method":"call_tool","params":{"name":"initialize_bundle","arguments":{"source":"https://example.com/bundle.tar.gz"}}}' | ./run.sh
```

### Execute kubectl Commands

```bash
# Using the MCP inspector to send a request to execute a kubectl command
echo '{"jsonrpc":"2.0","method":"call_tool","params":{"name":"kubectl","arguments":{"command":"get pods"}}}' | ./run.sh
```

### Explore Files

```bash
# Using the MCP inspector to send a request to list files
echo '{"jsonrpc":"2.0","method":"call_tool","params":{"name":"list_files","arguments":{"path":"logs"}}}' | ./run.sh
```

## Troubleshooting

### Container Fails to Start

Check if:
- The Docker daemon is running
- You have permissions to run Docker commands
- The required ports are available

### Cannot Access Bundle Files

Check if:
- The volume mount is correctly specified
- The bundle directory exists locally
- The container has the necessary permissions

### Authentication Errors

Check if:
- The `SBCTL_TOKEN` environment variable is correctly set
- The token has the required permissions for the bundle source