# Release Process

This document describes the process for releasing new versions of the MCP Server Troubleshoot tool.

## Container Release Process

Container images are automatically built and published to GitHub Container Registry (ghcr.io) when a SemVer tag is pushed to the repository.

### Creating a New Release

1. Ensure all changes for the release are committed and merged to the main branch
2. Create and push a tag with the version number (without a 'v' prefix):

```bash
git checkout main
git pull
git tag 1.0.0  # Replace with the actual version number
git push origin 1.0.0
```

3. The GitHub Actions workflow will automatically:
   - Build the container using the `scripts/build.sh` script
   - Tag the container with both the version number and `latest`
   - Push the container to GitHub Container Registry

4. Verify the container is published to `ghcr.io/[username]/troubleshoot-mcp-server/mcp-server-troubleshoot:<version>`

### Using the Published Container

You can pull and run the container using:

```bash
# Pull the versioned container
podman pull ghcr.io/[username]/troubleshoot-mcp-server/mcp-server-troubleshoot:1.0.0

# Or pull the latest container
podman pull ghcr.io/[username]/troubleshoot-mcp-server/mcp-server-troubleshoot:latest

# Run the container
podman run -it --rm \
  -v $(pwd)/bundles:/data/bundles \
  -e SBCTL_TOKEN=your_token_here \
  ghcr.io/[username]/troubleshoot-mcp-server/mcp-server-troubleshoot:latest
```

## Testing a Release Workflow

For testing purposes, you can manually trigger the workflow from the "Actions" tab in GitHub:

1. Go to "Actions" → "Publish Container" → "Run workflow"
2. Enter a test version (e.g., "test")
3. Click "Run workflow"

This will build and publish a container with the tag `test`, which will not affect the `latest` tag.

## Versioning Guidelines

We follow semantic versioning (SemVer):

- **MAJOR** version for incompatible API changes
- **MINOR** version for backward-compatible functionality additions
- **PATCH** version for backward-compatible bug fixes

Example: `1.0.0`, `1.1.0`, `1.0.1`