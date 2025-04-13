#!/bin/bash
set -e

# Configuration
IMAGE_NAME="mcp-server-troubleshoot"
IMAGE_TAG="latest"
BUNDLE_DIR="$(pwd)/tests/fixtures"
INTERACTIVE="-i"  # Default is interactive mode (-i)
VERBOSE=""

# Parse command-line options
ARGS=""
while [ $# -gt 0 ]; do
  case "$1" in
    --verbose)
      VERBOSE="--verbose"
      shift
      ;;
    --bundle-dir=*)
      BUNDLE_DIR="${1#*=}"
      shift
      ;;
    --bundle-dir)
      BUNDLE_DIR="$2"
      shift 2
      ;;
    *)
      if [ -z "$ARGS" ]; then
        ARGS="$1"
      else
        ARGS="$ARGS $1"
      fi
      shift
      ;;
  esac
done

# Create bundle directory if it doesn't exist
mkdir -p "${BUNDLE_DIR}"

# Set log level
LOG_LEVEL="ERROR"
if [ "$VERBOSE" = "--verbose" ]; then
  LOG_LEVEL="DEBUG"
fi

# Create a unique container name
CONTAINER_NAME="mcp-server-$(date +%s)-$RANDOM"

# Run the container in MCP mode
docker run ${INTERACTIVE} --rm \
  -v "${BUNDLE_DIR}:/data/bundles" \
  -e SBCTL_TOKEN="${SBCTL_TOKEN:-}" \
  -e MCP_BUNDLE_STORAGE="/data/bundles" \
  -e MCP_LOG_LEVEL="${LOG_LEVEL}" \
  -e MCP_KEEP_ALIVE="true" \
  --name "$CONTAINER_NAME" \
  "${IMAGE_NAME}:${IMAGE_TAG}" ${VERBOSE} ${ARGS}