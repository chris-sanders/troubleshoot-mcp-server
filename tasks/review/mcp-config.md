# Task: Clean up MCP Client config

## Objective
Make configuring an MCP client as simple as possible with good defaults.

## Context
Today to configure an MCP client many values must be setup for the docker run command. Here is the working client config:

```
{  
  "mcpServers": {
    "troubleshoot": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "-v",
        "/Users/chris/Downloads:/data/bundles",
        "-e",
        "MCP_BUNDLE_STORAGE=/data/bundles",
        "-e",
        "MCP_KEEP_ALIVE='true'",
        "--rm",
        "--entrypoint", 
        "python",
        "mcp-server-troubleshoot:latest",
        "-m",
        "mcp_server_troubleshoot.cli"
      ]
    }
  }
}
```

Most of these parameters could be defaults or built into the OCI image. The user should only have to configure in their client overrides for inputs.

## Success Criteria
- MCP client can be used with defaults and minimum config
- MCP client can still be configured with a mount for for local bundles `/data/bundles` as an optional mount
- All tests are still passing
- MCP Client config is tested somehow either in current test or new testing managed by pytest
- Documentation is updated or crated for configuring the MCP Client

## Dependencies
N/A

## Implementation Plan
- Created config module for handling smart default configuration for MCP clients
- Added `--expand-config` flag to CLI for client configuration expansion
- Updated Docker entrypoint to better support simplified client configuration
- Updated run.sh to work with new entrypoint
- Added comprehensive documentation in user_guide.md and DOCKER.md
- Added example MCP client configurations in examples directory
- Created integration tests for the new configuration functionality

## Validation Plan
- Run full pytest suite
- Run lint and code formatting checks
- Verify documentation clarity and completeness

## Evidence of Completion
- [x] Command output or logs demonstrating completion
- All tests passing, including new integration tests for client configuration
- Successfully linted and formatted code
- All 69 existing tests continue to pass
- [x] Summary of manual testing performed
- Created multiple example JSON configuration files in examples/mcp-servers/ directory
- Verified configuration expansion works correctly with minimal configs 
- Tested custom bundle directory and environment variable support
- [x] Output of `pytest` results post change
```
============================= test session starts ==============================
platform darwin -- Python 3.13.2, pytest-8.3.5, pluggy-1.5.0
rootdir: /Users/chris/src/troubleshoot-mcp-server/mcp-config
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.9.0, asyncio-0.22.0, timeout-2.3.1
asyncio: mode=Mode.STRICT
collected 69 items

tests/e2e/test_container.py ....                                         [  5%]
tests/e2e/test_docker.py ........                                        [ 17%]
tests/integration/test_mcp_client_config.py ...                          [ 21%]
tests/integration/test_real_bundle.py ....                               [ 27%]
tests/test_all.py .                                                      [ 28%]
tests/unit/test_bundle.py ..............                                 [ 49%]
tests/unit/test_bundle_path_resolution.py .                              [ 50%]
tests/unit/test_components.py ...                                        [ 55%]
tests/unit/test_files.py .............                                   [ 73%]
tests/unit/test_grep_fix.py .                                            [ 75%]
tests/unit/test_kubectl.py ............                                  [ 92%]
tests/unit/test_server.py .....                                          [100%]

============================= 69 passed in 49.01s ==============================
```

## Notes
- The Docker container can now be launched with an improved entrypoint script that handles standard configuration formats
- The configuration expander automatically detects troubleshoot MCP server configurations and enhances them with sensible defaults
- Custom bundle directory paths can be specified without having to create the full Docker command line
- Environment variables can be provided and are automatically passed to the Docker container
- Added specific tests for different configuration scenarios to ensure reliability

## Progress Updates
- Implementation complete with all test cases passing
- Documentation updated with detailed examples for MCP client configuration
- Docker container and support scripts updated to support simplified configuration
- Created example configuration files for reference
