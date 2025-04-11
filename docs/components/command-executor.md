# Component: Command Executor

## Purpose
The Command Executor is responsible for executing kubectl commands against the Kubernetes API server emulated from the support bundle and processing the results.

## Responsibilities
- Execute kubectl commands with proper environment configuration
- Validate command inputs for safety and correctness
- Format command outputs for consumption by AI models
- Handle command execution errors gracefully
- Provide contextual information about command results
- Encourage best practices in kubectl usage (e.g., namespace specification)

## Interfaces
- **Input**: kubectl command string, environment configuration (kubeconfig path)
- **Output**: Formatted command results (output, status, error messages)

## Dependencies
- kubectl CLI installed in the execution environment
- Bundle Manager for kubeconfig information
- Subprocess management for command execution
- JSON parsing for structured output

## Design Decisions
- Support arbitrary kubectl commands to provide maximum flexibility
- Default to JSON output format for consistent parsing
- Include command status and error information in the response
- Encourage namespace specification for better results
- Provide detailed error messages for debugging
- Handle both structured (JSON) and unstructured outputs

## Examples

```python
# Execute a kubectl command
result = await kubectl_executor.execute("get pods -n kube-system")

# Execute a more complex command
result = await kubectl_executor.execute(
    "get pods -n default -l app=nginx -o wide"
)

# Handle command with explicit output format
result = await kubectl_executor.execute(
    "get deployments -n default -o yaml"
)
```