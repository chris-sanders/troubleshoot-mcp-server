"""
Pytest configuration and fixtures for integration tests.
"""

import pytest
import pytest_asyncio
from pathlib import Path
import tempfile
from unittest.mock import AsyncMock, Mock, patch

# Import TestAssertions class and fixture from unit tests
from tests.unit.conftest import TestAssertions, test_assertions