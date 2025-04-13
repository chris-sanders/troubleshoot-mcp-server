# Implementation Recommendations for MCP Server

Based on our exploration of FastMCP lifecycle management with stdio communication, here are detailed recommendations for implementing these features in the main MCP troubleshoot server.

## Core Implementation Components

### 1. Context Manager for Lifecycle Management

Implement a comprehensive context manager that handles all resource lifecycle management:

```python
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle for MCP troubleshoot server"""
    # === STARTUP PHASE ===
    logger.info("Starting MCP Troubleshoot Server")
    
    # Initialize bundle manager
    bundle_manager = BundleManager()
    
    # Create temp directory for extracted bundles
    temp_dir = create_temp_directory()
    
    # Initialize command executor
    command_executor = CommandExecutor()
    
    # Initialize file explorer
    file_explorer = FileExplorer()
    
    # Initialize kubectl client
    kubectl_client = KubectlClient()
    
    # Track background tasks
    background_tasks = {}
    
    # Start periodic cleanup task if configured
    if config.enable_periodic_cleanup:
        background_tasks["bundle_cleanup"] = asyncio.create_task(
            periodic_bundle_cleanup(bundle_manager, config.cleanup_interval)
        )
    
    # Create context to share with tools
    context = AppContext(
        bundle_manager=bundle_manager,
        command_executor=command_executor,
        file_explorer=file_explorer,
        kubectl_client=kubectl_client,
        temp_dir=temp_dir,
        background_tasks=background_tasks,
    )
    
    try:
        # Yield context to FastMCP server
        yield context
    finally:
        # === SHUTDOWN PHASE ===
        logger.info("Shutting down MCP Troubleshoot Server")
        
        # Cancel background tasks with timeout
        for name, task in background_tasks.items():
            if not task.done():
                logger.info(f"Cancelling background task: {name}")
                task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=5.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    logger.warning(f"Task {name} did not complete gracefully within timeout")
        
        # Clean up temporary files
        if os.path.exists(temp_dir):
            logger.info(f"Removing temporary directory: {temp_dir}")
            try:
                shutil.rmtree(temp_dir)
            except OSError as e:
                logger.error(f"Failed to remove temp directory {temp_dir}: {e}")
        
        # Close other resources
        if kubectl_client:
            await kubectl_client.close()
        
        # Close bundle manager
        await bundle_manager.close()
        
        logger.info("Shutdown complete")
```

### 2. AppContext Data Class

Define a strongly-typed context for sharing between lifecycle phases:

```python
@dataclass
class AppContext:
    """Application context for the MCP troubleshoot server"""
    bundle_manager: BundleManager
    command_executor: CommandExecutor
    file_explorer: FileExplorer
    kubectl_client: Optional[KubectlClient] = None
    temp_dir: str = ""
    background_tasks: Dict[str, asyncio.Task] = field(default_factory=dict)
```

### 3. FastMCP Server Configuration

Configure the server with stdio mode and the lifecycle context:

```python
# Configure logging to stderr for stdio mode
logging.basicConfig(
    level=config.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,  # Must use stderr for stdio mode
)

# Create FastMCP server with stdio mode
mcp = FastMCP(
    "MCP Troubleshoot Server",
    lifespan=app_lifespan,
    use_stdio=True
)
```

### 4. Resource Management

Implement specific resource handling for the MCP server:

#### Bundle Management

```python
async def periodic_bundle_cleanup(bundle_manager: BundleManager, interval: int = 3600):
    """Periodically clean up old bundles"""
    logger.info(f"Starting periodic bundle cleanup (interval: {interval}s)")
    try:
        while True:
            await asyncio.sleep(interval)
            logger.info("Running bundle cleanup")
            await bundle_manager.cleanup_old_bundles()
    except asyncio.CancelledError:
        logger.info("Bundle cleanup task cancelled")
        raise
```

#### Temporary File Management

```python
def create_temp_directory() -> str:
    """Create a temporary directory for bundle extraction"""
    temp_dir = os.path.join(tempfile.gettempdir(), f"mcp-troubleshoot-{uuid.uuid4()}")
    os.makedirs(temp_dir, exist_ok=True)
    logger.info(f"Created temporary directory: {temp_dir}")
    return temp_dir
```

### 5. Signal Handling

Implement proper signal handling:

```python
def handle_signal(signum, frame):
    """Handle termination signals for graceful shutdown"""
    sig_name = signal.Signals(signum).name
    logger.info(f"Received signal {sig_name} ({signum}). Initiating shutdown...")
    sys.exit(0)  # Trigger the context manager's finally block

# Register signal handlers
signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)
```

### 6. Tool Implementation

Implement tools that access the shared context:

```python
@mcp.tool()
def list_bundles(ctx: Context) -> List[str]:
    """List available support bundles"""
    app_ctx = ctx.request_context.lifespan_context
    return app_ctx.bundle_manager.list_bundles()

@mcp.tool()
def explore_bundle(ctx: Context, bundle_name: str, path: str = "/") -> Dict[str, Any]:
    """Explore files within a bundle"""
    app_ctx = ctx.request_context.lifespan_context
    return app_ctx.file_explorer.explore(
        bundle_name, 
        path, 
        temp_dir=app_ctx.temp_dir
    )
```

## Docker Configuration

Update the Dockerfile to support stdio mode and lifecycle management:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ /app/src/

# CRITICAL: Disable output buffering for reliable stdio communication
ENV PYTHONUNBUFFERED=1

# Set proper signal handling
STOPSIGNAL SIGTERM

# Allow time for graceful shutdown (in seconds)
STOP_TIMEOUT 30

# Run the MCP server in stdio mode
CMD ["python", "-m", "mcp_server_troubleshoot"]
```

## Integration with Existing Components

The current MCP server already has several key components that need to be integrated with the lifecycle management:

1. **Bundle Manager**: 
   - Integrate with lifecycle for initialization and shutdown
   - Add proper resource cleanup for temporary files
   - Implement connection pooling with proper cleanup

2. **Command Executor**:
   - Ensure running commands are properly terminated during shutdown
   - Add timeouts to prevent hanging during shutdown

3. **File Explorer**:
   - Track temporary extracted files for cleanup
   - Ensure proper cleanup of file handles

4. **Kubectl Integration**:
   - Properly close kubectl connections during shutdown
   - Add timeouts to prevent hanging during shutdown

## Testing Strategy

Implement comprehensive tests for lifecycle management:

1. **Unit Tests**:
   - Test lifecycle context manager in isolation
   - Test resource initialization and cleanup
   - Test signal handling

2. **Integration Tests**:
   - Test lifecycle with mock components
   - Test resource sharing between components
   - Test shutdown sequence with active operations

3. **Container Tests**:
   - Test stdio communication in container
   - Test shutdown handling with Docker signals
   - Test resource cleanup after container stop

## Implementation Steps

1. Create the `AppContext` data class
2. Implement the `app_lifespan` context manager
3. Add signal handling
4. Configure FastMCP with stdio mode
5. Update Docker configuration
6. Modify existing components to use the shared context
7. Add resource tracking and cleanup to all components
8. Implement tests for lifecycle management
9. Update documentation with lifecycle details

## Security Considerations

1. **Resource Limits**:
   - Implement maximum temporary storage limit
   - Add timeout for long-running operations
   - Limit number of concurrent operations

2. **Graceful Degradation**:
   - Handle errors during shutdown without preventing other cleanup
   - Log detailed information about cleanup failures
   - Implement priority-based cleanup (critical resources first)

3. **Sensitive Data**:
   - Ensure proper cleanup of files containing sensitive data
   - Add secure deletion for critical temporary files
   - Implement proper file permissions for temporary files

## Monitoring and Observability

1. **Logging**:
   - Add detailed logging for lifecycle events
   - Log resource usage during operation
   - Log cleanup success/failure

2. **Metrics**:
   - Track resource usage over time
   - Measure startup and shutdown time
   - Count resources created and cleaned up

3. **Health Checks**:
   - Implement readiness probe for startup completion
   - Implement liveness probe for runtime health
   - Implement shutdown status endpoint

## Conclusion

Implementing proper lifecycle management with stdio communication will significantly improve the reliability and resource usage of the MCP troubleshoot server. By following these recommendations, we can ensure that resources are properly initialized during startup and cleaned up during shutdown, even when the container is stopped abruptly.