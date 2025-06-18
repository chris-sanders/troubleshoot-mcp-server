# GitHub CLI Operations Guide

This document provides guidance on how to use the GitHub CLI (`gh`) for Git and GitHub operations as part of the AI workflow.

## PREFERRED: Use GitHub CLI (gh)

**RECOMMENDATION**: Prefer using the `gh` command-line interface for GitHub operations to save tokens and context. MCP GitHub tools are available as an alternative if needed.

**Preferred approach (recommended):**
- Use `gh pr create` for creating PRs
- Use `gh pr review` for PR comments and reviews
- Use `gh pr merge` for merging PRs
- Use other `gh` commands as needed

**Alternative approach (if MCP tools available):**
- `mcp__github__create_pull_request` ✓ (allowed but less preferred)
- `mcp__github__create_pull_request_review` ✓ (allowed but less preferred)
- `mcp__github__merge_pull_request` ✓ (allowed but less preferred)

## Git vs GitHub Operations

**Git operations** (local repository management) - Use standard Git commands:
- `git checkout -b branch-name` - Create branches
- `git add`, `git commit` - Stage and commit changes  
- `git push` - Push changes to remote
- `git status`, `git diff` - Check repository status

**GitHub operations** (remote platform interactions) - Use GitHub CLI:
- `gh pr create` - Create pull requests
- `gh pr review` - Add PR reviews/comments
- `gh pr merge` - Merge pull requests
- `gh pr view` - Get PR information
- All other GitHub operations

## Prerequisites

- GitHub CLI (`gh`) must be installed and authenticated
- The repository must be a valid git repository with GitHub remote
- Agent must have access to run shell commands (`gh` CLI)

## Branch Management

### Creating a New Branch

When starting a task, create a branch using the following naming convention:

```
task/[task-filename-without-extension]
```

Example for a task file named `feature-implementation.md`:

```
git checkout -b task/feature-implementation
```

### Working with Branches

Basic branch operations:

```bash
# Check current branch
git branch

# Switch to another branch
git checkout [branch-name]

# Create and switch to a new branch
git checkout -b [branch-name]
```

## Making Changes

### Staging Changes

```bash
# Stage specific files
git add [file-path]

# Stage all changes
git add .

# Check what's staged
git status
```

### Committing Changes

```bash
# Commit staged changes with a message
git commit -m "Descriptive message about changes"

# Commit all tracked files with a message
git commit -am "Descriptive message about changes"
```

### Good Commit Messages

- Be descriptive but concise
- Focus on "why" rather than "what" when possible
- Start with a verb in present tense (e.g., "Add", "Fix", "Update")
- Do not include AI attribution (no "Created by Claude" or similar)

## Pull Requests

### Creating a Pull Request

After pushing your branch, create a pull request using the GitHub CLI:

```bash
# Basic PR creation
gh pr create --title "Implement [task-name]" --body "PR description with summary and test plan"

# PR creation with specific base branch
gh pr create --title "Implement [task-name]" --base main --body "PR description"

# Create draft PR
gh pr create --title "Implement [task-name]" --draft --body "PR description"
```

### PR Description Template

```
## Summary
- Brief summary of changes
- Purpose of the changes

## Test Plan
- Steps to test the changes
- Expected results
```

### Updating Task with PR Information

After creating a PR, update the task file metadata:

```
**Status**: completed
**PR**: #[PR-number]
**PR URL**: [PR-URL]
**PR Status**: Open
```

Get PR information with:
```bash
gh pr view  # View current PR
gh pr view 123  # View specific PR number
```

### Handling PR Feedback

When receiving PR feedback:

1. Make requested changes
2. Commit with a descriptive message
3. Update the task progress section with:
   ```
   [Date]: Updated PR with requested changes: [summary of changes]
   ```

## Merging Process

When a PR is approved and ready to merge:

```bash
# Merge PR with default method
gh pr merge

# Merge with specific method
gh pr merge --squash  # Squash and merge
gh pr merge --merge   # Create merge commit
gh pr merge --rebase  # Rebase and merge

# Merge specific PR by number
gh pr merge 123 --squash
```

After merging:
1. Update the task file with `**PR Status**: Merged`
2. Move the task from `review` to `completed` folder
3. Update the task status to `completed` with completion date

## Review Workflows

### Adding PR Comments

Always include AI attribution in comments to distinguish between human and AI responses:

```bash
# Add general comment to PR
gh pr review --comment "🤖 Comment text

---
[Comment by AI Assistant]"

# Add comment to specific PR by number
gh pr review 123 --comment "🤖 Comment text

---
[Comment by AI Assistant]"

# Add comment to specific file/line (during review)
gh pr review --comment "🤖 Comment about specific code

---
[Comment by AI Assistant]"
```

### Comment Attribution Format

All AI-generated comments must follow this format:
1. Start with 🤖 emoji to visually flag AI-generated content
2. End with a signature block after a horizontal rule

Example:
```
🤖 [Comment content here]

---
[Comment by AI Assistant]
```

### Approving a PR

```
# Format
mcp__github__create_pull_request_review:
  owner: [repository-owner]
  repo: [repository-name]
  pullNumber: [PR-number]
  event: "APPROVE"
  body: "🤖 Approval comment\n\n---\n[Comment by AI Assistant]"
```

## Important Notes

- MCP tool configuration is handled at the user level in Claude Code, not at the project level
- This guide only covers workflow instructions for GitHub operations
- When the GitHub workflow is enabled, creating PRs is a standard part of task completion
- Task workflow: backlog → ready → started → review → completed
- Tasks move from "started" to "review" folder when PR is created
- Tasks move from "review" to "completed" after PR is merged
