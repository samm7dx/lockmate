"""Tests for quarantine module."""

import pytest
from pathlib import Path
import tempfile
import json

from lockmate.ingestion.validation.quarantine import QuarantineManager, QuarantineConfig, QuarantineEntry


class TestQuarantineManager:
    """Tests for QuarantineManager."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.quarantine_dir = self.temp_dir / "quarantine"
        
        config = QuarantineConfig(
            quarantine_path=self.quarantine_dir,
            compress=False
        )
        self.manager = QuarantineManager(config)
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_quarantine_file(self):
        """Test quarantining a file."""
        # Create file to quarantine
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("malformed content")
        
        entry = self.manager.quarantine(test_file, reason="test_reason")
        
        # File should be moved to quarantine
        assert not test_file.exists()
        
        # Entry metadata should be correct
        assert entry.original_name == "test.txt"
        assert entry.reason == "test_reason"
        assert Path(entry.quarantine_path).exists()
        assert Path(entry.quarantine_path).name != "test.txt"  # Renamed with UUID
    
    def test_metadata_written(self):
        """Test that metadata is written to JSONL."""
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("malformed")
        
        self.manager.quarantine(test_file, reason="test_reason")
        
        # Metadata file should exist
        assert self.manager.metadata_file.exists()
        
        # Should contain one entry
        entries = self.manager.list_entries()
        assert len(entries) == 1
        assert entries[0].reason == "test_reason"
    
    def test_multiple_quarantines(self):
        """Test multiple quarantined files."""
        for i in range(3):
            test_file = self.temp_dir / f"test_{i}.txt"
            test_file.write_text(f"content {i}")
            self.manager.quarantine(test_file, reason=f"reason_{i}")
        
        entries = self.manager.list_entries()
        assert len(entries) == 3
    
    def test_restore(self):
        """Test restoring a quarantined file."""
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("content")
        
        entry = self.manager.quarantine(test_file, reason="test")
        
        # Restore to original location
        dest = self.temp_dir / "restored.txt"
        result = self.manager.restore(entry.id, dest)
        
        assert result is True
        assert dest.exists()
        assert dest.read_text() == "content"
        
        # Entry should be removed
        assert len(self.manager.list_entries()) == 0
    
    def test_restore_nonexistent(self):
        """Test restoring nonexistent entry."""
        import uuid
        result = self.manager.restore(uuid.uuid4(), self.temp_dir / "test.txt")
        assert result is False
    
    def test_delete(self):
        """Test deleting a quarantined file."""
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("content")
        
        entry = self.manager.quarantine(test_file, reason="test")
        
        result = self.manager.delete(entry.id)
        
        assert result is True
        assert len(self.manager.list_entries()) == 0
    
    def test_get_entry(self):
        """Test getting a specific entry."""
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("content")
        
        entry = self.manager.quarantine(test_file, reason="test")
        
        found = self.manager.get_entry(entry.id)
        assert found is not None
        assert found.id == entry.id
    
    def test_quarantine_size_limit(self):
        """Test quarantine size limit."""
        config = QuarantineConfig(
            quarantine_path=self.quarantine_dir,
            max_quarantine_size=200  # Allow two 100-byte files
        )
        manager = QuarantineManager(config)
        
        # Create files
        test_file = self.temp_dir / "large.txt"
        test_file.write_text("x" * 100)
        
        # First quarantine OK
        manager.quarantine(test_file, reason="test")
        
        # Second should also fit
        test_file2 = self.temp_dir / "large2.txt"
        test_file2.write_text("y" * 100)
        manager.quarantine(test_file2, reason="test")
        
        # Third should fail (size limit exceeded)
        test_file3 = self.temp_dir / "large3.txt"
        test_file3.write_text("z" * 100)
        
        with pytest.raises(RuntimeError, match="Quarantine size limit"):
            manager.quarantine(test_file3, reason="test")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])