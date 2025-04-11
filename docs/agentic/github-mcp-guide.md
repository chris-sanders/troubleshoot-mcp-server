# GitHub MCP Operations Guide

This document provides guidance on how to use GitHub MCP (Model Capability Provider) tools for Git and GitHub operations as part of the AI workflow.

## Prerequisites

- Claude Code must be configured with GitHub MCP access at the user level
- The repository must be a valid git repository

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

After pushing your branch, create a pull request using the MCP tools:

```
# Format
mcp__github__create_pull_request:
  owner: [repository-owner]
  repo: [repository-name]
  title: "Implement [task-name]"
  head: [branch-name]
  base: master
  body: "PR description with summary and test plan"
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

After creating a PR, update the task file metadata and move it to the review folder:

```
**Status**: review
**PR**: #[PR-number]
**PR URL**: [PR-URL]
**PR Status**: Open
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

```
# Format
mcp__github__merge_pull_request:
  owner: [repository-owner]
  repo: [repository-name]
  pullNumber: [PR-number]
  merge_method: "squash"  # or "merge" or "rebase"
```

After merging:
1. Update the task file with `**PR Status**: Merged`
2. Move the task from `review` to `completed` folder
3. Update the task status to `completed` with completion date

## Review Workflows

### Adding PR Comments

Always include AI attribution in comments to distinguish between human and AI responses:

```
# Format - IMPORTANT: Use create_pull_request_review for PR comments, NOT add_issue_comment
mcp__github__create_pull_request_review:
  owner: [repository-owner]
  repo: [repository-name]
  pullNumber: [PR-number]  # Use pullNumber (not issue_number) for PRs
  event: "COMMENT"  # or "APPROVE" or "REQUEST_CHANGES"
  body: "🤖 Comment text\n\n---\n[Comment by AI Assistant]"
```

> ⚠️ **IMPORTANT**: PRs and Issues are different in the GitHub API:
> - For Issues: Use `mcp__github__add_issue_comment` with `issue_number`
> - For PRs: Use `mcp__github__create_pull_request_review` with `pullNumber`
> - Never use `add_issue_comment` for PR comments, even though PRs and Issues share numbering

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
