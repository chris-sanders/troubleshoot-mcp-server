#!/bin/bash
set -e

# Configuration
IMAGE_NAME="mcp-server-troubleshoot"
IMAGE_TAG="latest"
BUNDLE_DIR="$(pwd)/tests/fixtures"
MCP_MODE=false
INTERACTIVE="-it"
VERBOSE=""

# Parse command-line options
ARGS=""
while [ $# -gt 0 ]; do
  case "$1" in
    --mcp)
      MCP_MODE=true
      # Use -i instead of -it for MCP mode
      INTERACTIVE="-i"
      shift
      ;;
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
if [ "$MCP_MODE" != true ]; then
  echo "Using bundle directory: ${BUNDLE_DIR}"

  # Check if SBCTL_TOKEN is set
  if [ -z "${SBCTL_TOKEN}" ]; then
    echo "Warning: SBCTL_TOKEN is not set. Some operations may fail."
    echo "Set it with: export SBCTL_TOKEN=your_token_here"
  fi
fi

# Run the container
if [ "$MCP_MODE" = true ]; then
  # Run in MCP server mode with direct stdio streaming
  docker run ${INTERACTIVE} --rm \
    -v "${BUNDLE_DIR}:/data/bundles" \
    -e SBCTL_TOKEN="${SBCTL_TOKEN:-}" \
    -e MCP_BUNDLE_STORAGE="/data/bundles" \
    --entrypoint python \
    "${IMAGE_NAME}:${IMAGE_TAG}" -m mcp_server_troubleshoot.cli ${VERBOSE} ${ARGS}
else
  # Run in regular mode
  docker run ${INTERACTIVE} --rm \
    -v "${BUNDLE_DIR}:/data/bundles" \
    -e SBCTL_TOKEN="${SBCTL_TOKEN:-}" \
    -e MCP_BUNDLE_STORAGE="/data/bundles" \
    --entrypoint python \
    "${IMAGE_NAME}:${IMAGE_TAG}" -m mcp_server_troubleshoot ${VERBOSE} ${ARGS}
fi
