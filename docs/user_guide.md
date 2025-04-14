# User Guide

This guide provides instructions for installing, configuring, and using the MCP Server for Kubernetes Support Bundles.

## Table of Contents

- [Installation](#installation)
  - [Using Docker](#using-docker)
  - [Manual Installation](#manual-installation)
- [Authentication](#authentication)
- [Tool Reference](#tool-reference)
  - [Bundle Management](#bundle-management)
  - [Kubectl Commands](#kubectl-commands)
  - [File Operations](#file-operations)
- [Usage Examples](#usage-examples)
- [Troubleshooting](#troubleshooting)

## Installation

### Using Docker

The easiest way to use the MCP server is with Docker. The provided Docker image includes all necessary dependencies.

1. Build the Docker image:

```bash
docker build -t mcp-server-troubleshoot:latest .
```

2. Run the container:

```bash
docker run -i --rm \
  -v "/path/to/bundles:/data/bundles" \
  -e SBCTL_TOKEN="your-token" \
  mcp-server-troubleshoot:latest
```

For complete Docker usage instructions, including container configuration and environment variables, see the [Docker documentation](../DOCKER.md).

#### Using with MCP Clients

To use the Docker container with MCP clients like Claude or other AI models, add it to your client's configuration. The server provides a command to generate the necessary configuration:

```bash
docker run --rm mcp-server-troubleshoot:latest --show-config
```

### Manual Installation

If you prefer to install the MCP server manually:

1. Ensure you have Python 3.13 installed.

2. Install required system dependencies:

```bash
# For Ubuntu/Debian
sudo apt-get update && sudo apt-get install -y curl

# For macOS
brew install curl
```

3. Install the `kubectl` command-line tool.

4. Install the `sbctl` command-line tool for bundle management.

5. Create a virtual environment with UV (recommended):

```bash
# Create virtual environment
uv venv -p python3.13 .venv
source .venv/bin/activate
```

6. Install the MCP server package:

```bash
# For development mode
git clone https://github.com/user/troubleshoot-mcp-server.git
cd troubleshoot-mcp-server
uv pip install -e ".[dev]" 
```

## Authentication

The MCP server uses token-based authentication for accessing support bundles. You need to provide your authentication token using the `SBCTL_TOKEN` environment variable.

```bash
export SBCTL_TOKEN=your-token
```

This token is used to authenticate with the support bundle service when downloading and managing bundles.

## Tool Reference

The MCP server exposes the following tools for AI models to interact with Kubernetes support bundles:

### Bundle Management

- **initialize_bundle**: Initialize a support bundle for use.
  - Parameters:
    - `source`: Path to the support bundle file (.tar.gz)
  - Returns: Information about the initialized bundle

- **list_bundles**: List available support bundles.
  - Parameters: None
  - Returns: List of available bundles

- **get_bundle_info**: Get information about the current active bundle.
  - Parameters: None
  - Returns: Bundle information object

### Kubectl Commands

- **kubectl**: Execute kubectl commands against the bundle.
  - Parameters:
    - `command`: The kubectl command to execute (without 'kubectl' prefix)
  - Returns: Command output as string

Examples:

```
kubectl command="get pods -n kube-system"
kubectl command="describe deployment nginx -n default"
kubectl command="get nodes -o json"
```

### File Operations

- **list_files**: List files and directories.
  - Parameters:
    - `path`: Directory path (relative to bundle root)
    - `recursive` (optional): Whether to list recursively (default: false)
  - Returns: List of file information objects

- **read_file**: Read file contents.
  - Parameters:
    - `path`: File path (relative to bundle root)
  - Returns: File contents as string

- **grep_files**: Search for files containing a pattern.
  - Parameters:
    - `pattern`: Pattern to search for
    - `path` (optional): Path to restrict search to
  - Returns: List of matching file paths with line numbers

Examples:

```
list_files path="/kubernetes/pods"
read_file path="/kubernetes/pods/kube-apiserver.yaml"
grep_files pattern="CrashLoopBackOff"
```

## Usage Examples

### Example 1: Examining Namespace Resources

```
# List all namespaces
kubectl command="get namespaces"

# List pods in a specific namespace
kubectl command="get pods -n kube-system"

# Get details of a specific pod
kubectl command="describe pod kube-apiserver-master -n kube-system"
```

### Example 2: Investigating Node Issues

```
# Check node status
kubectl command="get nodes"

# Get detailed node information
kubectl command="describe node my-node-name"

# Check pod distribution across nodes
kubectl command="get pods -o wide --all-namespaces"
```

### Example 3: Analyzing Logs

```
# List log files
list_files path="/kubernetes/logs"

# Read specific log file
read_file path="/kubernetes/logs/kube-apiserver.log"

# Search logs for errors
grep_files pattern="error" path="/kubernetes/logs"
```

### Example 4: Checking Pod Configuration

```
# List pod definition files
list_files path="/kubernetes/pods"

# Read pod definition
read_file path="/kubernetes/pods/kube-apiserver-master.yaml"

# Search for resource limits in pod definitions
grep_files pattern="resources:" path="/kubernetes/pods"
```

## Troubleshooting

### Bundle Initialization Issues

If you encounter problems initializing a support bundle:

1. Verify that your `SBCTL_TOKEN` is set correctly and valid.
2. Check network connectivity to the support bundle service.
3. Ensure the bundle ID exists and is accessible with your token.
4. Check available disk space for bundle extraction.

### Kubectl Command Failures

If kubectl commands fail:

1. Verify that the bundle is properly initialized.
2. Check the command syntax for errors.
3. Ensure the command is supported within a bundle context.
4. Check if the resources you're querying exist in the bundle.

### File Operation Errors

If file operations fail:

1. Verify the path is correct and exists within the bundle.
2. Check file permissions.
3. Ensure the bundle is properly initialized.
4. Use `list_files` to verify the correct path structure.

### Container Issues

If using the Docker container:

1. Verify the volume mount is correct.
2. Ensure environment variables are properly set.
3. Check Docker logs for error messages.
4. See [Docker troubleshooting](../DOCKER.md#troubleshooting) for more details.