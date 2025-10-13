# Task: Auto-start sbctl in Single Bundle Mode

**Status:** active
**Started:** 2025-10-13
**Priority:** high

## Problem Description

Environment Variables:
```
MCP_BUNDLE_STORAGE=/tmp/mcp-bundles
MCP_SINGLE_BUNDLE_MODE=true
PRESERVE_BUNDLES=true
SBCTL_TOKEN=<your-token>
GITHUB_TOKEN=<your-token>
```

Scenario:
1. Activity 1 (fresh MCP server process):
   - Calls initialize_bundle with bundle URL
   - MCP server downloads/extracts to /tmp/mcp-bundles/b_<id>/
   - Starts sbctl subprocess
   - Returns {"bundle_id": "b_xxx", "status": "ready"}
2. Activity 2 (NEW MCP server process):
   - Starts fresh Python process (new MCP server instance)
   - MCP_SINGLE_BUNDLE_MODE=true → Auto-discovers bundle from disk
   - Restores bundle metadata (bundle is "initialized": true)
   - But sbctl process is NOT running (died with previous process)
   - Returns {"bundle_id": "b_xxx", "status": "api_unavailable"}

## Expected Behavior

When MCP_SINGLE_BUNDLE_MODE=true and bundle is restored from disk, the MCP server should:
- Detect bundle has initialized=true but sbctl isn't running
- Auto-restart sbctl subprocess for that bundle
- Return "status": "ready" instead of "api_unavailable"

## Current Workaround

The agent must call initialize_bundle with force=true to restart sbctl, but this shouldn't be necessary in single bundle mode.

## File Location in MCP Server

- Issue is in bundle.py around line 2027-2062 in check_api_server_available()
- Should detect restored bundle + dead sbctl → restart sbctl automatically

## Progress

- 2025-10-13: Task started, worktree created
- 2025-10-13: Implemented auto-restart logic in check_api_server_available()
- 2025-10-13: Added integration test to verify sbctl auto-restart behavior
- 2025-10-13: All quality checks and tests passing

## Solution

Modified `check_api_server_available()` in bundle.py:2027-2064 to detect two scenarios:
1. **Case 1**: sbctl process crashed (process exists with non-None returncode) - already handled
2. **Case 2**: Bundle restored from disk but sbctl not started (process is None) - NEW

The fix checks if `self.active_bundle.initialized` is True but `self.sbctl_process` is None or crashed, then automatically calls `_restart_sbctl_process()` to restore functionality.

## Testing

Added `test_check_api_server_auto_restarts_sbctl_after_restore()` in `tests/integration/test_single_bundle_mode_stateless.py` to verify:
- Bundle initialized with sbctl running
- Server restart simulation (sbctl dies)
- Bundle auto-activated from disk (initialized=True, sbctl_process=None)
- check_api_server_available() automatically restarts sbctl
