"""
Custom plugin for pytest-asyncio to programmatically configure options.

This plugin is loaded via entry_points in pyproject.toml to ensure
it's available before pytest-asyncio plugin initializes.
"""
import pytest


def pytest_addoption(parser):
    """Add options for pytest-asyncio configuration."""
    asyncio_group = parser.getgroup("asyncio")
    asyncio_group.addoption(
        "--asyncio-fixture-loop-scope",
        dest="asyncio_default_fixture_loop_scope",
        default="function",
        help="Default event loop scope for asyncio fixtures",
    )
    asyncio_group.addoption(
        "--asyncio-test-loop-scope",
        dest="asyncio_default_test_loop_scope",
        default="function",
        help="Default event loop scope for asyncio test functions",
    )


def pytest_configure(config):
    """Configure pytest-asyncio options programmatically."""
    # Set or override pytest-asyncio options
    config.option.asyncio_mode = "strict"
    config.option.asyncio_default_fixture_loop_scope = "function"
    config.option.asyncio_default_test_loop_scope = "function"