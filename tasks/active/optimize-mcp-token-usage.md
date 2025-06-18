# Task: Optimize MCP Server Token Usage with Verbosity Levels

## Metadata
**Status**: active
**Created**: 2025-06-18
**Priority**: high
**Complexity**: medium
**Estimated effort**: 2-3 days
**Started**: 2025-06-18
**Branch**: task/optimize-mcp-token-usage

## Objective
Implement configurable verbosity levels in the MCP server to reduce token consumption in production use while maintaining full debugging capabilities for development.

## Context
Claude Desktop users are experiencing rapid token exhaustion when using this MCP server. The server currently returns extensive diagnostic information, metadata, and formatting that's useful for debugging but wasteful for production AI interactions.

## Problem Statement
The server sends verbose responses with:
- Extensive diagnostic information in success cases
- Redundant metadata (human-readable + raw values)
- Multiple JSON blocks with markdown formatting
- Full file metadata even when not needed
- Large unfiltered datasets without pagination

## Success Criteria
- [ ] Implement 4 verbosity levels: minimal, standard, verbose, debug
- [ ] Default to minimal verbosity for production efficiency
- [ ] Maintain all current functionality in debug mode
- [ ] Measure 30-50% token usage reduction in minimal mode
- [ ] All tests pass with verbose mode matching current behavior

## Implementation Plan

### Verbosity Levels

#### 1. Minimal (default)
- Essential data only
- No diagnostic information
- No metadata unless critical
- Compact JSON structures
- No markdown formatting

#### 2. Standard  
- Core data with basic metadata
- Essential error information
- Simplified JSON structures

#### 3. Verbose
- Current behavior maintained
- Full metadata included
- Diagnostic information on errors

#### 4. Debug
- All verbose content plus:
- System diagnostic information
- Performance metrics
- Extended error context

### Tool-Specific Optimizations

#### `list_files`
**Minimal**: Array of names only
```json
["file1.txt", "dir1/", "file2.yaml"]
```

**Standard**: Basic file info
```json
[
  {"name": "file1.txt", "type": "file", "size": 1024},
  {"name": "dir1/", "type": "directory"}
]
```

**Verbose/Debug**: Current full metadata

#### `read_file`
**Minimal**: File content only (no line numbers)
**Standard**: Content with line count
**Verbose/Debug**: Current format with full metadata

#### `grep_files`
**Minimal**: Match results only
```json
[
  {"file": "app.py", "line": 42, "match": "error_handler"},
  {"file": "utils.py", "line": 15, "match": "error_handler"}
]
```

**Standard**: Add line content
**Verbose/Debug**: Current full format with context

#### `kubectl`
**Minimal**: Command output only
**Standard**: Output + exit code
**Verbose/Debug**: Current format with diagnostics

#### `initialize_bundle`
**Minimal**: Success/failure + bundle ID
**Standard**: Add basic bundle info
**Verbose/Debug**: Current diagnostic output

### Configuration

#### Environment Variables
- `MCP_VERBOSITY`: Global default level (minimal|standard|verbose|debug)
- `MCP_DEBUG`: Boolean to force debug mode

#### Tool Parameters
All tools accept optional `verbosity` parameter:
```json
{
  "name": "list_files",
  "arguments": {
    "path": "/kubernetes/pods",
    "verbosity": "minimal"
  }
}
```

### Response Structure Changes

#### Current (verbose) format:
```
Listed files in /kubernetes/pods:
```json
[{"name": "file1", "path": "/full/path", "size": 1024, "modified": "2025-01-01", ...}]
```

Directory metadata:
```json
{"total_files": 5, "total_dirs": 2, ...}
```
```

#### New minimal format:
```json
["file1", "dir1/", "file2"]
```

#### New standard format:
```json
{
  "files": [
    {"name": "file1", "type": "file"},
    {"name": "dir1", "type": "directory"}
  ],
  "count": 2
}
```

### Implementation Steps

1. **Add verbosity parameter to all tool schemas**
2. **Create response formatting functions for each verbosity level**
3. **Update each tool handler to use appropriate formatter**
4. **Add environment variable configuration**
5. **Update error handling for each verbosity level**
6. **Add pagination support for large datasets**

### Code Structure

```python
class ResponseFormatter:
    def __init__(self, verbosity: str = "minimal"):
        self.verbosity = verbosity
    
    def format_file_list(self, files: List[FileInfo]) -> str:
        if self.verbosity == "minimal":
            return json.dumps([f.name for f in files])
        elif self.verbosity == "standard":
            return json.dumps({
                "files": [{"name": f.name, "type": f.type} for f in files],
                "count": len(files)
            })
        # ... verbose/debug implementations
```

### Validation Plan

1. **Functionality Testing**:
   - All current tests pass in verbose mode
   - New tests for each verbosity level
   - Edge cases (empty results, errors)

2. **Token Usage Testing**:
   - Measure response sizes for each level
   - Test with various bundle sizes
   - Compare against current implementation

3. **Integration Testing**:
   - Test with Claude Desktop
   - Measure real-world token improvements
   - Validate AI agent compatibility

### Success Metrics
- **Token Reduction**: 30-50% reduction in minimal mode
- **Functionality**: 100% feature parity in verbose mode
- **Performance**: No degradation in response times
- **Tests**: All existing tests pass

### Configuration Examples

#### Production (minimal)
```bash
export MCP_VERBOSITY=minimal
```

#### Development (debug)
```bash
export MCP_VERBOSITY=debug
```

#### Per-tool override
```json
{
  "name": "list_files",
  "arguments": {
    "path": "/logs",
    "verbosity": "debug"
  }
}
```

### Documentation Updates Required

1. **AI Developer Documentation (`docs/agentic/ai-readme.md`)**:
   - Add section on verbosity levels and when to use each
   - Document the production-first design philosophy
   - Include guidelines for future tool development to default to minimal output
   - Add examples of token-efficient vs. verbose responses

2. **API Documentation**:
   - Document verbosity parameter for all tools
   - Show response examples for each verbosity level
   - Add configuration guide for environment variables

3. **Developer Guide**:
   - Add design principle: "Minimal by default, verbose when needed"
   - Include guidelines for implementing new tools with verbosity support
   - Document the token efficiency goals and measurement

4. **Architecture Documentation**:
   - Update to reflect the verbosity system design
   - Document the ResponseFormatter pattern
   - Include performance considerations

### Design Philosophy Documentation
The task should establish and document the principle:
> **Production-First Design**: All MCP tools should default to minimal, token-efficient responses that provide only essential data for AI interactions. Full diagnostic information and metadata should be available via verbosity controls for development and debugging purposes.

This ensures future developers understand the token efficiency goals and implement new tools accordingly.

## Notes
This task focuses on making the MCP server production-ready by default while preserving all debugging capabilities. The implementation should be straightforward - essentially creating "lite" versions of current responses while keeping the full versions available when needed.

The documentation updates are critical to ensure future development follows the same token-efficient principles.