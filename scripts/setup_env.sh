#!/bin/bash
# Setup a clean development environment using uv
set -e

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Setting up development environment for MCP Server Troubleshoot"
echo "Project root: $PROJECT_ROOT"

# Parse command line arguments
FORCE_RECREATE=false

function usage() {
  echo "Usage: $0 [options]"
  echo
  echo "Options:"
  echo "  --force-recreate  Force recreation of the virtual environment"
  echo "  --help            Show this help message"
  exit 1
}

for arg in "$@"; do
  case "$arg" in
    --force-recreate)
      FORCE_RECREATE=true
      ;;
    --help)
      usage
      ;;
    *)
      echo "Unknown option: $arg"
      usage
      ;;
  esac
done

# Find the best available Python version (prefer newer versions)
PYTHON_BIN=""
for version in "python3.13" "python3.12" "python3.11" "python3.10"; do
  if command -v $version &> /dev/null; then
    PYTHON_BIN=$(command -v $version)
    break
  fi
done

# Fall back to system Python if no modern version found
if [ -z "$PYTHON_BIN" ]; then
  PYTHON_BIN=$(command -v python3)
fi

# Verify Python version is at least 3.9
PYTHON_VERSION=$($PYTHON_BIN --version | cut -d' ' -f2)
echo "Using Python $PYTHON_VERSION ($PYTHON_BIN)"

# Verify Python version is at least 3.9
if [[ $(echo $PYTHON_VERSION | cut -d. -f1,2 | sed 's/\.//') -lt 39 ]]; then
  echo "Error: Python 3.9 or higher is required. Found $PYTHON_VERSION"
  exit 1
fi

# Set virtual environment path
VENV_DIR="$PROJECT_ROOT/.venv"

# Check if virtual environment exists and handle recreation
if [ -d "$VENV_DIR" ]; then
  if [ "$FORCE_RECREATE" = true ]; then
    echo "Recreating virtual environment..."
    rm -rf "$VENV_DIR"
  else
    echo "Virtual environment already exists at $VENV_DIR"
    echo "To recreate it, use --force-recreate"
  fi
fi

# Create virtual environment if it doesn't exist using uv
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment with uv..."
  cd "$PROJECT_ROOT"
  uv venv -p $PYTHON_BIN .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Install dependencies using uv
cd "$PROJECT_ROOT"
echo "Installing development dependencies..."
uv pip install -e ".[dev]"

# Run test suite to verify setup
echo "Verifying installation by running unit tests..."
python -m pytest -m unit -v

# Show activation command
echo
echo "Development environment setup complete!"
echo "To activate this environment in the future, run:"
echo "source $VENV_DIR/bin/activate"
echo
echo "To run tests:"
echo "pytest"
echo
echo "To run specific test categories:"
echo "pytest -m unit"
echo "pytest -m integration"
echo "pytest -m e2e"