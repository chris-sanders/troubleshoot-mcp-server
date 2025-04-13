# Component: Command Executor (kubectl.py)

## Purpose
The Command Executor is responsible for executing kubectl commands against the Kubernetes API server initialized from a support bundle, enabling AI models to explore and analyze the Kubernetes resources captured in the bundle.

## Responsibilities
- Execute kubectl commands against the bundle's API server
- Validate commands for safety and compatibility
- Format command outputs appropriately (JSON or text)
- Handle command execution errors and timeouts
- Provide detailed execution metadata for diagnostics
- Ensure Kubernetes context is correctly set using the bundle's kubeconfig

## Interfaces

### Input
- **KubectlCommandArgs**:
  - **command**: The kubectl command to execute (e.g., "get pods -n kube-system")
  - **timeout**: Optional timeout in seconds (default: 30)
  - **json_output**: Whether to output in JSON format (default: true)

### Output
- **KubectlResult**:
  - **output**: Command output (either parsed JSON object or raw text)
  - **stdout**: Raw standard output
  - **stderr**: Raw standard error
  - **exit_code**: Command exit code
  - **command**: The full command that was executed
  - **duration_ms**: Execution time in milliseconds
  - **is_json**: Whether the output is in JSON format

## Dependencies
- `Bundle Manager`: For kubeconfig path and API server validation
- `kubectl`: CLI tool for Kubernetes interaction
- `asyncio`: For asynchronous process execution with timeout
- `json`: For parsing JSON output

## Error Handling
The Command Executor implements robust error handling for various scenarios:

- **CommandValidationError**: When the provided kubectl command is not allowed
- **CommandTimeoutError**: When the command execution exceeds the timeout
- **ApiServerError**: When the Kubernetes API server returns an error
- **KubectlNotFoundError**: When kubectl binary is not available
- **InvalidOutputFormatError**: When JSON output is requested but command produces non-JSON

## Implementation

### Command Validation

The executor filters kubectl commands for safety:

```python
def _validate_command(self, command: str) -> None:
    """
    Validate that the kubectl command is allowed.
    Raises CommandValidationError for disallowed commands.
    """
    # Must start with kubectl or be a valid subcommand
    normalized_cmd = command.strip()
    if normalized_cmd.startswith("kubectl "):
        normalized_cmd = normalized_cmd[8:].strip()
        
    # Check for shell metacharacters and injection attempts
    if any(char in command for char in [";", "&", "|", ">", "<", "`", "$", "\\"]):
        raise CommandValidationError(
            f"Command contains disallowed characters: {command}"
        )
        
    # Allowed command prefixes
    allowed_commands = [
        "get", "describe", "explain", "config", "version",
        "api-resources", "api-versions", "cluster-info"
    ]
    
    # Check if command starts with allowed prefix
    if not any(normalized_cmd.startswith(cmd) for cmd in allowed_commands):
        raise CommandValidationError(
            f"Command not allowed: {command}. Only informational commands are permitted."
        )
```

### Command Execution

The Command Executor runs kubectl with the bundle's kubeconfig:

```python
async def execute(
    self, command: str, timeout: int = 30, json_output: bool = True
) -> KubectlResult:
    """
    Execute a kubectl command against the bundle's API server.
    
    Args:
        command: The kubectl command to execute (without the 'kubectl' part)
        timeout: Command timeout in seconds
        json_output: Whether to format output as JSON
        
    Returns:
        KubectlResult with command output and metadata
    """
    # Validate the command
    self._validate_command(command)
    
    # Ensure bundle is initialized and get kubeconfig
    if not self._bundle_manager.is_initialized():
        raise BundleNotInitializedError("No bundle initialized")
    
    kubeconfig_path = self._bundle_manager.get_kubeconfig_path()
    
    # Prepare the environment with KUBECONFIG set
    env = os.environ.copy()
    env["KUBECONFIG"] = str(kubeconfig_path)
    
    # Add -o json if JSON output is requested and not already specified
    if json_output and "-o " not in command and "--output" not in command:
        command = f"{command} -o json"
    
    # Construct the full command
    full_command = f"kubectl {command}"
    
    # Record start time for duration measurement
    start_time = time.time()
    
    # Execute the command with timeout
    try:
        process = await asyncio.create_subprocess_shell(
            full_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        # Wait for the process with timeout
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout
            )
        except asyncio.TimeoutError:
            # Attempt to terminate the process
            process.terminate()
            raise CommandTimeoutError(
                f"Command timed out after {timeout} seconds: {full_command}"
            )
        
        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Process the results
        stdout_str = stdout.decode("utf-8", errors="replace")
        stderr_str = stderr.decode("utf-8", errors="replace")
        
        # Check for errors
        if process.returncode != 0:
            raise KubectlError(
                f"Command failed with exit code {process.returncode}: {stderr_str}"
            )
        
        # Parse JSON if requested and output looks like JSON
        is_json = False
        output = stdout_str
        if json_output and stdout_str.strip().startswith(("{", "[")):
            try:
                output = json.loads(stdout_str)
                is_json = True
            except json.JSONDecodeError:
                # Fall back to plain text if JSON parsing fails
                pass
        
        # Return the result
        return KubectlResult(
            output=output,
            stdout=stdout_str,
            stderr=stderr_str,
            exit_code=process.returncode,
            command=full_command,
            duration_ms=duration_ms,
            is_json=is_json
        )
    
    except KubectlError:
        # Re-raise KubectlError
        raise
    except CommandTimeoutError:
        # Re-raise timeout
        raise
    except Exception as e:
        # Wrap other exceptions
        raise KubectlError(f"Error executing kubectl command: {str(e)}")
```

## Sample Usage

```python
# Initialize dependencies
bundle_manager = BundleManager(Path("/data/bundles"))
kubectl_executor = KubectlExecutor(bundle_manager)

# Execute a kubectl command with JSON output
try:
    # Get pods in the kube-system namespace as JSON
    result = await kubectl_executor.execute(
        command="get pods -n kube-system",
        timeout=30,
        json_output=True
    )
    
    # Access the JSON output
    pods = result.output["items"]
    print(f"Found {len(pods)} pods in kube-system namespace")
    
    # Show execution metadata
    print(f"Command: {result.command}")
    print(f"Execution time: {result.duration_ms} ms")
    
except KubectlError as e:
    print(f"Error executing kubectl command: {e}")

# Execute a kubectl command with text output
try:
    # Describe a specific pod
    result = await kubectl_executor.execute(
        command="describe pod kube-apiserver-master1 -n kube-system",
        json_output=False
    )
    
    # Process the text output
    print(result.stdout)
    
except KubectlError as e:
    print(f"Error executing kubectl command: {e}")
```