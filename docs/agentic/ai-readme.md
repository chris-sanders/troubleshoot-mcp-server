# AI Agent Instructions

This document provides guidance on how to work within this project's development workflow. Follow these instructions to effectively contribute to the project.

## Task Management Workflow

As an AI agent, you should:

1. **Find tasks to work on**:
   - Look in `/tasks/backlog/` for new tasks to implement
   - Check in `/tasks/active/` for tasks needing continued work or PR feedback responses
   - Check dependencies to ensure they are completed

2. **Start working on a task**:
   - Move the task file from `/tasks/backlog/` to `/tasks/active/` using `git mv`:
     ```bash
     git mv tasks/backlog/[task-file].md tasks/active/[task-file].md
     ```
   - Update the task's metadata:
     - Change `**Status**: backlog` to `**Status**: active` 
     - Add `**Started**: YYYY-MM-DD` with today's date
   - Create a branch for the task:
     - Use naming convention: `task/[task-filename-without-extension]`
     - Example: `git checkout -b task/feature-implementation`
   - Add branch name to metadata: `**Branch**: task/feature-implementation`
   - Add a progress note with the current date in the Progress Updates section

3. **Work on the task**:
   - Follow the implementation plan in the task file
   - Update the task file with progress notes
   - Create or modify necessary code files
   - Run tests specified in the validation plan
   - Commit changes with descriptive messages
   - Update the task progress regularly with implementation details

4. **Create a Pull Request**:
   - When implementation is complete, create a PR:
     - Use the task name as the PR title
     - Include summary of changes and test plan in the PR body
   - Update the task's metadata:
     - Keep `**Status**: active` (no status change needed)
     - Add `**PR**: #[PR-number]` 
     - Add `**PR URL**: [PR-URL]`
     - Add `**PR Status**: Open`
   - Add a progress note with PR creation details
   - Keep the task file in `/tasks/active/` folder throughout PR review process

5. **Handle PR Feedback**:
   - Make requested changes to address PR feedback
   - When responding to PR comments:
     - Always prefix comments with 🤖 emoji
     - Always end comments with a signature: `---\n[Comment by AI Assistant]`
     - Example: `🤖 Feedback addressed in latest commit\n\n---\n[Comment by AI Assistant]`
   - Commit changes with descriptive messages
   - Update the task progress with details of changes
   - Keep the task in the `/tasks/active/` folder until PR is merged

6. **Complete a task** (after PR is merged):
   - Update the task's metadata:
     - Change `**Status**: active` to `**Status**: completed`
     - Add `**Completed**: YYYY-MM-DD` with today's date
     - Update `**PR Status**: Merged`
   - Document evidence of completion
   - Move the task file from `/tasks/active/` to `/tasks/completed/` using `git mv`:
     ```bash
     git mv tasks/active/[task-file].md tasks/completed/[task-file].md
     ```
   - Update relevant documentation in `/docs/` if necessary

7. **Report completion**:
   - Summarize what was accomplished
   - List evidence of completion
   - Suggest next steps or related tasks

## CRITICAL: Task File Movement Guidelines

**ALWAYS use `git mv` when moving task files between folders**. This ensures proper version control tracking and prevents orphaned documents.

**Correct approach:**
```bash
# Moving from backlog to active
git mv tasks/backlog/task-name.md tasks/active/task-name.md

# Moving from active to completed  
git mv tasks/active/task-name.md tasks/completed/task-name.md
```

**NEVER do this (incorrect):**
```bash
# This creates orphaned files and breaks version control tracking
mv tasks/backlog/task-name.md tasks/active/task-name.md
cp tasks/backlog/task-name.md tasks/active/task-name.md && rm tasks/backlog/task-name.md
```

**Why this matters:**
- Preserves file history and version control tracking
- Prevents duplicate or orphaned task files
- Maintains clean repository state
- Allows proper tracking of task progression through folders

## Context Understanding

Before working on any task:

1. Review `/docs/architecture.md` to understand the system architecture and project structure
2. Check other documentation in `/docs/components/`
3. Examine completed tasks in `/tasks/completed/` for similar work

## Code Quality Guidelines

When implementing solutions:

1. Follow the project's coding standards
2. Write clean, well-documented code
3. Add appropriate tests
4. Update documentation to reflect changes
5. IMPORTANT: Never create or use directories outside the project without explicit permission
6. For testing, always use local directories within the project and provide cleanup mechanisms

## Communication Format

When reporting progress or completion:

1. Be specific about what was accomplished
2. Reference specific files and line numbers
3. Explain any deviations from the task plan
4. Document any challenges encountered
5. Suggest improvements to the workflow if applicable

Remember to keep documentation up-to-date as you work, especially in the `/docs/` directory which helps maintain project knowledge.

## Git/GitHub Operations

When working with Git and GitHub:

1. **Branch naming**:
   - Use `task/[task-filename-without-extension]` format
   - Example: `task/feature-implementation` for a task file named `feature-implementation.md`

2. **Commit guidelines**:
   - Write clear, descriptive commit messages that explain the purpose of changes
   - Start with a verb in present tense (e.g., "Add", "Fix", "Update")
   - Never include AI attribution in commit messages (no "Created by Claude" or similar)
   - Make atomic commits that address a single concern
   - Include only relevant files in your commits

3. **Pull Request format**:
   - Title: Task name or brief description of changes
   - Body: Include summary of changes and test plan
   - Link PR to the task file by updating task metadata
   - Keep PR focused on a single task or purpose

4. **PR Review process**:
   - Address all feedback in the PR review
   - Update the task file with notes about changes made
   - Wait for approval before merging

5. **Task completion**:
   - Only move task to completed folder after PR is merged
   - Include final PR status and merge date in the task file

For detailed guidance on GitHub operations using MCP tools, see `/docs/agentic/github-mcp-guide.md`.
