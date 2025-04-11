# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Important
- ALWAYS read `docs/agentic/ai-readme.md` first to understand the task workflow
- Follow the structured workflow in `/docs/` for tasks, PRs, and code reviews
- Understand system architecture from `docs/architecture.md` before coding

## Build & Test Commands
- Install dependencies: `uv pip install -e .`
- Run tests: `pytest`
- Run single test: `pytest path/to/test.py::TestClass::test_function -v`
- Lint code: `ruff check .`
- Format code: `black .`

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