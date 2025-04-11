# Component: MCP Protocol Handler

## Purpose
The MCP Protocol Handler manages communication between AI models and the server using the Model Context Protocol standard, routing requests to the appropriate components and formatting responses.

## Responsibilities
- Implement the stdio MCP communication protocol
- Define the API contract for exposed functions
- Validate and parse incoming requests
- Route requests to the appropriate components
- Format responses according to MCP standards
- Handle errors and provide informative error messages
- Register available tools with the MCP framework

## Interfaces
- **Input**: MCP requests (tool calls with arguments)
- **Output**: MCP responses (formatted results, error messages)

## Dependencies
- MCP package for protocol implementation
- Bundle Manager for bundle operations
- Command Executor for kubectl commands
- File Explorer for file operations
- Error handling for consistent response formatting

## Design Decisions
- Use the mcp package to leverage existing protocol implementation
- Implement the stdio communication protocol initially for simplicity
- Design for potential future support of the SSE protocol
- Use Pydantic models for request validation and type safety
- Provide detailed tool descriptions for AI model understanding
- Implement consistent error handling across all operations
- Design the API to be intuitive for AI models to use

## Examples

```python
# MCP tool registration
@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="initialize_bundle",
            description="Initialize a Kubernetes support bundle for analysis",
            inputSchema=InitializeBundleArgs.model_json_schema(),
        ),
        # Additional tools...
    ]

# MCP tool call handling
@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    if name == "initialize_bundle":
        args = InitializeBundleArgs(**arguments)
        result = await bundle_manager.initialize_bundle(args.source, args.force)
        return [TextContent(type="text", text=str(result))]
    # Additional tool handlers...
```
