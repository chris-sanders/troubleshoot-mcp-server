#!/bin/bash
set -e

# Configuration
IMAGE_NAME="mcp-server-troubleshoot"
IMAGE_TAG="latest"

# Print commands before executing them
set -x

# Build the Podman image (without --no-cache to allow proper layer caching)
podman build -t ${IMAGE_NAME}:${IMAGE_TAG} -f Containerfile .

echo "Build completed successfully. The image is available as ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""
echo "To run the container:"
echo "  podman run -it --rm \\"
echo "    -v \$(pwd)/tests/fixtures:/data/bundles \\"
echo "    -e SBCTL_TOKEN=your_token_here \\"
echo "    ${IMAGE_NAME}:${IMAGE_TAG} [options]"
