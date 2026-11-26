"""Pytest fixtures for ingestion tests."""

import pytest
from pathlib import Path
import tempfile
import sys

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)