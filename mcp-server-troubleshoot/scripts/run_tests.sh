#!/bin/bash
# Script to run tests for the MCP server 

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Activate the virtual environment if it exists
if [ -d "../venv/bin" ]; then
  source "../venv/bin/activate"
fi

# Go to the project root
cd "$PROJECT_ROOT"

# Define usage
function usage() {
  echo "Usage: $0 [test_suite]"
  echo
  echo "Options:"
  echo "  unit        Run unit tests"
  echo "  integration Run integration tests"
  echo "  e2e         Run end-to-end tests"
  echo "  all         Run all tests (default)"
  echo
  echo "Examples:"
  echo "  $0          # Run all tests"
  echo "  $0 unit     # Run only unit tests"
  echo "  $0 e2e      # Run only end-to-end tests"
  exit 1
}

# Parse command-line arguments
TEST_SUITE=${1:-all}

case "$TEST_SUITE" in
  unit)
    echo "Running unit tests..."
    python -m pytest tests/unit/ -v
    ;;
  integration)
    echo "Running integration tests..."
    python -m pytest tests/integration/ -v
    ;;
  e2e)
    echo "Running end-to-end tests..."
    python -m pytest tests/e2e/ -v
    ;;
  all)
    echo "Running all tests..."
    python -m pytest
    ;;
  *)
    echo "Unknown test suite: $TEST_SUITE"
    usage
    ;;
esac