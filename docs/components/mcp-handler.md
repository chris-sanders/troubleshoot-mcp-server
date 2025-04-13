# Component: MCP Protocol Handler (server.py)

## Purpose
The MCP Protocol Handler manages communication between AI models and the server using the FastMCP implementation of the Model Context Protocol standard, exposing tools for bundle initialization, kubectl command execution, and file exploration.

## Responsibilities
- Implement the MCP protocol for AI model communication
- Provide and document tool interfaces for AI model interaction
- Validate and process incoming tool requests
- Route requests to the appropriate components
- Format responses with rich context and diagnostic information
- Handle errors with informative messages and diagnostic context
- Ensure proper initialization and cleanup of resources

## Tools Provided

The MCP Handler exposes five primary tools:

1. **initialize_bundle**: Initialize a Kubernetes support bundle from URL or file
2. **kubectl**: Execute kubectl commands against the bundle's API server
3. **list_files**: List files and directories within the bundle
4. **read_file**: Read file contents with line numbers and binary detection
5. **grep_files**: Search for patterns across files with advanced filtering

## Interfaces

### Tools and Arguments

- **InitializeBundleArgs**: 
  - `source`: URL or file path to bundle
  - `force`: Boolean to force reinitialization

- **KubectlCommandArgs**:
  - `command`: kubectl command to execute
  - `timeout`: execution timeout in seconds
  - `json_output`: whether to format as JSON

- **ListFilesArgs**:
  - `path`: path within bundle to list
  - `recursive`: whether to list recursively

- **ReadFileArgs**:
  - `path`: path to file within bundle
  - `start_line`: line to start reading from
  - `end_line`: line to end reading at

- **GrepFilesArgs**:
  - `pattern`: regex pattern to search for
  - `path`: base path to search in
  - `recursive`: whether to search recursively
  - `glob_pattern`: file pattern filter
  - `case_sensitive`: whether search is case-sensitive
  - `max_results`: maximum results to return

### Output Format

All tools return responses in a consistent format:

```json
{
  "content": [
    {
      "type": "text",
      "text": "Formatted response with operation results and metadata"
    }
  ]
}
```

## Dependencies
- `FastMCP` from `mcp.server.fastmcp` for protocol implementation
- `Bundle Manager` for bundle lifecycle operations
- `kubectl Executor` for running Kubernetes commands
- `File Explorer` for file operations
- `asyncio` for asynchronous execution

## Implementation

The MCP Handler uses FastMCP's decorator pattern to register tools:

```python
# Create FastMCP server
mcp = FastMCP("troubleshoot-mcp-server")

# Tool implementation with decorator
@mcp.tool()
async def initialize_bundle(args: InitializeBundleArgs) -> List[TextContent]:
    """
    Initialize a Kubernetes support bundle for analysis. This tool loads a bundle 
    and makes it available for exploration with other tools.

    Args:
        args: Arguments containing:
            source: (string, required) The source of the bundle (URL or local file path)
            force: (boolean, optional) Whether to force re-initialization if a bundle 
                is already active. Defaults to False.

    Returns:
        Metadata about the initialized bundle including path and kubeconfig location.
        If the API server is not available, also returns diagnostic information.
    """
    bundle_manager = get_bundle_manager()
    
    try:
        # Implementation...
        return [TextContent(type="text", text=response)]
    except BundleManagerError as e:
        # Error handling with diagnostics...
        return [TextContent(type="text", text=error_message)]
```

## Singleton Pattern

The MCP Handler uses a singleton pattern for component access:

```python
# Global instances for managers/executors
_bundle_manager = None
_kubectl_executor = None
_file_explorer = None

def get_bundle_manager(bundle_dir: Optional[Path] = None) -> BundleManager:
    """Get the bundle manager instance."""
    global _bundle_manager
    if _bundle_manager is None:
        _bundle_manager = BundleManager(bundle_dir)
    return _bundle_manager
```

## Error Handling Strategy

Each tool implements comprehensive error handling:

1. Catch specific component errors (e.g., BundleManagerError)
2. Catch unexpected errors with broad exception handling 
3. Log errors for debugging
4. Add diagnostic information when available
5. Return formatted error messages to the client

## Sample Client-Server Interaction

```
Client: 
{
  "name": "initialize_bundle",
  "input": {
    "source": "https://example.com/bundle-123.tar.gz",
    "force": true
  }
}

Server:
{
  "content": [
    {
      "type": "text", 
      "text": "Bundle initialized successfully:\n```json\n{\n  \"path\": \"/data/bundles/bundle-123\",\n  \"kubeconfig_path\": \"/tmp/kubeconfig-123\",\n  \"source\": \"https://example.com/bundle-123.tar.gz\",\n  \"api_server_pid\": 12345,\n  \"initialized_at\": \"2025-04-12T10:15:30Z\"\n}\n```"
    }
  ]
}

Client:
{
  "name": "kubectl",
  "input": {
    "command": "get pods -n kube-system",
    "json_output": true
  }
}

Server:
{
  "content": [
    {
      "type": "text",
      "text": "kubectl command executed successfully:\n```json\n{\"items\": [{\"metadata\": {\"name\": \"kube-apiserver-master1\"}}]}\n```\n\nCommand metadata:\n```json\n{\"command\": \"kubectl get pods -n kube-system -o json\", \"exit_code\": 0, \"duration_ms\": 120}\n```"
    }
  ]
}
```