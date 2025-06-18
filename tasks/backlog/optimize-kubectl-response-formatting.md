# Task: Optimize kubectl Response Formatting to Reduce Token Usage

## Objective
Dramatically reduce token usage in kubectl responses which currently can generate 160k+ tokens for simple commands like `kubectl get pod -n rook-ceph` due to excessive JSON formatting and verbosity.

## Context
Investigation revealed that kubectl responses are generating excessive tokens due to:
1. Default JSON output with `indent=2` formatting in verbose mode
2. JSON output enabled by default (`json_output: bool = Field(True, ...)`)
3. Additional metadata and markdown wrapping that compounds the bloat
4. Verbose mode being set as default in test environment potentially affecting production

A simple pod listing generating 160k tokens is completely unacceptable for LLM context usage.

## Success Criteria
- [ ] kubectl responses use minimal formatting by default
- [ ] JSON indentation removed or made optional
- [ ] Token usage for typical kubectl commands reduced by 50-75%
- [ ] Maintain readability for human users when explicitly requested
- [ ] Preserve all functionality while optimizing token efficiency
- [ ] Update default verbosity settings to minimize token usage

## Dependencies
- `src/mcp_server_troubleshoot/formatters.py` - Response formatting logic
- `src/mcp_server_troubleshoot/kubectl.py` - kubectl execution and JSON output defaults
- `src/mcp_server_troubleshoot/server.py` - Tool parameter handling
- `tests/conftest.py` - Default verbosity configuration

## Implementation Plan

### 1. Fix JSON Formatting Issues
- **File**: `src/mcp_server_troubleshoot/formatters.py:339`
- **Change**: Remove `indent=2` from `json.dumps(result.output, indent=2)`
- **Impact**: Eliminate JSON indentation bloat

### 2. Optimize Default Settings
- **File**: `src/mcp_server_troubleshoot/kubectl.py:47`
- **Change**: Consider changing `json_output: bool = Field(False, ...)` for minimal output by default
- **Alternative**: Keep JSON but ensure minimal formatting

### 3. Implement Compact JSON Mode
- **File**: `src/mcp_server_troubleshoot/formatters.py`
- **Add**: Compact JSON formatting option that outputs raw JSON without indentation
- **Logic**: Use compact format unless explicitly requesting verbose formatting

### 4. Review Verbosity Defaults
- **File**: `tests/conftest.py:12`
- **Change**: Ensure test environment doesn't force verbose mode in production
- **Add**: Clear separation between test and production verbosity defaults

### 5. Streamline Metadata
- **File**: `src/mcp_server_troubleshoot/formatters.py:345-357`
- **Change**: Reduce metadata bloat in responses
- **Keep**: Only essential information unless debug mode explicitly requested

## Validation Plan

### Token Usage Testing
- Test `kubectl get pods` in default namespace (small response)
- Test `kubectl get pods -n rook-ceph` (large response that caused 160k tokens)
- Test `kubectl get nodes -o wide` (medium response)
- Measure token counts before/after optimization

### Response Quality Testing  
- Verify JSON structure remains valid and parseable
- Ensure human readability is maintained when verbose mode explicitly requested
- Confirm all kubectl functionality works with optimized formatting

### Verbosity Level Testing
- **Minimal**: Raw output with minimal formatting
- **Standard**: Structured but compact JSON
- **Verbose**: Current formatting (when explicitly requested)
- **Debug**: Full metadata (when explicitly requested)

### Performance Benchmarks
- Measure token reduction percentages across different kubectl commands
- Target: 50-75% reduction in token usage for typical commands
- Ensure response times are not negatively impacted

## Target Token Reductions
Based on investigation findings:
- **Current**: ~93,644 tokens for rook-ceph pod listing (verbose with indent)
- **Target**: ~53,348 tokens (raw JSON without indentation)
- **Goal**: 43% reduction minimum, 60%+ preferred

## Evidence of Completion
(To be filled by AI)
- [ ] Before/after token count measurements for test commands
- [ ] Path to modified files with specific changes made
- [ ] Test results showing maintained functionality with reduced token usage

## Notes
- This is a critical performance issue affecting LLM context efficiency
- JSON indentation (`indent=2`) is the primary culprit causing massive token bloat
- Default settings should prioritize minimal token usage over human readability
- Human-readable formatting should be opt-in via explicit verbosity requests
- Consider this task high priority due to severe impact on LLM usability

## Progress Updates
(To be filled by AI during implementation)