#!/bin/bash
set -e

# Configuration
IMAGE_NAME="mcp-server-troubleshoot"
IMAGE_TAG="latest"
BUNDLE_DIR="$(pwd)/tests/fixtures"
MCP_MODE=false
INTERACTIVE="-it"
VERBOSE=""
DEBUG_MODE=false

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
    --debug)
      DEBUG_MODE=true
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
  # ABSOLUTELY CRITICAL: In MCP mode, the ONLY thing that should be written to stdout
  # is JSON-RPC messages. Any other stdout will break the protocol.
  # No echo statements here, logs must go to stderr or be suppressed.
  
  # Set log level based on debug mode
  LOG_LEVEL="ERROR"
  if [ "$DEBUG_MODE" = true ]; then
    LOG_LEVEL="DEBUG"
    # Don't echo to stdout here - use stderr
    >&2 echo "Running in DEBUG mode, logs going to stderr"
  fi
  
  # Create a unique container name
  CONTAINER_NAME="mcp-server-$(date +%s)-$RANDOM"
  
  # Only print to stderr, never stdout in MCP mode
  >&2 echo "Starting MCP server in container: $CONTAINER_NAME"
  >&2 echo "Using bundle directory: $BUNDLE_DIR"
  
  # IMPORTANT: Use -i flag, not -it for MCP mode
  # Redirect stderr to file descriptor 2 (stderr) instead of discarding it
  cat | docker run -i \
    -v "${BUNDLE_DIR}:/data/bundles" \
    -e SBCTL_TOKEN="${SBCTL_TOKEN:-}" \
    -e MCP_BUNDLE_STORAGE="/data/bundles" \
    -e MCP_LOG_LEVEL="${LOG_LEVEL}" \
    -e MCP_KEEP_ALIVE="true" \
    --rm \
    --name "$CONTAINER_NAME" \
    --entrypoint python \
    "${IMAGE_NAME}:${IMAGE_TAG}" -u -m mcp_server_troubleshoot.cli ${VERBOSE} ${ARGS} 2>&2
else
  # Run in regular mode
  docker run ${INTERACTIVE} --rm \
    -v "${BUNDLE_DIR}:/data/bundles" \
    -e SBCTL_TOKEN="${SBCTL_TOKEN:-}" \
    -e MCP_BUNDLE_STORAGE="/data/bundles" \
    --entrypoint python \
    "${IMAGE_NAME}:${IMAGE_TAG}" -u -m mcp_server_troubleshoot ${VERBOSE} ${ARGS}
fi
