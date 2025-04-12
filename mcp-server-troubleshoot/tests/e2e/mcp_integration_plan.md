# MCP Protocol Integration Test Plan

This document outlines the implementation plan for a complete MCP protocol integration test that verifies client-server communication.

## Objective

Create an end-to-end test that validates:
1. Starting the MCP server in a separate process
2. Connecting to it from a client
3. Exchanging JSON-RPC messages
4. Verifying correct responses
5. Testing all key functionality

## Implementation Steps

### 1. Server-Client Test Framework

The framework should:
- Start the MCP server in a subprocess
- Connect to it via stdio
- Handle JSON-RPC message exchange
- Provide clean setup/teardown
- Support asynchronous operations

### 2. Test Cases to Implement

1. **Tool Discovery**
   - Test that `get_tool_definitions` returns the expected list of tools
   - Verify all required tools are available

2. **Bundle Initialization**
   - Test initializing a bundle from a fixture
   - Verify successful initialization response

3. **Directory Listing**
   - Test listing files in the bundle
   - Verify response structure and content

4. **File Reading**
   - Test reading a file from the bundle
   - Verify file content in response

5. **Search Functionality**
   - Test searching for patterns in files
   - Verify search results

6. **Kubectl Commands**
   - Test executing kubectl commands
   - Verify command output

7. **Error Handling**
   - Test invalid tool calls
   - Test missing parameters
   - Test nonexistent resources

### 3. Test Data Requirements

- A small test support bundle in `tests/fixtures/`
- Sample search patterns guaranteed to have matches

### 4. Execution Environment

- The test should work both in development and CI environments
- It should handle environment variable setup for SBCTL_TOKEN
- It should clean up resources after test completion

## Implementation Notes

1. Use `asyncio.create_subprocess_exec` to start the server
2. Use pipes for stdin/stdout communication
3. Implement a simple MCPClient class to handle protocol details
4. Use a temporary directory for test bundles
5. Make tests skippable in environments where they can't run

## Expected Outcome

A robust test that validates the MCP server can communicate properly with clients, ensuring the correctness of the JSON-RPC implementation and all tool functionality.

## Path Forward

This test should be implemented as part of completing the current task-6-integration-testing PR, or as a separate follow-up PR if needed to avoid delaying the current work.
