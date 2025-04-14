# Docker Usage Instructions

This document provides instructions for building and running the MCP server for Kubernetes support bundles in a Docker container. The container includes all required dependencies, including Python, `kubectl`, and `sbctl` (from replicatedhq/sbctl).

## Building the Container

Build the Docker container with the standard Docker build command:

```bash
# Navigate to the project directory
cd troubleshoot-mcp-server

# Build the image
docker build -t mcp-server-troubleshoot:latest .
```

This will create a Docker image named `mcp-server-troubleshoot:latest`.

The project also includes a convenience script that performs the same operation:

```bash
./scripts/build.sh
```

## Running the Container

Run the container directly with Docker, mounting your bundle storage directory and setting required environment variables:

```bash
# Create a directory for bundles (if it doesn't exist)
mkdir -p ./bundles

# Set the SBCTL_TOKEN environment variable for bundle operations
export SBCTL_TOKEN="your_token_here"

# Run the container
docker run -i --rm \
  -v "$(pwd)/bundles:/data/bundles" \
  -e SBCTL_TOKEN="$SBCTL_TOKEN" \
  -e MCP_BUNDLE_STORAGE="/data/bundles" \
  mcp-server-troubleshoot:latest
```

### Command Parameters Explained

- `-i`: Run in interactive mode (required for MCP protocol communication)
- `--rm`: Automatically remove the container when it exits
- `-v "$(pwd)/bundles:/data/bundles"`: Mount local bundle directory to container path
- `-e SBCTL_TOKEN="$SBCTL_TOKEN"`: Pass authentication token from environment
- `-e MCP_BUNDLE_STORAGE="/data/bundles"`: Specify bundle storage location in container

### Optional Parameters

- `--verbose`: Enable verbose logging: `-e MCP_LOG_LEVEL=DEBUG`
- `--port 8080`: Map container port: `-p 8080:8080`

### Using Convenience Script

The project also includes a convenience script that simplifies running the container:

```bash
# Basic usage
./scripts/run.sh

# With options
./scripts/run.sh --verbose --bundle-dir=/path/to/bundles
```

## Configuration

The container can be configured using the following:

### Volume Mounts

- `/data/bundles`: Mount a local directory to store and access support bundles.

### Environment Variables

- `SBCTL_TOKEN`: Authentication token for accessing protected bundles.
- `MCP_BUNDLE_STORAGE`: Directory to store and manage bundles (defaults to `/data/bundles`).
- `MCP_LOG_LEVEL`: Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).

## Testing the Container

You can run the container tests using pytest:

```bash
# Run the container tests
pytest tests/e2e/test_container.py -v
```

For a more comprehensive test of the MCP protocol:

```bash
# Run the MCP protocol tests
./scripts/test_mcp.sh
```

These tests:
1. Verify that the container builds and runs correctly
2. Test the Python environment in the container
3. Verify the MCP server CLI functionality
4. Test JSON-RPC communication with the MCP server

## Configuration with MCP Clients

To use the Docker container with MCP clients (such as Claude or other AI models), add the server configuration to your client's settings.

### MCP Client Configuration

You can get the recommended configuration by running:

```bash
docker run --rm mcp-server-troubleshoot:latest --show-config
```

The output will provide a ready-to-use configuration for MCP clients:

```json
{
  "mcpServers": {
    "troubleshoot": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-v", 
        "${HOME}/bundles:/data/bundles",
        "-e",
        "SBCTL_TOKEN=${SBCTL_TOKEN}",
        "mcp-server-troubleshoot:latest"
      ]
    }
  }
}
```

This configuration assumes:

1. You have the `SBCTL_TOKEN` environment variable set in your environment
2. You want to store bundles in `${HOME}/bundles` on your host machine
3. You're using Docker as your container runtime

Replace `${HOME}/bundles` with the actual path to your bundles directory if needed.

## Usage Examples

### Initialize a Bundle

```bash
# Using echo to send a request to initialize a bundle
echo '{"jsonrpc":"2.0","id":"1","method":"call_tool","params":{"name":"initialize_bundle","arguments":{"source":"/data/bundles/bundle.tar.gz"}}}' | \
docker run -i --rm \
  -v "$(pwd)/bundles:/data/bundles" \
  -e SBCTL_TOKEN="$SBCTL_TOKEN" \
  mcp-server-troubleshoot:latest
```

### Execute kubectl Commands

```bash
# Using echo to send a request to execute a kubectl command
echo '{"jsonrpc":"2.0","id":"1","method":"call_tool","params":{"name":"kubectl","arguments":{"command":"get pods"}}}' | \
docker run -i --rm \
  -v "$(pwd)/bundles:/data/bundles" \
  -e SBCTL_TOKEN="$SBCTL_TOKEN" \
  mcp-server-troubleshoot:latest
```

### Explore Files

```bash
# Using echo to send a request to list files
echo '{"jsonrpc":"2.0","id":"1","method":"call_tool","params":{"name":"list_files","arguments":{"path":"/"}}}' | \
docker run -i --rm \
  -v "$(pwd)/bundles:/data/bundles" \
  -e SBCTL_TOKEN="$SBCTL_TOKEN" \
  mcp-server-troubleshoot:latest
```

### Using Convenience Script

If you prefer using the convenience script, you can still use it for all the examples above:

```bash
echo '{"jsonrpc":"2.0","id":"1","method":"call_tool","params":{"name":"list_files","arguments":{"path":"/"}}}' | ./scripts/run.sh
```

### Using with an MCP Client

Configure your MCP client to use the server as shown in the Configuration section, then you can interact with it via your AI model.

Example prompt to Claude:
```
I need help troubleshooting my Kubernetes cluster. I have a support bundle at `/path/to/bundles/bundle-2025-04-11.tar.gz`. 
Can you analyze it for common issues?
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

### JSON-RPC Communication Errors

Check if:
- The correct MCP protocol format is being used
- JSON is properly formatted in requests
- The tool name specified exists in the available tools list