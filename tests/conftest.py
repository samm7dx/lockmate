"""
LOCKMATE — Pytest Configuration
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for tests."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_csv_file(tmp_path):
    """Create a sample CSV file for testing."""
    file_path = Path(tmp_path) / "sample.csv"
    file_path.write_text("id,name,value\n1,Alice,100\n2,Bob,200\n3,Charlie,300\n")
    return file_path


@pytest.fixture
def sample_json_file(tmp_path):
    """Create a sample JSON file for testing."""
    file_path = Path(tmp_path) / "sample.json"
    file_path.write_text('[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]')
    return file_path


@pytest.fixture
def sample_jsonl_file(tmp_path):
    """Create a sample JSONL file for testing."""
    file_path = Path(tmp_path) / "sample.jsonl"
    file_path.write_text('{"id": 1, "name": "Alice"}\n{"id": 2, "name": "Bob"}\n')
    return file_path


@pytest.fixture
def sample_text_file(tmp_path):
    """Create a sample text file for testing."""
    file_path = Path(tmp_path) / "sample.txt"
    file_path.write_text("Line 1\nLine 2\nLine 3\n")
    return file_path