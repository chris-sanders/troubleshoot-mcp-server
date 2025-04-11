# Troubleshooting Guide

This guide provides solutions for common issues you may encounter when using the MCP Server for Kubernetes Support Bundles.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Authentication Problems](#authentication-problems)
- [Bundle Management Issues](#bundle-management-issues)
- [Kubectl Command Failures](#kubectl-command-failures)
- [File Operation Errors](#file-operation-errors)
- [Container Issues](#container-issues)
- [Performance Problems](#performance-problems)
- [Common Error Messages](#common-error-messages)

## Installation Issues

### Package Installation Failures

**Issue**: Installation fails with dependency resolution errors.

**Solutions**:
1. Try using the recommended installation method with `uv`:
   ```
   uv pip install mcp-server-troubleshoot
   ```

2. If dependencies conflict with existing packages, consider using a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   uv pip install mcp-server-troubleshoot
   ```

3. Check your Python version. This package requires Python 3.11 or later.

### Missing System Dependencies

**Issue**: Installation succeeds, but the server fails to start due to missing system dependencies.

**Solutions**:
1. Install required system dependencies:

   For Ubuntu/Debian:
   ```
   sudo apt-get update && sudo apt-get install -y curl
   ```

   For macOS:
   ```
   brew install curl
   ```

2. Install kubectl if not already available:
   ```
   curl -LO "https://dl.k8s.io/release/stable.txt"
   curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
   chmod +x kubectl
   sudo mv kubectl /usr/local/bin/
   ```

3. Verify that all dependencies are installed:
   ```
   which kubectl
   kubectl version --client
   ```

## Authentication Problems

### Invalid or Missing Token

**Issue**: Server returns authentication errors when trying to list or initialize bundles.

**Solutions**:
1. Make sure you've set the SBCTL_TOKEN environment variable:
   ```
   export SBCTL_TOKEN=your-token
   ```

2. Verify that your token is valid and has not expired.

3. If using Docker, ensure you're passing the token to the container:
   ```
   docker run -e SBCTL_TOKEN=your-token ...
   ```

4. Check for any leading or trailing whitespace in your token.

### Token Permission Issues

**Issue**: Token authenticated successfully but you don't have permission to access specific bundles.

**Solutions**:
1. Confirm that your token has permission to access the requested bundles.

2. Contact your administrator to request the necessary permissions.

3. Try listing available bundles to see which ones you have access to:
   ```
   curl -H "Authorization: Bearer $SBCTL_TOKEN" https://api.example.com/bundles
   ```

## Bundle Management Issues

### Bundle Download Failures

**Issue**: Bundle downloads fail or time out.

**Solutions**:
1. Check your network connection and ensure you can reach the bundle service.

2. Verify that the bundle ID is correct.

3. Check available disk space for the download:
   ```
   df -h
   ```

4. If using a proxy, ensure it's properly configured for your environment.

5. Try downloading with increased timeout:
   ```
   export SBCTL_TIMEOUT=300  # Set timeout to 5 minutes
   ```

### Bundle Extraction Errors

**Issue**: Bundles download but fail to extract.

**Solutions**:
1. Ensure you have sufficient disk space for the extracted bundle (typically 3-5x the compressed size).

2. Check if the bundle archive is corrupt:
   ```
   tar -tvf bundle.tar.gz
   ```

3. Make sure your filesystem supports the required file sizes and attributes.

4. If the bundle uses a different compression format, make sure the appropriate tools are installed.

## Kubectl Command Failures

### Command Not Found

**Issue**: The server reports "kubectl not found" when executing commands.

**Solutions**:
1. Make sure kubectl is installed and in the system PATH.

2. If using Docker, verify that kubectl is installed in the container image.

3. Try specifying the full path to kubectl:
   ```
   export KUBECTL_PATH=/path/to/kubectl
   ```

### Unsupported Commands

**Issue**: Some kubectl commands fail with "unsupported command" errors.

**Solutions**:
1. Be aware that some kubectl commands aren't supported in the bundle context, such as:
   - `kubectl exec` (cannot execute commands in pods from a bundle)
   - `kubectl port-forward` (cannot forward ports to pods in a bundle)
   - `kubectl attach` (cannot attach to pod containers in a bundle)

2. Use alternative approaches:
   - Instead of `exec`, examine pod logs with `files__read_file`
   - Instead of `port-forward`, look for service configurations

### Resource Not Found

**Issue**: Kubectl commands fail with "not found" errors for resources that should exist.

**Solutions**:
1. Verify the resource exists in the bundle by listing resources of that type:
   ```
   kubectl__execute command="get pods -A"
   ```

2. Check if you're using the correct namespace:
   ```
   kubectl__execute command="get pods -n correct-namespace"
   ```

3. The bundle might be incomplete or the resource might have been created after the bundle was generated.

## File Operation Errors

### Path Not Found

**Issue**: File operations fail with "path not found" errors.

**Solutions**:
1. Make sure the path is relative to the bundle root, not an absolute system path.

2. Use `files__list_directory` to navigate and find the correct path.

3. Check that the bundle is properly initialized before attempting file operations.

4. Make sure you're using forward slashes (`/`) even on Windows systems.

### Security Errors

**Issue**: File operations fail with security or access errors.

**Solutions**:
1. Avoid attempting to access paths outside the bundle root using `../` or similar patterns.

2. Make sure the paths don't contain any special characters that might be interpreted as escape sequences.

3. If you receive a "suspicious path" error, review your path to ensure it doesn't contain any potential security issues.

## Container Issues

### Volume Mount Problems

**Issue**: Container cannot access or write to mounted volumes.

**Solutions**:
1. Ensure the volume mount paths are correct:
   ```
   docker run -v /absolute/path/on/host:/bundles ...
   ```

2. Check permissions on the host directory:
   ```
   ls -la /absolute/path/on/host
   ```

3. Make sure the container user has permission to write to the mounted volume.

4. Use bind mounts with proper options if you're experiencing permission issues:
   ```
   docker run -v /host/path:/bundles:Z ...
   ```

### Container Startup Failures

**Issue**: Container fails to start or exits immediately.

**Solutions**:
1. Check container logs for error messages:
   ```
   docker logs container-id
   ```

2. Verify that all required environment variables are set.

3. Make sure the image tag is correct and the image exists.

4. If you've built your own image, check that the entrypoint and CMD are properly configured.

5. Try running with interactive mode to see console output:
   ```
   docker run -it --rm your-image
   ```

## Performance Problems

### Slow Command Execution

**Issue**: Commands take a long time to complete.

**Solutions**:
1. For large bundles, use more specific queries rather than listing all resources:
   ```
   # Instead of
   kubectl__execute command="get pods -A"
   
   # Use
   kubectl__execute command="get pods -n specific-namespace"
   ```

2. Use labels and field selectors to limit results:
   ```
   kubectl__execute command="get pods -l app=frontend"
   ```

3. For file searches, provide a specific directory path to limit the search scope:
   ```
   files__search_files pattern="error" path="/kubernetes/logs/specific-pod"
   ```

4. Consider increasing resources allocated to the MCP server or container.

### Memory Issues

**Issue**: Server crashes with out-of-memory errors when processing large bundles.

**Solutions**:
1. Increase available memory for the process or container:
   ```
   docker run --memory=2g ...
   ```

2. Break down operations into smaller chunks, especially for large file operations.

3. Use more specific paths when searching or listing files to reduce memory requirements.

4. Consider upgrading to a server with more RAM for very large bundles.

## Common Error Messages

### "No bundle initialized. Use bundle__initialize first"

This error occurs when you try to use kubectl or file operations before initializing a bundle.

**Solution**: Initialize a bundle first:
```
bundle__initialize bundle_id="bundle-123"
```

### "Access to path outside bundle root is not allowed"

This security error occurs when attempting to access files outside the bundle directory.

**Solution**: Use only paths relative to the bundle root and avoid path traversal patterns like `../`.

### "Command 'kubectl exec' is not supported in bundle context"

Some kubectl commands that interact with live pods are not supported when working with bundles.

**Solution**: Use file operations to examine pod definitions and logs instead of trying to execute commands in containers.

### "Bundle extraction failed: Insufficient disk space"

This occurs when there isn't enough disk space to extract the bundle.

**Solution**: Free up disk space or mount a volume with more space available.

### "Failed to connect to bundle service: Network error"

This indicates network connectivity issues when trying to access the bundle service.

**Solution**: Check your network connection, proxy settings, and make sure the service URL is correct.

### "JSON parsing error in kubectl output"

This can happen when trying to parse kubectl output as JSON when it's not in JSON format.

**Solution**: Explicitly request JSON output with the `-o json` flag in your kubectl command.