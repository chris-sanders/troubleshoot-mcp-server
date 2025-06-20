# Claude Code for Automated Release Notes

## Metadata
- **Status**: backlog
- **Priority**: high
- **Created**: 2025-06-20
- **Epic**: Release Automation

## Problem Statement

Currently, the project has excellent CI/CD automation for testing and container publishing, but release notes generation is completely manual. This creates inconsistency in release documentation and adds manual overhead to the release process.

**Current State:**
- Automated container publishing via GitHub Actions
- Manual release note creation (no standardized format)
- Version inconsistency (pyproject.toml shows 0.1.0, git tags at 1.5.0)
- No CHANGELOG.md or automated release documentation

## Solution Overview

Integrate Claude Code with GitHub Actions to automatically generate professional release notes when publishing releases. This builds on the existing melange/apko and UV-based infrastructure.

## Requirements

### Functional Requirements
- Automatically generate release notes on git tag push
- Analyze commits between releases to categorize changes
- Create structured markdown with sections for features, fixes, breaking changes
- Integrate with existing container publishing workflow
- Support manual trigger for testing and ad-hoc releases

### Non-Functional Requirements
- Complete within 2-3 minutes of tag push
- Generate consistent, professional documentation
- Maintain existing CI/CD pipeline performance
- Provide fallback for manual release creation if automation fails

## Implementation Plan

### Phase 1: Foundation Setup (High Priority)
**Goal**: Establish Claude Code integration for automated release notes

**Files to Create/Modify:**
- `.github/workflows/generate-release-notes.yaml` - Standalone release notes generator
- `CHANGELOG.md` - Initialize changelog file
- Update `pyproject.toml` - Fix version synchronization to match git tags

**Implementation Steps:**
1. **Create Release Notes Workflow**
   - Use `anthropics/claude-code-base-action@beta`
   - Trigger on tag push or workflow_dispatch
   - Analyze git commits since last release
   - Generate structured markdown release notes
   - Create GitHub release with generated notes

2. **Add Claude GitHub App Integration**
   - Install Claude GitHub App
   - Add `ANTHROPIC_API_KEY` to repository secrets
   - Configure repository permissions

3. **Version Synchronization**
   - Update pyproject.toml version from 0.1.0 to current 1.5.0
   - Add pre-release version bump automation

### Phase 2: Enhanced Release Automation (Medium Priority)
**Goal**: Complete end-to-end release workflow automation

**Files to Create/Modify:**
- `.github/workflows/release.yaml` - Comprehensive release orchestration
- `scripts/release.sh` - Local release helper script
- Update `CLAUDE.md` - Add release workflow instructions

**Implementation Steps:**
1. **Unified Release Workflow**
   - Validate current state (clean working directory, passing tests)
   - Update pyproject.toml version automatically
   - Generate release notes from commits
   - Create and push git tag
   - Monitor CI pipeline completion
   - Create GitHub release

2. **Release Planning Assistant**
   - Analyze commit types to suggest version increment (patch/minor/major)
   - Validate SemVer compliance
   - Check for breaking changes in commits

### Phase 3: Advanced Features (Low Priority)
**Goal**: Intelligent release management and validation

**Files to Create/Modify:**
- `.github/workflows/post-release-validation.yaml` - Release verification
- `scripts/validate-release.sh` - Release health checks

**Implementation Steps:**
1. **Post-Release Validation**
   - Automated smoke testing of published containers
   - Verify container registry availability
   - Test MCP server functionality

2. **Release Analytics**
   - Track release metrics and patterns
   - Automated dependency update suggestions

## Technical Implementation

### Claude Code Integration
```yaml
- name: Generate Release Notes with Claude
  uses: anthropics/claude-code-base-action@beta
  with:
    prompt: |
      Analyze the merged commits and generate professional release notes.
      Focus on:
      - New features added
      - Bug fixes implemented  
      - Breaking changes
      - Performance improvements
      - Security updates
      
      Format as markdown with appropriate sections.
    model: "claude-3-7-sonnet-20250219"
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
    allowed_tools: [
      "Bash(git log --oneline --since='last tag')",
      "Bash(git diff HEAD~10..HEAD --name-only)",
      "View",
      "GlobTool"
    ]
```

### Authentication Requirements
- `ANTHROPIC_API_KEY` in repository secrets
- Standard `GITHUB_TOKEN` with repo access
- Claude GitHub App installation

### Integration Points
- **Existing CI/CD**: Works with current pr-checks.yaml and publish-container.yaml
- **Git Worktree Workflow**: Release scripts work within worktree environment
- **UV Environment**: All scripts use `uv run` commands for consistency

## Testing Strategy

### Unit Tests
- **Location**: `tests/unit/test_release_workflow.py`
- **Coverage**: Version parsing, changelog generation logic, Git operations
- **Command**: `uv run pytest tests/unit/test_release_workflow.py -v`

### Integration Tests
- **Location**: `tests/integration/test_github_integration.py`
- **Coverage**: GitHub API interactions, workflow trigger testing
- **Mocking**: GitHub API responses, Claude API calls

### E2E Tests
- **Location**: `tests/e2e/test_release_e2e.py`
- **Coverage**: Full release workflow with test repository
- **Environment**: Dedicated test repository or branch

### Workflow Testing
- Use `workflow_dispatch` for safe testing
- Test with non-production tags (e.g., `test-1.5.1`)
- Validate generated release notes quality and accuracy

## Acceptance Criteria

### Primary Success Metrics
- [ ] GitHub tag push automatically generates professional release notes
- [ ] Release notes include categorized changes (features, fixes, breaking changes)
- [ ] Version in pyproject.toml matches git tag version
- [ ] Generated release notes follow consistent markdown format
- [ ] Workflow completes within 2-3 minutes of tag push

### Quality Gates
- [ ] All existing CI tests pass before release creation
- [ ] Release notes accurately reflect actual code changes
- [ ] No manual intervention required for standard releases
- [ ] Errors in release generation are clearly reported
- [ ] Rollback capability if release generation fails

## Dependencies

### External Dependencies
- Anthropic Claude API access
- GitHub App permissions
- Existing git history with meaningful commit messages

### Internal Dependencies
- Current CI/CD pipeline (pr-checks.yaml, publish-container.yaml)
- UV-based Python environment
- Git worktree development workflow
- Melange/apko container build system

## Risk Assessment

### Risks
- **API Rate Limits**: Claude API usage limits could affect release frequency
- **Commit Message Quality**: Poor commit messages may result in low-quality release notes
- **Authentication Issues**: API key or GitHub App configuration problems

### Mitigation Strategies
- **Gradual Rollout**: Start with manual trigger workflow before automating on tag push
- **Fallback Plan**: Maintain ability to create releases manually if automation fails
- **Testing Strategy**: Thorough testing with test repositories and non-production tags
- **Monitoring**: Clear error reporting and logging for troubleshooting

## Definition of Done

- [ ] GitHub tag push triggers automated release note generation
- [ ] Generated release notes are created as GitHub releases
- [ ] Version synchronization between pyproject.toml and git tags
- [ ] All existing CI/CD tests continue to pass
- [ ] Documentation updated in CLAUDE.md
- [ ] Testing strategy implemented and passing
- [ ] Manual fallback process documented
- [ ] Monitoring and error handling in place

## Success Metrics

- **Time Savings**: Reduce release documentation time from 30+ minutes to < 5 minutes
- **Consistency**: 100% of releases have professional, structured release notes
- **Quality**: Release notes accurately reflect code changes with proper categorization
- **Reliability**: 95%+ success rate for automated release note generation
- **Developer Experience**: Simplified release process reduces manual errors