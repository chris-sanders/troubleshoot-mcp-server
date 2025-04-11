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

1. Pull the Docker image:

```bash
docker pull ghcr.io/user/troubleshoot-mcp-server:latest
```

2. Run the container:

```bash
docker run -v /path/to/bundles:/bundles -e SBCTL_TOKEN=your-token -p 8080:8080 ghcr.io/user/troubleshoot-mcp-server:latest
```

Alternatively, use the provided `run.sh` script:

```bash
./run.sh /path/to/bundles your-token
```

See the [Docker documentation](DOCKER.md) for more details.

### Manual Installation

If you prefer to install the MCP server manually:

1. Ensure you have Python 3.11 or later installed.

2. Install required system dependencies:

```bash
# For Ubuntu/Debian
sudo apt-get update && sudo apt-get install -y curl

# For macOS
brew install curl
```

3. Install the `kubectl` command-line tool.

4. Install the `sbctl` command-line tool for bundle management.

5. Install the MCP server package:

```bash
# Using pip
pip install mcp-server-troubleshoot

# Using uv (recommended)
uv pip install mcp-server-troubleshoot
```

6. For development, install in development mode:

```bash
git clone https://github.com/user/troubleshoot-mcp-server.git
cd troubleshoot-mcp-server
uv pip install -e .
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

- **bundle__list**: List available support bundles.
  - Parameters: None
  - Returns: List of bundle information objects

- **bundle__initialize**: Download and initialize a support bundle.
  - Parameters:
    - `bundle_id`: ID of the bundle to initialize
  - Returns: Path to the initialized bundle

- **bundle__info**: Get information about the current active bundle.
  - Parameters: None
  - Returns: Bundle information object

### Kubectl Commands

- **kubectl__execute**: Execute kubectl commands against the bundle.
  - Parameters:
    - `command`: The kubectl command to execute (without 'kubectl' prefix)
  - Returns: Command output as string

Examples:

```
kubectl__execute command="get pods -n kube-system"
kubectl__execute command="describe deployment nginx -n default"
kubectl__execute command="get nodes -o json"
```

### File Operations

- **files__list_directory**: List files and directories.
  - Parameters:
    - `path`: Directory path (relative to bundle root)
  - Returns: List of file information objects

- **files__read_file**: Read file contents.
  - Parameters:
    - `path`: File path (relative to bundle root)
  - Returns: File contents as string

- **files__search_files**: Search for files containing a pattern.
  - Parameters:
    - `pattern`: Pattern to search for
    - `path` (optional): Path to restrict search to
  - Returns: List of matching file paths with line numbers

Examples:

```
files__list_directory path="/kubernetes/pods"
files__read_file path="/kubernetes/pods/kube-apiserver.yaml"
files__search_files pattern="CrashLoopBackOff"
```

## Usage Examples

### Example 1: Examining Namespace Resources

```
# List all namespaces
kubectl__execute command="get namespaces"

# List pods in a specific namespace
kubectl__execute command="get pods -n kube-system"

# Get details of a specific pod
kubectl__execute command="describe pod kube-apiserver-master -n kube-system"
```

### Example 2: Investigating Node Issues

```
# Check node status
kubectl__execute command="get nodes"

# Get detailed node information
kubectl__execute command="describe node my-node-name"

# Check pod distribution across nodes
kubectl__execute command="get pods -o wide --all-namespaces"
```

### Example 3: Analyzing Logs

```
# List log files
files__list_directory path="/kubernetes/logs"

# Read specific log file
files__read_file path="/kubernetes/logs/kube-apiserver.log"

# Search logs for errors
files__search_files pattern="error" path="/kubernetes/logs"
```

### Example 4: Checking Pod Configuration

```
# List pod definition files
files__list_directory path="/kubernetes/pods"

# Read pod definition
files__read_file path="/kubernetes/pods/kube-apiserver-master.yaml"

# Search for resource limits in pod definitions
files__search_files pattern="resources:" path="/kubernetes/pods"
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
4. Use `files__list_directory` to verify the correct path structure.

### Container Issues

If using the Docker container:

1. Verify the volume mount is correct.
2. Ensure environment variables are properly set.
3. Check Docker logs for error messages.
4. See [Docker troubleshooting](DOCKER.md#troubleshooting) for more details.