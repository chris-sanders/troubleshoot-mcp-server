# Task: Optimize kubectl Response Formatting to Reduce Token Usage

## Objective
Dramatically reduce token usage in kubectl responses which currently can generate 160k+ tokens for simple commands like `kubectl get pod -n rook-ceph` due to excessive JSON formatting and verbosity.

## Context
Investigation revealed a fundamental issue: kubectl responses are returning full Kubernetes API JSON objects instead of normal CLI output due to:
1. **Automatic `-o json` injection**: Line 177-178 in kubectl.py automatically adds `-o json` to commands
2. **JSON output enabled by default**: `json_output: bool = Field(True, ...)` on line 47
3. **CLI table output bypassed**: Users expect compact CLI tables, not verbose API responses
4. **Massive token bloat**: Full API objects contain extensive metadata vs simple table rows

The system is returning `kubectl get pods -o json` (full API objects) instead of `kubectl get pods` (compact tables). This is why a simple pod listing generates 160k tokens instead of ~100 lines of table output.

## Success Criteria
- [ ] Return normal kubectl CLI table output by default (not JSON API objects)
- [ ] Change default `json_output` to `False` to get compact CLI format
- [ ] JSON output available only when explicitly requested (`json_output=True`)
- [ ] Token usage for typical kubectl commands reduced by 90%+ (from API objects to CLI tables)
- [ ] Maintain familiar kubectl CLI experience users expect
- [ ] Preserve JSON functionality for programmatic use when needed

## Dependencies
- `src/mcp_server_troubleshoot/formatters.py` - Response formatting logic
- `src/mcp_server_troubleshoot/kubectl.py` - kubectl execution and JSON output defaults
- `src/mcp_server_troubleshoot/server.py` - Tool parameter handling
- `tests/conftest.py` - Default verbosity configuration

## Implementation Plan

### 1. Fix Default Output Format (CRITICAL)
- **File**: `src/mcp_server_troubleshoot/kubectl.py:47`
- **Change**: `json_output: bool = Field(False, ...)` - Disable JSON by default
- **Impact**: Return normal CLI tables instead of full API objects
- **Token Reduction**: 90%+ reduction (160k → ~1-2k tokens)

### 2. Remove Automatic JSON Injection
- **File**: `src/mcp_server_troubleshoot/kubectl.py:177-178`
- **Current**: Automatically adds `-o json` when `json_output=True`
- **Keep**: Logic but ensure it's only used when explicitly requested

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

### Output Format Testing
- **Default behavior (`json_output=False`)**: 
  - Verify `kubectl get pods` returns CLI table format (not JSON)
  - Confirm no `-o json` is added to commands automatically
  - Test that output looks like normal kubectl CLI (headers, columns, etc.)
- **Explicit JSON request (`json_output=True`)**:
  - Verify `-o json` is added to commands when explicitly requested
  - Confirm JSON structure remains valid and parseable  
  - Test that JSON output works for programmatic use cases
- **User-specified output formats**:
  - Verify commands like `kubectl get pods -o yaml` are not modified
  - Ensure existing `-o` flags in user commands are preserved

### Verbosity Level Testing
- **Minimal**: Raw output with minimal formatting
- **Standard**: Structured but compact JSON
- **Verbose**: Current formatting (when explicitly requested)
- **Debug**: Full metadata (when explicitly requested)

### Specific Test Cases to Implement
```python
# Test 1: Default behavior returns CLI format
def test_kubectl_default_format():
    result = kubectl_executor.execute("get pods", json_output=False)
    assert not result.is_json
    assert "NAME" in result.stdout  # CLI table header
    assert "READY" in result.stdout
    assert result.command == "get pods"  # No -o json added

# Test 2: Explicit JSON request works  
def test_kubectl_explicit_json():
    result = kubectl_executor.execute("get pods", json_output=True)
    assert result.is_json
    assert result.command == "get pods -o json"  # -o json was added
    
# Test 3: User-specified format preserved
def test_kubectl_user_format_preserved():
    result = kubectl_executor.execute("get pods -o yaml", json_output=False)
    assert result.command == "get pods -o yaml"  # No modification
```

### Performance Benchmarks
- Measure token reduction percentages across different kubectl commands
- Target: 90%+ reduction in token usage for typical commands (CLI vs JSON)
- Ensure response times are not negatively impacted

## Target Token Reductions
Based on investigation findings:
- **Current**: 160k+ tokens for rook-ceph pod listing (full API JSON objects)
- **Expected CLI Output**: ~1-2k tokens (compact table format)
- **Goal**: 90%+ reduction by returning normal CLI output instead of API objects

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