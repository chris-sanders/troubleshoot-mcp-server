# MCP Protocol Integration Test Plan

This document outlines the implementation plan for a complete MCP protocol integration test that verifies client-server communication with the containerized MCP server.

## Objective

Create an end-to-end test that validates:
1. Building and starting the MCP server in a Docker container
2. Connecting to it from a client
3. Exchanging JSON-RPC messages over stdio
4. Verifying correct responses
5. Testing all key functionality

## Implementation Steps

### 1. Container-Client Test Framework

The framework should:
- Build the Docker container if needed
- Start the container in MCP mode with proper volume mounts
- Connect to it via stdio pipes
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
- It should mount the test fixtures directory to make test bundles available
- It should clean up containers and other resources after test completion

## Implementation Notes

1. Use `subprocess.Popen` to start the Docker container with proper pipes
2. Connect to stdin/stdout/stderr of the container for communication
3. Implement a simple MCPClient class to handle protocol details with containers
4. Use volume mounts to make test fixtures and bundle directories available
5. Make tests skippable in environments where Docker isn't available

## Expected Outcome

A robust test that validates the MCP server can communicate properly with clients, ensuring the correctness of the JSON-RPC implementation and all tool functionality.

## Path Forward

This test should be implemented as part of completing the current task-6-integration-testing PR, or as a separate follow-up PR if needed to avoid delaying the current work.
