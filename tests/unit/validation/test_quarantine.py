"""
LOCKMATE — Quarantine Manager Tests

Tests for QuarantineManager and QuarantineEntry.
"""

import pytest
import json
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory

from secret_wards.validation import QuarantineManager, QuarantineConfig, QuarantineEntry


class TestQuarantineEntry:
    """Test QuarantineEntry dataclass."""
    
    def test_creation(self):
        """Test QuarantineEntry creation."""
        entry = QuarantineEntry(
            original_path="/input/test.csv",
            original_name="test.csv",
            quarantine_path="/output/quarantine/abc123.csv",
            reason="parse_error",
            file_size=1024,
            mime_type="text/csv",
            details={"error": "Malformed CSV"}
        )
        
        assert entry.original_path == "/input/test.csv"
        assert entry.original_name == "test.csv"
        assert entry.reason == "parse_error"
        assert entry.file_size == 1024
        assert entry.mime_type == "text/csv"
        assert entry.details == {"error": "Malformed CSV"}
        assert isinstance(entry.id, uuid.UUID)
        assert entry.timestamp is not None
    
    def test_serialization_roundtrip(self):
        """Test JSON serialization roundtrip."""
        entry = QuarantineEntry(
            original_path="/input/test.csv",
            original_name="test.csv",
            quarantine_path="/output/quarantine/abc123.csv",
            reason="parse_error",
            file_size=1024,
            mime_type="text/csv",
            details={"error": "Malformed CSV", "line": 42}
        )
        
        data = entry.to_dict()
        restored = QuarantineEntry.from_dict(data)
        
        assert restored.original_path == entry.original_path
        assert restored.original_name == entry.original_name
        assert restored.quarantine_path == entry.quarantine_path
        assert restored.reason == entry.reason
        assert restored.id == entry.id
        assert restored.timestamp == entry.timestamp
        assert restored.file_size == entry.file_size
        assert restored.mime_type == entry.mime_type
        assert restored.details == entry.details


class TestQuarantineManager:
    """Test QuarantineManager functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.quarantine_dir = self.temp_path / "quarantine"
        self.input_dir = self.temp_path / "input"
        self.input_dir.mkdir()
        
        self.config = QuarantineConfig(quarantine_path=self.quarantine_dir)
        self.manager = QuarantineManager(config=self.config)
    
    def teardown_method(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()
    
    def test_quarantine_file(self):
        """Test quarantining a file."""
        # Create test file
        test_file = Path(self.temp_path) / "input" / "test.csv"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("id,name\n1,test\n")
        
        # Quarantine it
        entry = self.manager.quarantine(
            file_path=Path(self.temp_path) / "input" / "test.csv",
            reason="parse_error",
            mime_type="text/csv",
            details={"line": 2, "error": "malformed"}
        )
        
        # Check entry
        assert entry.reason == "parse_error"
        assert entry.mime_type == "text/csv"
        assert entry.file_size > 0
        assert entry.original_name == "test.csv"
        assert entry.quarantine_path.startswith(str(self.quarantine_dir))
        assert entry.details == {"line": 2, "error": "malformed"}
        
        # Check file was moved
        quarantine_file = Path(entry.quarantine_path)
        assert quarantine_file.exists()
        assert not (Path(self.temp_path) / "input" / "test.csv").exists()
        
        # Check metadata file
        metadata_file = self.quarantine_dir / "metadata.jsonl"
        assert metadata_file.exists()
    
    def test_metadata_persistence(self):
        """Test that quarantine metadata persists across manager instances."""
        # Create and quarantine a file
        test_file = Path(self.temp_path) / "input" / "test.csv"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("id,value\n1,100\n")
        
        entry = self.manager.quarantine(
            file_path=Path(self.temp_path) / "input" / "test.csv",
            reason="test",
            details={"test": True}
        )
        
        # Create new manager instance
        new_manager = QuarantineManager(config=self.config)
        
        # Check entry is listed
        entries = new_manager.list_entries()
        assert len(entries) == 1
        assert entries[0].id == entry.id
        assert entries[0].reason == "test"
        assert entries[0].details == {"test": True}
    
    def test_get_entry(self):
        """Test retrieving a specific entry by ID."""
        test_file = Path(self.temp_path) / "input" / "test.csv"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("test")
        
        entry = self.manager.quarantine(
            file_path=Path(self.temp_path) / "input" / "test.csv",
            reason="test"
        )
        
        # Get entry by ID
        retrieved = self.manager.get_entry(entry.id)
        assert retrieved is not None
        assert retrieved.id == entry.id
        
        # Non-existent ID
        assert self.manager.get_entry(uuid.uuid4()) is None
    
    def test_restore_file(self):
        """Test restoring a quarantined file."""
        test_file = Path(self.temp_path) / "input" / "test.csv"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("id,value\n1,100\n")
        
        entry = self.manager.quarantine(
            file_path=Path(self.temp_path) / "input" / "test.csv",
            reason="test"
        )
        
        # Restore to new location
        restore_path = self.temp_path / "restored" / "test.csv"
        result = self.manager.restore(entry.id, restore_path)
        
        assert result is True
        assert restore_path.exists()
        assert restore_path.read_text() == "id,value\n1,100\n"
        
        # Original quarantine file should be gone
        assert not Path(entry.quarantine_path).exists()
        
        # Metadata should be removed
        entries = self.manager.list_entries()
        assert len(entries) == 0
    
    def test_delete_file(self):
        """Test permanent deletion of quarantined file."""
        test_file = Path(self.temp_path) / "input" / "test.csv"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("test")
        
        entry = self.manager.quarantine(
            file_path=Path(self.temp_path) / "input" / "test.csv",
            reason="test"
        )
        
        # Delete
        result = self.manager.delete(entry.id)
        
        assert result is True
        assert not Path(entry.quarantine_path).exists()
        
        # Metadata should be removed
        entries = self.manager.list_entries()
        assert len(entries) == 0
    
    def test_quarantine_size_limit(self):
        """Test that quarantine size limit is enforced."""
        # Create config with small limit
        config = QuarantineConfig(
            quarantine_path=self.quarantine_dir,
            max_quarantine_size=1024  # 1KB limit
        )
        manager = QuarantineManager(config=config)
        
        # Create a file larger than limit
        test_file = Path(self.temp_path) / "input" / "large.csv"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("x" * 2000)  # 2KB > 1KB limit
        
        # Should raise error
        with pytest.raises(RuntimeError, match="Quarantine size limit exceeded"):
            manager.quarantine(
                file_path=Path(self.temp_path) / "input" / "large.csv",
                reason="size_test"
            )
    
    def test_quarantine_reason_preserved(self):
        """Test that quarantine reason is preserved."""
        test_file = Path(self.temp_path) / "input" / "test.csv"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("test")
        
        reasons = ["parse_error", "encoding_failed", "size_limit", "unsupported_format"]
        
        for reason in reasons:
            test_file.write_text(f"test for {reason}")
            entry = self.manager.quarantine(
                file_path=Path(self.temp_path) / "input" / "test.csv",
                reason=reason
            )
            assert entry.reason == reason
    
    def test_quarantine_details_preserved(self):
        """Test that quarantine details are preserved."""
        test_file = Path(self.temp_path) / "input" / "test.csv"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("test")
        
        details = {
            "error_line": 42,
            "error_type": "csv.Error",
            "message": "line contains NUL"
        }
        
        entry = self.manager.quarantine(
            file_path=Path(self.temp_path) / "input" / "test.csv",
            reason="parse_error",
            details=details
        )
        
        assert entry.details == details
        
        # Check persistence
        new_manager = QuarantineManager(config=QuarantineConfig(quarantine_path=self.quarantine_dir))
        entries = new_manager.list_entries()
        assert entries[0].details == details