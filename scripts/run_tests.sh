#!/bin/bash
# Simple script to run tests for the MCP server with proper markers
set -e

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Activate the virtual environment if it exists
if [ -d "$PROJECT_ROOT/venv/bin" ]; then
  source "$PROJECT_ROOT/venv/bin/activate"
fi

# Go to the project root
cd "$PROJECT_ROOT"

# Define usage
function usage() {
  echo "Usage: $0 [test_type] [options]"
  echo
  echo "Test Types:"
  echo "  unit         Run unit tests                          (pytest -m unit)"
  echo "  integration  Run integration tests                   (pytest -m integration)"
  echo "  e2e          Run end-to-end tests                    (pytest -m e2e)"
  echo "  quick        Run quick verification tests            (pytest -m quick)"
  echo "  docker       Run tests that need Docker              (pytest -m docker)"
  echo "  all          Run all tests (default)                 (pytest)"
  echo
  echo "Options:"
  echo "  -v, --verbose     Run with verbose output            (pytest -v)"
  echo "  --no-timeout      Disable test timeouts              (pytest --timeout 0)"
  echo "  --mock-sbctl      Use mock sbctl for tests           (USE_MOCK_SBCTL=true)" 
  echo "  --                Pass remaining options to pytest   (pytest ...)"
  echo
  echo "Examples:"
  echo "  $0                   # Run all tests"
  echo "  $0 unit              # Run only unit tests"
  echo "  $0 e2e -v            # Run e2e tests with verbose output"
  echo "  $0 quick --mock-sbctl # Run quick tests with mock sbctl"
  echo "  $0 docker -- -k \"container\"  # Run Docker tests matching 'container'"
  exit 1
}

# Default options
VERBOSE=""
TIMEOUT=""
MOCK_SBCTL=""
TEST_TYPE=${1:-all}
shift_index=0

# Parse command-line arguments that we handle
for arg in "$@"; do
  shift_index=$((shift_index + 1))
  
  case "$arg" in
    -v|--verbose)
      VERBOSE="-v"
      ;;
    --no-timeout)
      TIMEOUT="--timeout 0"
      ;;
    --mock-sbctl)
      MOCK_SBCTL="USE_MOCK_SBCTL=true"
      ;;
    --)
      # Stop parsing our args
      break
      ;;
    --help)
      usage
      ;;
  esac
done

# Remove the arguments we've processed
shift $shift_index

# Determine pytest marker based on test type
case "$TEST_TYPE" in
  unit)
    MARKER="-m unit"
    ;;
  integration)
    MARKER="-m integration"
    ;;
  e2e)
    MARKER="-m e2e"
    ;;
  quick)
    MARKER="-m quick"
    ;;
  docker)
    MARKER="-m docker"
    ;;
  all)
    MARKER=""
    ;;
  --help)
    usage
    ;;
  *)
    echo "Unknown test type: $TEST_TYPE"
    usage
    ;;
esac

# Run the tests
echo "Running tests: $TEST_TYPE"
$MOCK_SBCTL python -m pytest $MARKER $VERBOSE $TIMEOUT "$@"