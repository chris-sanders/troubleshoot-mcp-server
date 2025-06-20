#!/bin/bash
set -euo pipefail

# Configuration - use environment variables if set, otherwise use defaults
# This allows GitHub Actions to override these values
IMAGE_NAME=${IMAGE_NAME:-"troubleshoot-mcp-server"}
IMAGE_TAG=${IMAGE_TAG:-"latest"}

# Print commands before executing them
set -x

# Build melange package (multi-arch)
podman run --rm -v "$PWD":/work cgr.dev/chainguard/melange build .melange.yaml --arch=amd64,arm64

# Build apko image (multi-arch)
podman run --rm -v "$PWD":/work cgr.dev/chainguard/apko build apko.yaml "${IMAGE_NAME}:${IMAGE_TAG}" "${IMAGE_NAME}.tar" --arch=amd64,arm64

# Load into podman
podman load < "${IMAGE_NAME}.tar"

echo "Build completed successfully. The image is available as ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""
echo "To run the container:"
echo "  podman run -it --rm \\"
echo "    -v \$(pwd)/tests/fixtures:/data/bundles \\"
echo "    -e SBCTL_TOKEN=your_token_here \\"
echo "    ${IMAGE_NAME}:${IMAGE_TAG} [options]"
