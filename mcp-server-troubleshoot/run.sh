#!/bin/bash
set -e

# Configuration
IMAGE_NAME="mcp-server-troubleshoot"
IMAGE_TAG="latest"
BUNDLE_DIR="$(pwd)/bundles"

# Create bundle directory if it doesn't exist
mkdir -p "${BUNDLE_DIR}"

# Ensure the script handles command-line arguments correctly
ARGS=""
if [ $# -gt 0 ]; then
  ARGS="$@"
fi

# Run the container
docker run -it --rm \
  -v "${BUNDLE_DIR}:/data/bundles" \
  -e SBCTL_TOKEN="${SBCTL_TOKEN:-}" \
  "${IMAGE_NAME}:${IMAGE_TAG}" ${ARGS}