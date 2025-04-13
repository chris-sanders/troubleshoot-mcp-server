# Component: Bundle Manager

## Purpose
The Bundle Manager is responsible for handling the lifecycle of Kubernetes support bundles, including downloading, extraction, initialization, diagnostics, and cleanup.

## Responsibilities
- Download support bundles from remote sources when needed
- Handle authentication for protected bundles
- Extract bundle contents to a specified location
- Initialize sbctl to create a Kubernetes API server from the bundle
- Maintain the state of the current active bundle
- Provide API server availability checking with diagnostics
- Clean up orphaned processes and resources
- Provide bundle metadata to other components

## Interfaces

### Input
- **Source**: URL or local file path to a support bundle
- **Force**: Boolean flag to force reinitialization
- **Bundle Directory**: Optional directory for bundle storage

### Output
- **BundleMetadata**: Contains bundle info including:
  - `path`: Path to the extracted bundle
  - `kubeconfig_path`: Path to the kubeconfig file for kubectl
  - `source`: Original source of the bundle
  - `api_server_pid`: Process ID of the API server
  - `initialized_at`: Timestamp of initialization

## Dependencies
- `sbctl` for bundle initialization and API server creation
- `asyncio` for asynchronous process management
- File system access for bundle storage
- Network access for downloading remote bundles
- Authentication handling for protected bundles

## Error Handling
The Bundle Manager implements robust error handling for various failure scenarios:

- **SbctlNotFoundError**: When sbctl is not installed or available
- **BundleInitializationError**: When the bundle fails to initialize
- **BundleNotFoundError**: When the specified bundle doesn't exist
- **ApiServerNotAvailableError**: When the Kubernetes API server isn't functioning
- **ProcessManagementError**: When there are issues with the sbctl process

## Implementation

### Key Methods

- **initialize_bundle(source, force)**: Initializes a bundle from a URL or local file
- **check_api_server_available()**: Verifies if the Kubernetes API server is responding
- **get_diagnostic_info()**: Collects diagnostic information for troubleshooting
- **_check_sbctl_available()**: Validates sbctl is installed and working
- **cleanup()**: Cleans up resources when shutting down

### sbctl Process Management

The Bundle Manager launches sbctl as a subprocess and manages its lifecycle:

```python
# Launch sbctl process
process = await asyncio.create_subprocess_exec(
    "sbctl", 
    "serve", 
    bundle_path, 
    "--kubeconfig", 
    kubeconfig_path,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE
)

# Store process for lifecycle management
self._api_server_process = process
self._api_server_pid = process.pid
```

### Bundle Path Resolution

The Bundle Manager handles both local and remote paths:

```python
# Handling local files
if os.path.exists(source) and (
    source.endswith(".tar.gz") or 
    source.endswith(".tgz") or 
    os.path.isdir(source)
):
    return Path(source).resolve()

# Handling remote URLs
if source.startswith(("http://", "https://")):
    # Download bundle or use sbctl directly
    return await self._download_or_use_remote_bundle(source)
```

### API Server Verification

The Bundle Manager actively checks if the API server is available:

```python
async def check_api_server_available(self) -> bool:
    """Check if the Kubernetes API server is available."""
    if not self.is_initialized():
        return False
        
    # Use kubectl to check API server
    env = os.environ.copy()
    env["KUBECONFIG"] = str(self._kubeconfig_path)
    
    try:
        process = await asyncio.create_subprocess_exec(
            "kubectl", "get", "pods", "--v=0",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        stdout, stderr = await process.communicate()
        return process.returncode == 0
    except Exception:
        return False
```

## Sample Usage

```python
# Initialize a bundle from a URL
bundle_manager = BundleManager(Path("/data/bundles"))
try:
    metadata = await bundle_manager.initialize_bundle(
        "https://vendor.replicated.com/troubleshoot/analyze/2024-04-11@08:15",
        force=False
    )
    
    # Check if API server is running properly
    api_server_available = await bundle_manager.check_api_server_available()
    if not api_server_available:
        # Get diagnostic information
        diagnostics = await bundle_manager.get_diagnostic_info()
        print(f"API server is not available. Diagnostics: {diagnostics}")
except BundleManagerError as e:
    print(f"Failed to initialize bundle: {e}")
```