# Task: GitHub Workflow for Container Publishing

## Metadata
**Status**: completed
**Created**: 2025-04-25
**Started**: 2025-04-25
**Completed**: 2025-04-25
**Branch**: fix-podman-error
**PR**: #25
**PR URL**: https://github.com/chris-sanders/troubleshoot-mcp-server/pull/25
**PR Status**: Merged

## Objective
Create a GitHub workflow that automatically builds and publishes the container image to GitHub Container Registry (ghcr.io) whenever a SemVer tag (e.g., "1.0.0" without 'v' prefix) is pushed to the primary branch.

## Context
Currently, the container image for the MCP Server is built manually using the `scripts/build.sh` script. We need to automate the build and publishing process for releases to make it easier to distribute the software. This task will implement a GitHub Actions workflow that triggers on SemVer tag pushes and publishes the container to ghcr.io.

## Success Criteria
- [x] GitHub workflow file created in `.github/workflows/` directory
- [x] Workflow triggers on SemVer tag pushes (e.g., "1.0.0", without 'v' prefix)
- [x] Workflow uses the existing `scripts/build.sh` script for building the container
- [x] Workflow publishes the container to GitHub Container Registry (ghcr.io)
- [x] The image is tagged with both the SemVer tag and "latest"
- [x] Documentation added explaining how to release new versions
- [x] Fixed Podman configuration in the workflow

## Dependencies
- Complete Containerfile (already completed)
- Working build script (already completed)

## Implementation Plan
1. Create a new workflow file at `.github/workflows/publish-container.yml`
2. Configure the workflow to trigger on tag pushes matching the SemVer pattern (without 'v' prefix)
3. Set up the workflow job with the following steps:
   - Check out the repository
   - Set up Podman (replacing Docker)
   - Log in to GitHub Container Registry using GitHub Actions credentials
   - Extract version from tag to use as image tag
   - Modify or use the build script to build the container with the correct tag
   - Push the container to ghcr.io with both the version tag and "latest" tag
4. Add documentation about the release process to the project README or a new RELEASE.md file
5. Test the workflow by pushing a test tag to verify it works correctly

## Validation Plan
- Perform a dry run locally to simulate what the workflow will do
- Review the workflow for security best practices
- Push a test tag to trigger the workflow and verify the container is published correctly
- Note: Since this is a GitHub workflow, full testing can only be done in the GitHub environment

## Evidence of Completion
- [x] Path to created workflow file: `.github/workflows/publish-container.yaml`
- [x] Fixed Podman configuration in GitHub workflow
- [x] Documentation added about the release process: `RELEASE.md` and updated `README.md`

## Notes
- The workflow needs to handle GitHub Container Registry authentication securely
- We need to ensure proper image tagging with both version-specific tags and "latest"
- The workflow should leverage the existing build script to maintain consistency with local builds

## Progress Updates
2025-04-25: Started task, created branch, moved task to started status
2025-04-25: Created GitHub workflow file for container publishing
2025-04-25: Updated build.sh to accept environment variables for image name and tag
2025-04-25: Added RELEASE.md documentation and updated README.md with release process information
2025-04-25: Fixed Podman configuration in GitHub workflow (using redhat-actions/podman-installer)
2025-04-25: Renamed workflow file to use .yaml extension
2025-04-25: Task completed and merged via PR #25</content>