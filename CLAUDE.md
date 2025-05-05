# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Important
- ALWAYS read both READMEs in the root directory and in the mcp-server-troubleshoot folder to understand the project
- ALWAYS read `docs/agentic/ai-readme.md` first to understand the task workflow
- Follow the structured workflow in `/docs/` for tasks, PRs, and code reviews
- Understand system architecture from `docs/architecture.md` before coding

## Development Environment Setup
- Setup dev environment: `./scripts/setup_env.sh`
- Create virtual environment manually (if needed): `uv venv -p python3.13 .venv`
- Install dependencies: `uv pip install -e ".[dev]"`

## Testing Commands
- Run all tests: `uv run pytest`
- Run test categories: `uv run pytest -m unit`, `uv run pytest -m integration`, `uv run pytest -m e2e`
- Run single test: `uv run pytest tests/unit/test_bundle.py -v`
- Run with coverage: `uv run pytest --cov=src`
- Run tests with helper script: `./scripts/run_tests.sh [test_type]`

## Code Quality Commands
- Lint code: `uv run ruff check .`
- Format code: `uv run black .`
- Type check: `uv run mypy src`

## Code Style Guidelines
- Python: Follow PEP 8 and use type annotations
- Imports: Group standard lib, third-party, then local imports
- Naming: snake_case for functions/variables, CamelCase for classes
- Error handling: Use specific exceptions, provide context messages
- Use f-strings for string formatting
- 100 character line length maximum
- Document public interfaces with docstrings
- Write atomic, focused unit tests with pytest
- Use the MCP protocol standard for handler implementations

## Task Workflow
- Tasks flow through: ready → started → review → completed
- Move task files between corresponding directories as they progress
- Create branches with pattern: `task/[task-filename-without-extension]`
- Commit messages: Start with present-tense verb, be descriptive
- When completing tasks, update all metadata and move to correct folder

## UV Best Practices
- Always use `uv run` to execute commands in the virtual environment
- No need to manually activate the virtual environment
- Use `uv pip` for dependency management
- UV automatically detects the virtual environment in .venv