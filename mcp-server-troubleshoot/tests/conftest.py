"""
Test configuration and fixtures for pytest.
"""

import os
import pytest
from pathlib import Path


@pytest.fixture
def fixtures_dir() -> Path:
    """
    Returns the path to the test fixtures directory.
    
    This is a standardized location for test data files.
    """
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def test_support_bundle(fixtures_dir) -> Path:
    """
    Returns the path to the test support bundle file.
    
    This fixture ensures the support bundle exists before returning it.
    """
    bundle_path = fixtures_dir / "support-bundle-2025-04-11T14_05_31.tar.gz"
    assert bundle_path.exists(), f"Support bundle not found at {bundle_path}"
    return bundle_path