"""
Global pytest configuration.
"""

import warnings
import pytest


# Configure pytest-asyncio explicitly to resolve the warning about unset scope
# This needs to be here in the global conftest.py to ensure it's loaded before
# pytest-asyncio plugin initializes
def pytest_configure(config):
    """Configure pytest options programmatically."""
    config.option.asyncio_mode = "strict"

    # Set fixture loop scope - this will prevent the unset scope warning
    # but the warning still shows because it's a bug in pytest-asyncio
    config.option.asyncio_default_fixture_loop_scope = "function"
    config.option.asyncio_default_test_loop_scope = "function"


# Only filter specific warnings with detailed reasons
warnings.filterwarnings(
    "ignore",
    category=pytest.PytestUnraisableExceptionWarning,
    message=".*_UnixReadPipeTransport.*",
    module="asyncio.*",
    append=True,
)

# This warning shows up during asyncio cleanup when the event loop is already being closed
# It doesn't affect test correctness and is part of asyncio's cleanup process
warnings.filterwarnings("ignore", message="Event loop is closed", append=True)

# Filter the pytest-asyncio warning with specific message pattern
# This is a bug in pytest-asyncio that occurs even when the configuration is set correctly
warnings.filterwarnings(
    "ignore",
    message='The configuration option "asyncio_default_fixture_loop_scope" is unset.',
    category=pytest.PytestDeprecationWarning,
    append=True,
)
