# Component: Bundle Manager

## Purpose
The Bundle Manager is responsible for handling the lifecycle of Kubernetes support bundles, including downloading, extraction, initialization, and cleanup.

## Responsibilities
- Download support bundles from remote sources when needed
- Handle authentication for protected bundles
- Extract bundle contents to a specified location
- Initialize sbctl to create a Kubernetes API server from the bundle
- Maintain the state of the current active bundle
- Clean up bundles when they are no longer needed
- Provide bundle metadata to other components

## Interfaces
- **Input**: Bundle source (URL or file path), authentication token
- **Output**: Bundle metadata (path, ID, status), Kubernetes API server details (kubeconfig path)

## Dependencies
- sbctl for bundle initialization and API server creation
- File system access for bundle storage
- Network access for downloading remote bundles
- Authentication handling for protected bundles

## Design Decisions
- Use sbctl's built-in capabilities for downloading and serving bundles to leverage existing functionality
- Store bundles in a configurable directory to support different deployment scenarios
- Use environment variables for authentication to keep credentials out of the application code
- Support both local and remote bundle sources to accommodate different user workflows
- Implement proper error handling and reporting for bundle operations

## Key sbctl Commands

### For Local Bundle Files

```bash
# Initialize bundle and create kubeconfig
sbctl serve /path/to/bundle.tar.gz --kubeconfig /path/to/kubeconfig

# Initialize bundle and launch a shell with KUBECONFIG set
sbctl shell /path/to/bundle.tar.gz --no-shell --kubeconfig /path/to/kubeconfig
```

### For Remote Bundle URLs

```bash
# Download and initialize bundle with authentication
# (SBCTL_TOKEN should be set in environment variables)
sbctl shell https://vendor.replicated.com/troubleshoot/analyze/bundle-id --no-shell --kubeconfig /path/to/kubeconfig
```

### Output Parsing

The Bundle Manager needs to:

1. Call sbctl and wait for it to initialize
2. Determine the kubeconfig path from the command output or from the explicitly specified `--kubeconfig` path
3. Verify that the kubeconfig file exists
4. Keep track of the sbctl process to maintain the API server

Example parsing logic:
```python
# When using explicit --kubeconfig path
kubeconfig_path = Path(specified_kubeconfig_path)
if not kubeconfig_path.exists():
    raise RuntimeError("Failed to initialize bundle: kubeconfig not created")

# When parsing from output
for line in output:
    if "export KUBECONFIG=" in line:
        kubeconfig_path = line.split("=")[1].strip()
        break
```

## Examples

```python
# Initialize a bundle from a URL
result = await bundle_manager.initialize_bundle(
    "https://vendor.replicated.com/troubleshoot/analyze/2024-04-11@08:15",
    force=False
)

# Initialize a bundle from a local file
result = await bundle_manager.initialize_bundle(
    "/path/to/local/bundle.tar.gz",
    force=True
)

# Check if a bundle is initialized
if bundle_manager.is_initialized():
    # Perform operations on the initialized bundle
    pass
```