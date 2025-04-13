# FastMCP Lifecycle Management with Stdio Communication

This directory contains an example implementation of FastMCP lifecycle management using stdio (stdin/stdout) communication, intended for the MCP troubleshoot server.

## Files

- `stdio_lifecycle_example.py` - Complete example of a FastMCP server with lifecycle management and stdio mode
- `Dockerfile` - Docker configuration for running the example server
- `requirements.txt` - Required Python dependencies
- `demonstrate_lifecycle.sh` - Script to demonstrate the lifecycle in action, showing logs during startup and shutdown

## Understanding the Implementation

### Lifecycle Management

FastMCP uses an async context manager to handle lifecycle events:

1. **Startup Phase**: Code before the `yield` runs during startup
   - Initialize resources (database connections, file handles, etc.)
   - Start background tasks
   - Create context to share with tools

2. **Operation Phase**: While the application is running
   - FastMCP handles requests and responses
   - Tools access shared resources via the context

3. **Shutdown Phase**: Code in the `finally` block runs during shutdown
   - Clean up resources (close connections, delete temp files)
   - Cancel background tasks 
   - Log final status

### Stdio Communication

When using FastMCP with `use_stdio=True`:

- FastMCP reads requests from stdin, one JSON object per line
- FastMCP writes responses to stdout, one JSON object per line
- All logging must go to stderr to avoid interfering with protocol messages

## Key Considerations

1. **Logging**: Always configure logging to use stderr
   ```python
   logging.basicConfig(stream=sys.stderr)
   ```

2. **Buffering**: Disable Python's output buffering
   ```dockerfile
   ENV PYTHONUNBUFFERED=1
   ```

3. **Signal Handling**: Handle termination signals properly
   ```python
   signal.signal(signal.SIGTERM, handle_signal)
   ```

4. **Resource Tracking**: Keep track of all resources in the context
   ```python
   context = {"temp_files": {}, "background_tasks": {}}
   ```

5. **Error Handling**: Add error handling to cleanup operations
   ```python
   try:
       os.remove(path)
   except OSError as e:
       logger.error(f"Failed to remove {path}: {e}")
   ```

6. **Timeout Management**: Add timeouts to prevent hanging during shutdown
   ```python
   await asyncio.wait_for(task, timeout=5.0)
   ```

## Running the Demonstration

To see the lifecycle in action, run the demonstration script:

```bash
./demonstrate_lifecycle.sh
```

This script will:
1. Build a Docker image with the example server
2. Run a container that starts the server
3. Send a test request to the server
4. Trigger shutdown with SIGTERM
5. Display logs showing resource creation and cleanup

The demonstration clearly shows:
- Server startup with resource initialization
- Request handling via stdio
- Graceful shutdown with proper resource cleanup

You'll see logs verifying that temporary files are created during startup and removed during shutdown, providing visual confirmation that the lifecycle hooks work as expected.

## Applying to Your MCP Server

1. Implement the lifespan context manager with proper resource management
2. Configure FastMCP with `use_stdio=True`
3. Configure logging to use stderr
4. Set up proper signal handling
5. Configure Docker with `PYTHONUNBUFFERED=1`