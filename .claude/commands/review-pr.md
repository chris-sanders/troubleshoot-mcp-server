# Review PR

Conduct a thorough code review of a pull request.

## Instructions

Review pull request: **$ARGUMENTS**

**REVIEW CHECKLIST:**

### 1. Setup and Context
- [ ] Checkout PR: `gh pr checkout $ARGUMENTS` (if reviewing locally)
- [ ] Understand the feature/task being implemented
- [ ] Review PR description and test plan

### 2. Code Quality Review
- [ ] **Code Style**: Follows PEP 8 and project conventions
- [ ] **Type Annotations**: All functions have proper type hints
- [ ] **Error Handling**: Appropriate exception handling with context
- [ ] **Documentation**: Public interfaces have docstrings
- [ ] **Complexity**: Functions are focused and maintainable

### 3. Architecture and Integration
- [ ] **Design Patterns**: Follows existing project patterns
- [ ] **MCP Protocol**: Follows MCP standard implementations  
- [ ] **Dependencies**: No unnecessary or circular dependencies
- [ ] **Integration**: Integrates cleanly with existing components

### 4. Testing and Validation
- [ ] **Unit Tests**: New functionality has unit tests
- [ ] **Test Coverage**: Tests cover happy path and edge cases
- [ ] **Error Testing**: Error conditions are tested
- [ ] **Test Quality**: Tests are clear and maintainable

### 5. Security and Performance
- [ ] **Input Validation**: User inputs are validated
- [ ] **Path Traversal**: File operations prevent directory traversal
- [ ] **Resource Management**: Proper cleanup of resources
- [ ] **Performance**: No obvious bottlenecks

### 6. Project Standards Compliance
- [ ] **UV Usage**: Dependencies managed through UV
- [ ] **Import Organization**: Standard lib, third-party, local imports
- [ ] **Line Length**: Maximum 100 characters
- [ ] **Documentation**: Updates docs/ if needed

**VERIFICATION COMMANDS:**
```bash
# Verify code quality tools pass
uv run black --check .
uv run ruff check .
uv run mypy src

# Run tests
uv run pytest
uv run pytest --cov=src
```

**REVIEW CATEGORIES:**
- **Critical Issues**: Must fix before merge (security, breaking changes, failing tests)
- **Major Issues**: Should fix before merge (missing tests, poor error handling)
- **Minor Issues**: Nice to fix (style improvements, naming suggestions)
- **Positive Feedback**: Well-designed solutions, good practices

For each issue, provide:
1. File and line reference (e.g., "src/bundle.py:125")
2. Issue category and description
3. Suggested solution with code example if helpful

Use GitHub CLI for review: `gh pr review $ARGUMENTS --comment "feedback"` or `gh pr review $ARGUMENTS --approve`