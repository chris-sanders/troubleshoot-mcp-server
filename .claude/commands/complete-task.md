# Complete Task

Complete and finalize a development task.

## Instructions

Complete task: **$ARGUMENTS**

**MANDATORY COMPLETION CHECKLIST:**

### 1. Final Quality Assurance
- [ ] Run complete test suite: `uv run pytest`
- [ ] All tests MUST pass before proceeding
- [ ] Run quality checks: `uv run black . && uv run ruff check . && uv run mypy src`
- [ ] Fix any quality issues before proceeding

### 2. Code Review Self-Check
- [ ] All functions have type annotations
- [ ] Error handling is appropriate  
- [ ] New code follows project conventions
- [ ] No debug code or temporary changes remain

### 3. Testing Validation
- [ ] Unit tests exist for new functionality
- [ ] Integration tests exist if applicable
- [ ] Edge cases and error conditions are tested
- [ ] Run with coverage: `uv run pytest --cov=src`

### 4. Documentation Updates
- [ ] Update relevant documentation in `docs/` if needed
- [ ] Add/update docstrings for new public interfaces
- [ ] Check if README.md needs updates

### 5. Push and PR Creation
- [ ] Commit final changes: `git add . && git commit -m "Complete implementation of $ARGUMENTS"`
- [ ] Push branch: `git push -u origin task/$ARGUMENTS`
- [ ] Create PR (prefer gh CLI): `gh pr create --title "$ARGUMENTS" --body "Implementation summary and test plan"`
- [ ] Copy PR URL for task metadata

### 6. Task File Finalization
- [ ] Update task status to "completed"
- [ ] Add completion date and PR information  
- [ ] Move task IN WORKTREE: `git mv tasks/active/$ARGUMENTS.md tasks/completed/$ARGUMENTS.md`
- [ ] Commit task completion: `git commit -m "Complete task: $ARGUMENTS"`

### 7. Final Documentation
- [ ] Document implementation summary in task file
- [ ] List all files created or modified
- [ ] Note any follow-up tasks identified

**POST-MERGE CLEANUP (after PR is merged):**
- [ ] Delete worktree: `git worktree remove trees/$ARGUMENTS`
- [ ] Delete local branch: `git branch -d task/$ARGUMENTS`

Complete this checklist and report when task is ready for review.