"""
Custom plugin for pytest-asyncio to programmatically configure options.

This plugin is loaded via entry_points in pyproject.toml to ensure
it's available before pytest-asyncio plugin initializes.
"""


def pytest_configure(config):
    """Configure pytest-asyncio options programmatically."""
    # Set or override pytest-asyncio options
    config.option.asyncio_mode = "strict"
    config.option.asyncio_default_fixture_loop_scope = "function"
    config.option.asyncio_default_test_loop_scope = "function"
