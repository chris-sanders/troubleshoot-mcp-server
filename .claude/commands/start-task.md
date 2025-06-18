# Start Task

Begin implementation of a planned development task.

## Instructions

Start working on task: **{{TASK_NAME}}**

**MANDATORY PRE-WORK CHECKLIST:**

### 1. Environment Setup
- [ ] Verify environment: `./scripts/setup_env.sh` (if not done)
- [ ] Test setup: `uv run pytest tests/unit/test_components.py -v`

### 2. Git Worktree Setup  
- [ ] Create worktree: `git worktree add trees/{{TASK_NAME}} -b task/{{TASK_NAME}}`
- [ ] Switch to worktree: `cd trees/{{TASK_NAME}}`
- [ ] Verify location: `pwd` should show `trees/{{TASK_NAME}}`

### 3. Task File Management
- [ ] Move task file IN WORKTREE: `git mv tasks/backlog/{{TASK_NAME}}.md tasks/active/{{TASK_NAME}}.md`
- [ ] Update task metadata: Change status to "active", add started date
- [ ] Commit task move: `git commit -m "Start task: {{TASK_NAME}}"`

### 4. Development Environment Check
- [ ] Verify UV environment: `uv run python --version`
- [ ] Test dependencies: `uv run pytest --version`

**DEVELOPMENT WORKFLOW:**
- Work ONLY in your worktree directory: `trees/{{TASK_NAME}}/`
- Use ONLY `uv run [command]` for all Python operations
- After ANY code changes, run mandatory quality checks:
  - `uv run black .` (format code)
  - `uv run ruff check .` (lint code)  
  - `uv run mypy src` (type check)
- Run relevant tests: `uv run pytest tests/unit/test_[component].py -v`
- Make atomic commits with descriptive messages

**IMPORTANT:**
- All quality checks MUST pass before proceeding
- Update task progress regularly
- Follow existing code patterns and conventions

Confirm checklist completion, then begin implementation.