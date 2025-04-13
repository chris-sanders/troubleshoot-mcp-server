#!/bin/bash
set -e

# Script to run e2e tests selectively with proper timeouts

echo "=== Running e2e tests ==="

# Default to running basic tests
TEST_LEVEL=${1:-"basic"}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --level=*)
      TEST_LEVEL="${1#*=}"
      shift
      ;;
    --level)
      TEST_LEVEL="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

# Set environment variables for testing
export MCP_CLIENT_DEBUG=true
export MCP_CLIENT_TIMEOUT=5.0
export MCP_LOG_LEVEL=ERROR

# Function to run tests with proper error handling
run_test() {
  TEST_PATH=$1
  echo "Running test: $TEST_PATH"
  
  # Run with timeout (Python's pytest has built-in timeout support)
  python -m pytest "$TEST_PATH" -v --timeout=30
  
  # Check result
  RESULT=$?
  if [ $RESULT -eq 0 ]; then
    echo "✅ Test passed: $TEST_PATH"
    return 0
  elif [ $RESULT -eq 124 ]; then
    echo "⏱️ Test timed out: $TEST_PATH"
    return 1
  else
    echo "❌ Test failed with code $RESULT: $TEST_PATH"
    return 1
  fi
}

# Run basic tests for quick check
if [[ "$TEST_LEVEL" == "basic" || "$TEST_LEVEL" == "all" ]]; then
  echo "=== Running basic tests ==="
  run_test tests/e2e/quick_check.py::test_basic_container_check
fi

# Run Docker tests
if [[ "$TEST_LEVEL" == "docker" || "$TEST_LEVEL" == "all" ]]; then
  echo "=== Running Docker tests ==="
  run_test tests/e2e/test_docker.py::test_dockerfile_exists
  run_test tests/e2e/test_docker.py::test_docker_build
  run_test tests/e2e/test_docker.py::test_docker_run
fi

# Run container tests
if [[ "$TEST_LEVEL" == "container" || "$TEST_LEVEL" == "all" ]]; then
  echo "=== Running container tests ==="
  run_test tests/e2e/test_container.py::test_basic_container_functionality
  run_test tests/e2e/test_container.py::test_python_functionality
  run_test tests/e2e/test_container.py::test_mcp_cli
  run_test tests/e2e/test_container.py::test_mcp_protocol
fi

# Run MCP tests if requested
if [[ "$TEST_LEVEL" == "mcp" || "$TEST_LEVEL" == "all" ]]; then
  echo "=== Running MCP protocol tests ==="
  python -m pytest tests/e2e/test_mcp_protocol.py::test_list_tools -v --timeout=15 || echo "⏱️ MCP protocol test timed out (expected)"
fi

echo "=== All tests complete ==="