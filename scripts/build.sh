#!/bin/bash
set -euo pipefail

# Configuration - use environment variables if set, otherwise use defaults
# This allows GitHub Actions to override these values
IMAGE_NAME=${IMAGE_NAME:-"troubleshoot-mcp-server"}
IMAGE_TAG=${IMAGE_TAG:-"latest"}

# Print commands before executing them
set -x

echo "Building with melange/apko..."

# Build melange package (single arch for local development, multi-arch for CI)
ARCH_FLAGS="--arch=amd64"
if [[ "${CI:-false}" == "true" ]]; then
    ARCH_FLAGS="--arch=amd64,arm64"
fi

echo "Building melange package..."
# Check if signing key exists, create instructions if not
if [ ! -f melange.rsa ]; then
    echo "ERROR: melange.rsa signing key not found!"
    echo "For local development:"
    echo "  1. Copy your melange.rsa private key to the project root"
    echo "  2. The key should be ignored by git (already in .gitignore)"
    echo "For CI/CD, this key is provided via MELANGE_RSA secret"
    exit 1
fi

if ! podman run --rm --privileged --cap-add=SYS_ADMIN -v "$PWD":/work cgr.dev/chainguard/melange build .melange.yaml ${ARCH_FLAGS} --signing-key=melange.rsa; then
    echo "Melange build failed!"
    exit 1
fi

echo "Building apko image..."
if ! podman run --rm --privileged --cap-add=SYS_ADMIN -v "$PWD":/work cgr.dev/chainguard/apko build apko.yaml "${IMAGE_NAME}:${IMAGE_TAG}" "${IMAGE_NAME}.tar" ${ARCH_FLAGS}; then
    echo "Apko build failed!"
    exit 1
fi

echo "Loading image into podman..."
if ! podman load < "${IMAGE_NAME}.tar"; then
    echo "Failed to load apko image!"
    exit 1
fi

echo "✅ Melange/apko build completed successfully!"
echo "📦 Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "🔧 Includes: sbctl v0.17.2, kubectl v1.33, Python MCP server"
echo ""
echo "To run the container:"
echo "  podman run -it --rm \\"
echo "    -v \$(pwd)/tests/fixtures:/data/bundles \\"
echo "    -e SBCTL_TOKEN=your_token_here \\"
echo "    ${IMAGE_NAME}:${IMAGE_TAG} [options]"
