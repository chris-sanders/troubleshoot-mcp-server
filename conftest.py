"""
Global pytest configuration.
"""
import warnings
import pytest
from pytest_asyncio.plugin import PytestDeprecationWarning

# Filter out common warnings that don't affect test functionality
warnings.filterwarnings("ignore", category=PytestDeprecationWarning)
warnings.filterwarnings("ignore", category=pytest.PytestUnraisableExceptionWarning)
warnings.filterwarnings("ignore", message="Event loop is closed")