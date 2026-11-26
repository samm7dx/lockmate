"""Tests for json_parser module."""

import pytest
from pathlib import Path
import tempfile
import json

from lockmate.ingestion.parsers.json_parser import JSONParser, NestedJSONParser, JSONParserConfig


class TestJSONParser:
    """Tests for JSONParser."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_single_object(self):
        """Test parsing single JSON object."""
        json_file = self.temp_dir / "test.json"
        json_file.write_text('{"name": "John", "age": 30}', encoding="utf-8")
        
        parser = JSONParser()
        records = list(parser.parse(json_file))
        
        assert len(records) == 1
        assert records[0]["name"] == "John"
        assert records[0]["age"] == 30
    
    def test_array_of_objects(self):
        """Test parsing array of objects yields each item."""
        json_file = self.temp_dir / "array.json"
        json_file.write_text(
            '[{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]',
            encoding="utf-8"
        )
        
        parser = JSONParser()
        records = list(parser.parse(json_file))
        
        assert len(records) == 2
        assert records[0]["id"] == 1
        assert records[0]["_row_number"] == 1
        assert records[1]["id"] == 2
        assert records[1]["_row_number"] == 2
    
    def test_nested_json(self):
        """Test parsing nested JSON structure."""
        json_file = self.temp_dir / "nested.json"
        json_file.write_text(
            '{"name": "John", "address": {"city": "NYC", "zip": "10001"}}',
            encoding="utf-8"
        )
        
        parser = JSONParser()
        records = list(parser.parse(json_file))
        
        assert len(records) == 1
        assert records[0]["address"]["city"] == "NYC"
    
    def test_array_mode_whole(self):
        """Test parsing array as whole."""
        json_file = self.temp_dir / "array.json"
        json_file.write_text(
            '[1, 2, 3]',
            encoding="utf-8"
        )
        
        config = JSONParserConfig(array_mode="whole")
        parser = JSONParser(config)
        records = list(parser.parse(json_file))
        
        assert len(records) == 1
        assert "_array" in records[0]
        assert records[0]["_array"] == [1, 2, 3]
    
    def test_invalid_json(self):
        """Test invalid JSON raises error."""
        json_file = self.temp_dir / "invalid.json"
        json_file.write_text('{"invalid": ', encoding="utf-8")
        
        parser = JSONParser()
        with pytest.raises(Exception):
            list(parser.parse(json_file))
    
    def test_array_of_primitives(self):
        """Test array of primitive values."""
        json_file = self.temp_dir / "primitives.json"
        json_file.write_text('[1, 2, 3]', encoding="utf-8")
        
        parser = JSONParser()
        records = list(parser.parse(json_file))
        
        assert len(records) == 3
        assert records[0]["value"] == 1
        assert records[2]["value"] == 3


class TestNestedJSONParser:
    """Tests for NestedJSONParser."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_flatten_nested_dict(self):
        """Test flattening nested dictionaries."""
        json_file = self.temp_dir / "nested.json"
        json_file.write_text(
            '{"name": "John", "address": {"city": "NYC", "geo": {"lat": 40.7, "lng": -74}}}',
            encoding="utf-8"
        )
        
        parser = NestedJSONParser()
        records = list(parser.parse(json_file))
        
        assert len(records) == 1
        record = records[0]
        assert record["name"] == "John"
        assert record["address.city"] == "NYC"
        assert record["address.geo.lat"] == 40.7
        assert record["address.geo.lng"] == -74
    
    def test_flatten_nested_array(self):
        """Test flattening arrays within objects."""
        json_file = self.temp_dir / "array_nested.json"
        json_file.write_text(
            '{"items": [{"id": 1}, {"id": 2}]}',
            encoding="utf-8"
        )
        
        parser = NestedJSONParser()
        records = list(parser.parse(json_file))
        
        assert len(records) == 1
        record = records[0]
        assert record["items[0].id"] == 1
        assert record["items[1].id"] == 2
    
    def test_flatten_array_of_objects(self):
        """Test flattening array of objects."""
        json_file = self.temp_dir / "array.json"
        json_file.write_text(
            '[{"name": "A", "meta": {"age": 1}}, {"name": "B", "meta": {"age": 2}}]',
            encoding="utf-8"
        )
        
        parser = NestedJSONParser()
        records = list(parser.parse(json_file))
        
        assert len(records) == 2
        assert records[0]["name"] == "A"
        assert records[0]["meta.age"] == 1
        assert records[1]["name"] == "B"
        assert records[1]["meta.age"] == 2
    
    def test_max_depth_truncation(self):
        """Test that deep nesting is truncated."""
        json_file = self.temp_dir / "deep.json"
        
        # Create deeply nested JSON
        depth = 150
        nested = {}
        current = nested
        for i in range(depth):
            current[f"level{i}"] = {}
            current = current[f"level{i}"]
        current["value"] = "deep"
        
        json_file.write_text(json.dumps(nested), encoding="utf-8")
        
        config = JSONParserConfig(max_depth=100)
        parser = NestedJSONParser(config)
        records = list(parser.parse(json_file))
        
        assert len(records) == 1
        assert "_truncated" in records[0] or "level0" in records[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])