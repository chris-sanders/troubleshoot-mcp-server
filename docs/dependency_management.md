# Dependency Management Guide

This guide outlines the recommended workflow for managing dependencies in the MCP Server Troubleshoot project. Following these practices will ensure consistent environments across feature branches and minimize dependency-related issues during development and testing.

## Recent Improvements

The following improvements have been made to dependency management in this project:

1. **Standardized Python Version**: Using Python 3.10+ (preferably 3.13) for all development and testing
2. **Full UV Integration**: Complete dependency and virtual environment management through UV
3. **Proper Dependency Resolution**: Direct dependency resolution without mocking dependencies
4. **Containerized Consistency**: Updated Docker configuration to use Python 3.13
5. **Docker Build Fix**: Improved Docker build process to handle dependencies correctly with `--system` flag
6. **Test Suite Verification**: All 74 tests now pass consistently, including Docker tests
7. **Improved .dockerignore**: Better exclusion patterns to avoid copying virtual environments

## Environment Setup

### Prerequisites

- Python 3.10 or later (3.13 recommended)
- `uv` - Modern Python package installer and environment manager
  - Install with: `pip install uv` if not already installed

### Setting Up a Development Environment

Use our setup script to create a consistent development environment:

```bash
# Create a fresh environment with latest available Python
./scripts/setup_env.sh

# Force recreation of an existing environment if needed
./scripts/setup_env.sh --force-recreate
```

The script automatically:
1. Finds the best available Python version (3.13, 3.12, 3.11, or 3.10)
2. Creates a virtual environment using UV
3. Installs project dependencies
4. Verifies the installation by running unit tests

### Manual Environment Setup

If you prefer to set up manually:

```bash
# Create a virtual environment with UV using Python 3.13
uv venv -p python3.13 .venv

# Activate the environment
source .venv/bin/activate

# Install development dependencies
uv pip install -e ".[dev]"

# Run tests to verify setup
pytest -m unit
```

## Working with Dependencies

### Adding New Dependencies

When you identify a new dependency requirement during development:

1. **Update `pyproject.toml`**:
   - Add runtime dependencies to the `dependencies` list
   - Add development dependencies to the `[project.optional-dependencies]` section under `dev`

2. **Document the dependency**:
   - Include purpose of the dependency in a comment
   - Specify version constraints if necessary

3. **Reinstall dependencies**:
   ```bash
   uv pip install -e ".[dev]"
   ```

4. **Verify tests pass with the new dependency**:
   ```bash
   pytest
   ```

5. **Commit changes**:
   ```bash
   git add pyproject.toml
   git commit -m "Add dependency: package-name for feature X"
   ```

### Upgrading Dependencies

When upgrading dependencies:

1. **Update version constraints in `pyproject.toml`**
2. **Reinstall with the latest versions**:
   ```bash
   uv pip install -e ".[dev]" --upgrade
   ```
3. **Run all tests to verify compatibility**:
   ```bash
   pytest
   ```

## Testing Workflow

To ensure consistent testing across all environments:

1. **Always start with a clean environment**:
   ```bash
   # Create fresh test environment with UV
   uv venv -p python3.13 test-env
   source test-env/bin/activate
   
   # Install project with test dependencies
   uv pip install -e ".[dev]"
   ```

2. **Run tests**:
   ```bash
   # Run all tests
   pytest
   
   # Run specific test categories
   pytest -m unit
   pytest -m integration
   pytest -m e2e
   
   # Run with coverage
   pytest --cov=src
   ```

3. **Clean up after testing**:
   ```bash
   deactivate
   ```

## Troubleshooting Dependency Issues

If you encounter dependency-related problems:

1. **Recreate the virtual environment**:
   ```bash
   deactivate
   rm -rf .venv
   ./scripts/setup_env.sh --force-recreate
   ```

2. **Check for conflicts**:
   ```bash
   uv pip check
   ```

3. **Verify installed packages**:
   ```bash
   uv pip list
   ```

4. **Common issues and solutions**:
   - **ImportError or ModuleNotFoundError**: A dependency might be missing - verify it's listed in `pyproject.toml` and reinstall with `uv pip install -e ".[dev]"`
   - **Version conflicts**: Check version constraints in `pyproject.toml` and adjust if necessary
   - **Python version compatibility**: Ensure you're using Python 3.10+ (preferably 3.13)
   - **Tests failing in CI but passing locally**: Ensure CI environment has all necessary dependencies and is using the correct Python version

## Docker Development

The project uses a multi-stage Docker build with Python 3.13. The container uses UV for dependency management with the `--system` flag to avoid virtual environment issues.

When working with Docker:

1. **Build the container**:
   ```bash
   ./scripts/build.sh
   ```

2. **Test within the container**:
   ```bash
   docker run -it --rm mcp-server-troubleshoot:latest python -m pytest
   ```

3. **When adding dependencies, rebuild the container**:
   ```bash
   ./scripts/build.sh --no-cache
   ```

### Docker Build Considerations

- The `.dockerignore` file excludes virtual environments and other development artifacts
- The `--system` flag with UV pip ensures dependencies are installed to the system Python path
- The multi-stage build reduces the final image size by only including necessary runtime dependencies
- Container tests are run as part of the standard test suite to ensure image functionality

## Best Practices

- **Use modern Python**: Always use Python 3.10 or later (preferably 3.13)
- **Manage environments with UV**: Use UV for both package and virtual environment management
- **Minimize dependencies**: Only add dependencies that are truly necessary
- **Use specific versions**: Pin versions to avoid unexpected upgrades
- **Document requirements**: Add comments for non-obvious dependencies
- **Test all dependency changes**: Run the full test suite after adding or upgrading dependencies
- **Keep CI configuration in sync**: Update CI workflows when changing dependencies
- **Verify full test suite**: Always run the complete test suite before committing changes

By following these guidelines, the team can maintain consistent environments across feature branches and minimize dependency-related issues during development and testing.