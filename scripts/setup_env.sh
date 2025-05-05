#!/bin/bash
# Setup a clean development environment using UV best practices
# UV manages the environment completely, we don't manually activate it
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

# Verify Python version
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

# Create virtual environment if it doesn't exist using UV
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment with UV..."
  cd "$PROJECT_ROOT"
  
  # Use UV to create venv with specified Python interpreter
  uv venv -p $PYTHON_BIN .venv
fi

# Install dependencies using UV directly (no manual activation needed)
cd "$PROJECT_ROOT"
echo "Installing development dependencies..."
uv pip install -e ".[dev]"

# Run a simple check to verify installation
echo "Verifying installation by running a basic test..."
uv run pytest tests/unit/test_components.py -v

# Show usage information
echo
echo "Development environment setup complete!"
echo
echo "To run commands in this environment use UV:"
echo "uv run pytest                # Run all tests"
echo "uv run pytest -m unit        # Run specific test category" 
echo "uv run ruff check .          # Run linting"
echo "uv run black .               # Format code"
echo "uv run mypy src              # Run type checking"
echo
echo "Note: UV automatically detects and uses the virtual environment"
echo "      at $VENV_DIR - no manual activation needed!"