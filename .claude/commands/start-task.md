# Start Task

Begin implementation of a planned development task.

## Instructions

Start working on task with name containing: **$ARGUMENTS**

**MANDATORY WORKFLOW (Execute in this exact order):**

### 1. Find and Prepare Task
- [ ] Find matching task file in `tasks/backlog/` containing "$ARGUMENTS" in filename
- [ ] Determine appropriate feature branch name based on task content
- [ ] Create worktree FIRST: `git worktree add trees/[feature-name] -b task/[feature-name]`
- [ ] Switch to worktree: `cd trees/[feature-name]`
- [ ] Verify location: `pwd` should show `trees/[feature-name]`

### 2. Task File Management (In Worktree)
- [ ] Move task file: `git mv tasks/backlog/[task-file].md tasks/active/[task-file].md`
- [ ] Update task metadata: Change status to "active", add started date
- [ ] Commit task move: `git commit -m "Start task: [feature-name]"`

### 3. Environment Verification
- [ ] Verify UV environment: `uv run python --version`
- [ ] Test dependencies: `uv run pytest --version`

**DEVELOPMENT WORKFLOW:**
- Work ONLY in your worktree directory: `trees/[feature-name]/`
- Use ONLY `uv run [command]` for all Python operations
- Make incremental commits during development
- Quality checks run automatically before PR creation (see completion workflow)

**COMPLETION WORKFLOW (Before PR):**
- Run auto-fix quality checks:
  - `uv run black .` (auto-format code)
  - `uv run ruff check . --fix` (auto-fix linting issues)
  - Commit any auto-fixes: `git commit -am "Auto-fix code quality issues"`
- Run final checks:
  - `uv run ruff check .` (verify no remaining lint issues)
  - `uv run mypy src` (type check - manual fixes required)
- Run full test suite: `uv run pytest`
- Only create PR after all checks pass

**IMPORTANT:**
- Worktree creation happens FIRST, before any other steps
- Task name is approximate - find best matching file
- Auto-fix tools run before manual verification
- All tests must pass before PR creation

Begin by finding the matching task file and creating the worktree.