# Plan Task

Plan a new development task with comprehensive analysis.

## Instructions

You are planning a development task for the MCP Server for Kubernetes Support Bundles project.

**Task to plan:** $ARGUMENTS

**Requirements:**
1. Analyze the task requirements and identify scope
2. Check existing codebase for similar implementations (use search tools)
3. Plan implementation approach with dependencies
4. Define testing strategy (unit, integration, e2e as needed)
5. Create step-by-step implementation plan, with small vertical slices and progress tracking in the task.

**Deliverables:**
1. **Implementation Plan**: Detailed steps with order of operations
2. **Files to Create/Modify**: Specific file paths and purpose
3. **Testing Strategy**: What tests are needed and where
4. **Dependencies**: What existing code/systems this interacts with
5. **Acceptance Criteria**: How to know the task is complete

**Code Standards to Follow:**
- Use UV for all Python operations (`uv run pytest`, etc.)
- Follow existing code patterns and conventions  
- Add type annotations and docstrings
- Handle errors with specific exceptions
- Work in git worktree under `trees/` directory

Provide a comprehensive plan that can be executed by following the implementation steps.
DO NOT START ON THE WORK
