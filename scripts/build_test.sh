#!/bin/bash
set -e

# Configuration
IMAGE_NAME="mcp-server-troubleshoot"
IMAGE_TAG="latest"

# Print commands before executing them
set -x

# Build the Docker image using the test Dockerfile
docker build -f Dockerfile.test -t ${IMAGE_NAME}:${IMAGE_TAG} .

echo "Build completed successfully. The test image is available as ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""
echo "This test image uses a mock sbctl implementation for testing."
echo ""
echo "To run the container:"
echo "  docker run -it --rm \\"
echo "    -v \$(pwd)/tests/fixtures:/data/bundles \\"
echo "    -e SBCTL_TOKEN=your_token_here \\"
echo "    ${IMAGE_NAME}:${IMAGE_TAG} [options]"