#!/bin/bash
set -e

# Configuration
IMAGE_NAME="mcp-server-troubleshoot"
IMAGE_TAG="latest"

# Print commands before executing them
set -x

# Build the Docker image
docker build --no-cache -t ${IMAGE_NAME}:${IMAGE_TAG} .

echo "Build completed successfully. The image is available as ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""
echo "To run the container:"
echo "  docker run -it --rm \\"
echo "    -v \$(pwd)/bundles:/data/bundles \\"
echo "    -e SBCTL_TOKEN=your_token_here \\"
echo "    ${IMAGE_NAME}:${IMAGE_TAG} [options]"
