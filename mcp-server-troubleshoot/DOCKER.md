# Docker Usage Instructions

This document provides instructions for building and running the MCP server for Kubernetes support bundles in a Docker container. The container includes all required dependencies, including Python, `kubectl`, and `sbctl` (from replicatedhq/sbctl).

## Building the Container

You can build the Docker container using the provided build script:

```bash
# Navigate to the project directory
cd mcp-server-troubleshoot

# Run the build script
./scripts/build.sh
```

This will create a Docker image named `mcp-server-troubleshoot:latest`.

Alternatively, you can build the container manually:

```bash
docker build -t mcp-server-troubleshoot:latest .
```

## Running the Container

You can run the container using the provided run script, which automatically sets up volume mounts and environment variables:

```bash
# Set the SBCTL_TOKEN environment variable for bundle operations
export SBCTL_TOKEN="your_token_here"

# Run the container in interactive mode
./scripts/run.sh

# You can also pass command-line options
./scripts/run.sh --verbose

# Run in MCP server mode for use with MCP clients (using stdio)
./scripts/run.sh --mcp

# Specify a custom bundle directory
./scripts/run.sh --bundle-dir=/path/to/bundles
```

Alternatively, you can run the container manually:

```bash
# Create a directory for bundles
mkdir -p ./bundles

# Run the container with the default entrypoint
docker run -it --rm \
  -v "$(pwd)/bundles:/data/bundles" \
  -e SBCTL_TOKEN="your_token_here" \
  -e MCP_BUNDLE_STORAGE="/data/bundles" \
  mcp-server-troubleshoot:latest

# Run the container with the MCP server stdio mode for use with MCP clients
docker run -i --rm \
  -v "$(pwd)/bundles:/data/bundles" \
  -e SBCTL_TOKEN="your_token_here" \
  -e MCP_BUNDLE_STORAGE="/data/bundles" \
  mcp-server-troubleshoot:latest python -m mcp_server_troubleshoot.cli
```

## Configuration

The container can be configured using the following:

### Volume Mounts

- `/data/bundles`: Mount a local directory to store and access support bundles.

### Environment Variables

- `SBCTL_TOKEN`: Authentication token for accessing protected bundles.
- `MCP_BUNDLE_STORAGE`: Directory to store and manage bundles (defaults to `/data/bundles`).

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

To use the Docker container with MCP clients (such as Claude or other AI models), add the server configuration to your client's settings:

### Claude/Anthropic MCP Configuration

In the `.mcpconfig.json` file (or corresponding environment variables):

```json
{
  "mcpServers": {
    "troubleshoot": {
      "type": "stdio",
      "command": "/path/to/scripts/run.sh",
      "args": [
        "--mcp"
      ],
      "env": {
        "SBCTL_TOKEN": "${SBCTL_TOKEN}"
      }
    }
  }
}
```

Or if you prefer using docker directly:

```json
{
  "mcpServers": {
    "troubleshoot": {
      "type": "stdio",
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-v", 
        "${LOCAL_BUNDLE_DIRECTORY}:/data/bundles",
        "-e",
        "SBCTL_TOKEN=${SBCTL_TOKEN}",
        "-e",
        "MCP_BUNDLE_STORAGE=/data/bundles",
        "mcp-server-troubleshoot:latest",
        "python",
        "-m",
        "mcp_server_troubleshoot.cli"
      ],
      "env": {}
    }
  }
}
```

Replace `${LOCAL_BUNDLE_DIRECTORY}` with the actual path to your bundles directory. Make sure the `SBCTL_TOKEN` environment variable is set in your environment if needed.

### Other MCP Clients

For other MCP clients, the configuration will follow a similar pattern:

1. Set the server type to `stdio`
2. Use `docker run -i --rm` as the command
3. Mount your bundles directory to `/data/bundles` in the container
4. Pass required environment variables like `SBCTL_TOKEN`

## Usage Examples

### Initialize a Bundle

```bash
# Using the MCP inspector to send a request to initialize a bundle
echo '{"jsonrpc":"2.0","id":"1","method":"call_tool","params":{"name":"initialize_bundle","arguments":{"source":"/data/bundles/bundle.tar.gz"}}}' | ./scripts/run.sh --mcp
```

### Execute kubectl Commands

```bash
# Using the MCP inspector to send a request to execute a kubectl command
echo '{"jsonrpc":"2.0","id":"1","method":"call_tool","params":{"name":"kubectl","arguments":{"command":"get pods"}}}' | ./scripts/run.sh --mcp
```

### Explore Files

```bash
# Using the MCP inspector to send a request to list files
echo '{"jsonrpc":"2.0","id":"1","method":"call_tool","params":{"name":"list_files","arguments":{"path":"/"}}}' | ./scripts/run.sh --mcp
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