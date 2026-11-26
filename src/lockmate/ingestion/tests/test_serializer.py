"""Tests for serializer module."""

import pytest
from pathlib import Path
import tempfile
import json

from lockmate.ingestion.output.serializer import OutputSerializer, SerializerConfig, serialize_to_json, serialize_to_jsonl


class TestOutputSerializer:
    """Tests for OutputSerializer."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_serialize_json(self):
        """Test JSON serialization."""
        records = iter([
            {"name": "John", "age": 30},
            {"name": "Jane", "age": 25},
        ])
        
        output_path = self.temp_dir / "output.json"
        serializer = OutputSerializer()
        count = serializer.serialize_json(records, output_path)
        
        assert count == 2
        assert output_path.exists()
        
        data = json.loads(output_path.read_text())
        assert len(data) == 2
        assert data[0]["name"] == "John"
    
    def test_serialize_jsonl(self):
        """Test JSONL serialization."""
        records = iter([
            {"name": "John", "age": 30},
            {"name": "Jane", "age": 25},
        ])
        
        output_path = self.temp_dir / "output.jsonl"
        serializer = OutputSerializer()
        count = serializer.serialize_jsonl(records, output_path)
        
        assert count == 2
        assert output_path.exists()
        
        lines = output_path.read_text().strip().split("\n")
        assert len(lines) == 2
        
        data = [json.loads(line) for line in lines]
        assert data[0]["name"] == "John"
        assert data[1]["name"] == "Jane"
    
    def test_sanitize_internal_fields(self):
        """Test that internal fields (prefixed with _) are removed."""
        records = iter([
            {"name": "John", "_row_number": 1, "_internal": "secret"},
        ])
        
        output_path = self.temp_dir / "output.jsonl"
        serializer = OutputSerializer()
        serializer.serialize_jsonl(records, output_path)
        
        lines = output_path.read_text().strip().split("\n")
        data = json.loads(lines[0])
        
        assert "name" in data
        assert "_row_number" not in data
        assert "_internal" not in data
    
    def test_exclude_none(self):
        """Test excluding None values."""
        records = iter([
            {"name": "John", "email": None, "age": 30},
        ])
        
        output_path = self.temp_dir / "output.json"
        config = SerializerConfig(exclude_none=True)
        serializer = OutputSerializer(config)
        serializer.serialize_json(records, output_path)
        
        data = json.loads(output_path.read_text())
        assert "email" not in data[0]
        assert data[0]["name"] == "John"
    
    def test_convenience_functions(self):
        """Test convenience functions."""
        records = iter([{"a": 1}, {"a": 2}])
        
        output_path = self.temp_dir / "convenience.jsonl"
        count = serialize_to_jsonl(records, output_path)
        
        assert count == 2
        assert output_path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])