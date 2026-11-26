"""Tests for atomic_write module."""

import pytest
from pathlib import Path
import tempfile
import os

from lockmate.ingestion.output.atomic_write import AtomicWriter, AtomicWriteConfig, atomic_write


class TestAtomicWriter:
    """Tests for AtomicWriter."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.output_dir = self.temp_dir / "output"
        self.writer = AtomicWriter(AtomicWriteConfig(output_dir=self.output_dir))
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_write_bytes(self):
        """Test writing bytes atomically."""
        result = self.writer.write_bytes(b"Hello World")
        
        assert result.exists()
        assert result.read_bytes() == b"Hello World"
    
    def test_write_text(self):
        """Test writing text atomically."""
        result = self.writer.write_text("Hello World")
        
        assert result.exists()
        assert result.read_text() == "Hello World"
    
    def test_atomic_write_context(self):
        """Test atomic_write context manager."""
        filename = "test.txt"
        with self.writer.atomic_write(filename=filename, mode="wb") as (f, final_path):
            f.write(b"content")
        
        assert final_path.exists()
        assert final_path.read_bytes() == b"content"
    
    def test_no_temp_files_left(self):
        """Test that no temp files are left behind."""
        self.writer.write_bytes(b"data")
        
        # Check no temp files remain
        temp_files = list(self.output_dir.glob("*.tmp"))
        hidden_temp = list(self.output_dir.glob(".*.tmp"))
        assert len(temp_files) == 0
        assert len(hidden_temp) == 0
    
    def test_generate_filename_unique(self):
        """Test that generated filenames are unique."""
        f1 = self.writer.generate_filename()
        f2 = self.writer.generate_filename()
        
        assert f1 != f2
    
    def test_generate_filename_from_original(self):
        """Test filename generation from original name."""
        filename = self.writer.generate_filename("test_data.csv")
        
        assert "test_data" in filename
        assert filename.endswith(".csv")
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        # Test with unsafe characters
        unsafe_name = "test<>:\"/\\|?*"
        sanitized = self.writer._sanitize_filename(unsafe_name)
        
        # No unsafe characters should remain
        for c in '<>:"/\\|?*':
            assert c not in sanitized
    
    def test_convenience_function(self):
        """Test convenience function."""
        result = atomic_write(
            b"data",
            output_dir=self.output_dir,
            filename="test.bin"
        )
        
        assert result.exists()
        assert result.read_bytes() == b"data"
    
    def test_overwrite_existing(self):
        """Test overwriting existing files."""
        self.writer.write_bytes(b"first", filename="test.txt")
        self.writer.write_bytes(b"second", filename="test.txt")
        
        # Should have created both (or overwritten)
        result = self.output_dir / "test.txt"
        assert result.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])