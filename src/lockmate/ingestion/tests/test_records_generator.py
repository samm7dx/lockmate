"""Tests for records_generator module."""

import pytest
from pathlib import Path
import tempfile
import json

from lockmate.ingestion.output.records_generator import RecordsGenerator, RecordsConfig


class TestRecordsGenerator:
    """Tests for RecordsGenerator."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.output_dir = self.temp_dir / "output"
        self.generator = RecordsGenerator(RecordsConfig(output_dir=self.output_dir))
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_write_records(self):
        """Test writing records to JSONL."""
        records = iter([
            {"name": "John", "age": 30},
            {"name": "Jane", "age": 25},
        ])
        
        result = self.generator.write_records(records, filename="records.jsonl")
        
        assert result["records_written"] == 2
        assert result["files_created"] == 1
        
        output_path = self.output_dir / "records.jsonl"
        assert output_path.exists()
        
        lines = output_path.read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["name"] == "John"
        assert json.loads(lines[1])["name"] == "Jane"
    
    def test_write_records_default_filename(self):
        """Test writing records with default filename."""
        records = iter([{"a": 1}])
        
        result = self.generator.write_records(records)
        
        assert result["records_written"] == 1
        assert (self.output_dir / "records.jsonl").exists()
    
    def test_sharded_records(self):
        """Test writing records to sharded files."""
        # Create 10 records
        records = iter([
            {"id": i, "value": f"value{i}"} for i in range(10)
        ])
        
        config = RecordsConfig(
            output_dir=self.output_dir,
            max_records_per_file=3
        )
        generator = RecordsGenerator(config)
        
        result = generator.write_records(records, filename="sharded.jsonl")
        
        assert result["records_written"] == 10
        assert result["files_created"] == 4  # 10 / 3 = 4 shards
        
        # Verify shards exist
        shard_files = list(self.output_dir.glob("sharded_part*.jsonl"))
        assert len(shard_files) == 4
        
        # Verify total records in shards
        total = 0
        for shard in shard_files:
            lines = shard.read_text().strip().split("\n")
            total += len([l for l in lines if l])
        assert total == 10
    
    def test_sanitize_internal_fields(self):
        """Test that internal fields are removed."""
        records = iter([
            {"name": "John", "_row_number": 1, "_internal": "secret"},
        ])
        
        self.generator.write_records(records, filename="test.jsonl")
        
        output_path = self.output_dir / "test.jsonl"
        data = json.loads(output_path.read_text().strip())
        
        assert "name" in data
        assert "_row_number" not in data
        assert "_internal" not in data
    
    def test_append_records(self):
        """Test appending records to existing file."""
        # Write initial records
        initial = iter([{"id": 1}, {"id": 2}])
        self.generator.write_records(initial, filename="test.jsonl")
        
        # Append more
        more = iter([{"id": 3}])
        appended = self.generator.append_records(more, filename="test.jsonl")
        
        assert appended == 1
        
        output_path = self.output_dir / "test.jsonl"
        lines = output_path.read_text().strip().split("\n")
        assert len(lines) == 3
        assert json.loads(lines[2])["id"] == 3
    
    def test_empty_records(self):
        """Test writing empty records."""
        records = iter([])
        
        result = self.generator.write_records(records, filename="empty.jsonl")
        
        assert result["records_written"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])