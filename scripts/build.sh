#!/bin/bash
set -euo pipefail

# Configuration - use environment variables if set, otherwise use defaults
# This allows GitHub Actions to override these values
IMAGE_NAME=${IMAGE_NAME:-"troubleshoot-mcp-server-dev"}
IMAGE_TAG=${IMAGE_TAG:-"latest"}

# Print commands before executing them
set -x

echo "Building with melange/apko..."

# Determine build configuration based on environment
echo "Building melange package..."

# Default: single-arch production build
ARCH_FLAGS="--arch=amd64"
SIGNING_KEY=""
MELANGE_FLAGS=""
APKO_IGNORE_SIGNATURES=""

# Configure based on build type
if [[ "${MELANGE_TEST_BUILD:-false}" == "true" ]]; then
    echo "🧪 Test build mode: using test keys and ignoring signatures"
    SIGNING_KEY="melange-test.rsa"
    APKO_IGNORE_SIGNATURES="--ignore-signatures"
    
    # Multi-arch only in true CI environment (not when CI=false is forced)
    if [[ "${CI:-false}" == "true" ]]; then
        echo "🏗️  CI detected: building multi-architecture"
        ARCH_FLAGS="--arch=amd64,arm64"
    fi
    
    # Generate test keys if they don't exist
    if [ ! -f "$SIGNING_KEY" ]; then
        echo "Generating test signing keys..."
        ./scripts/generate_test_keys.sh
    fi
elif [ -f melange.rsa ]; then
    echo "🔐 Production build: using production signing key"
    SIGNING_KEY="melange.rsa"
    # Multi-arch for production builds in CI
    if [[ "${CI:-false}" == "true" ]]; then
        ARCH_FLAGS="--arch=amd64,arm64"
    fi
else
    echo "❌ ERROR: No signing configuration available!"
    echo ""
    echo "For testing/development:"
    echo "  export MELANGE_TEST_BUILD=true"
    echo "  ./scripts/build.sh"
    echo ""
    echo "For production builds:"
    echo "  1. Copy your melange.rsa private key to the project root"
    echo "  2. The key should be ignored by git (already in .gitignore)"
    echo "  3. For CI/CD, this key is provided via MELANGE_RSA secret"
    exit 1
fi

if [[ -n "$SIGNING_KEY" ]]; then
    echo "Using signing key: $SIGNING_KEY"
    if ! podman run --rm --privileged --cap-add=SYS_ADMIN -v "$PWD":/work cgr.dev/chainguard/melange build .melange.yaml ${ARCH_FLAGS} ${MELANGE_FLAGS} --signing-key="$SIGNING_KEY"; then
        echo "Melange build failed!"
        exit 1
    fi
else
    echo "Building unsigned package"
    if ! podman run --rm --privileged --cap-add=SYS_ADMIN -v "$PWD":/work cgr.dev/chainguard/melange build .melange.yaml ${ARCH_FLAGS} ${MELANGE_FLAGS}; then
        echo "Melange build failed!"
        exit 1
    fi
fi

echo "Building apko image..."
APKO_FLAGS="${ARCH_FLAGS} ${APKO_IGNORE_SIGNATURES}"

if ! podman run --rm --privileged --cap-add=SYS_ADMIN -v "$PWD":/work cgr.dev/chainguard/apko build apko.yaml "${IMAGE_NAME}:${IMAGE_TAG}" "${IMAGE_NAME}.tar" ${APKO_FLAGS}; then
    echo "Apko build failed!"
    exit 1
fi

echo "Loading image into podman..."
if ! podman load < "${IMAGE_NAME}.tar"; then
    echo "Failed to load apko image!"
    exit 1
fi

# Retag the loaded image to the expected tag (apko adds architecture suffix)
echo "Retagging image for local use..."
LOADED_TAG="${IMAGE_NAME}:${IMAGE_TAG}-amd64"
TARGET_TAG="${IMAGE_NAME}:${IMAGE_TAG}"

# Check if the loaded image exists and retag it
if podman image exists "$LOADED_TAG"; then
    if ! podman tag "$LOADED_TAG" "$TARGET_TAG"; then
        echo "Failed to retag image from $LOADED_TAG to $TARGET_TAG!"
        exit 1
    fi
    echo "Successfully retagged $LOADED_TAG to $TARGET_TAG"
else
    echo "Warning: Expected loaded image $LOADED_TAG not found, checking available images:"
    podman images | grep "$IMAGE_NAME" || echo "No images found with name $IMAGE_NAME"
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
