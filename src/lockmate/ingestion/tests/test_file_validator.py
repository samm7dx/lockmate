"""Tests for file_validator module."""

import pytest
from pathlib import Path
import tempfile

from lockmate.ingestion.validation.file_validator import FileValidator, ValidationConfig, ValidationResult


class TestFileValidator:
    """Tests for FileValidator."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.validator = FileValidator()
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_valid_text_file(self):
        """Test validation of valid text file."""
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("Hello, World!", encoding="utf-8")
        
        result = self.validator.validate(test_file)
        
        assert result.is_valid
        assert result.mime_type == "text/plain"
        assert result.encoding.lower() in ("utf-8", "ascii")
    
    def test_valid_csv_file(self):
        """Test validation of valid CSV file."""
        test_file = self.temp_dir / "test.csv"
        test_file.write_text("col1,col2\n1,2\n3,4", encoding="utf-8")
        
        result = self.validator.validate(test_file)
        
        assert result.is_valid
        assert "csv" in result.mime_type.lower()
    
    def test_valid_json_file(self):
        """Test validation of valid JSON file."""
        test_file = self.temp_dir / "test.json"
        test_file.write_text('{"key": "value"}', encoding="utf-8")
        
        result = self.validator.validate(test_file)
        
        assert result.is_valid
        assert result.mime_type == "application/json"
    
    def test_nonexistent_file(self):
        """Test validation of nonexistent file."""
        test_file = self.temp_dir / "nonexistent.txt"
        
        result = self.validator.validate(test_file)
        
        assert not result.is_valid
        assert "does not exist" in result.reason
    
    def test_directory_not_file(self):
        """Test validation of directory (not a file)."""
        test_dir = self.temp_dir / "subdir"
        test_dir.mkdir()
        
        result = self.validator.validate(test_dir)
        
        assert not result.is_valid
        assert "not a regular file" in result.reason
    
    def test_disallowed_mime_type(self):
        """Test validation rejects disallowed MIME types."""
        # Create a config that only allows JSON
        config = ValidationConfig(
            allowed_mime_types={"application/json"}
        )
        validator = FileValidator(config=config)
        
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("plain text", encoding="utf-8")
        
        result = validator.validate(test_file)
        
        assert not result.is_valid
        assert "not allowed" in result.reason
    
    def test_non_utf8_encoding(self):
        """Test validation of non-UTF8 file with require_utf8=True."""
        test_file = self.temp_dir / "latin1.txt"
        # Use longer text for more reliable detection
        test_file.write_bytes("café au lait avec accents: éàùç".encode("latin-1"))
        
        result = self.validator.validate(test_file)
        
        # Should detect non-UTF8 encoding
        assert result.is_valid  # Still valid but encoding is not utf-8
        # Just verify it's detected as something other than UTF-8
        assert result.encoding.lower().replace('_', '-') != "utf-8"
        # And not ASCII
        assert result.encoding.lower().replace('_', '-') != "ascii"
    
    def test_utf8_with_bom(self):
        """Test validation of UTF-8 with BOM."""
        test_file = self.temp_dir / "utf8_bom.txt"
        test_file.write_bytes(b"\xef\xbb\xbfHello World")
        
        result = self.validator.validate(test_file)
        
        assert result.is_valid
        # Accept both utf-8 and utf_8 variants
        assert result.encoding.lower().replace('_', '-') == "utf-8"
    
    def test_empty_file(self):
        """Test validation of empty file."""
        test_file = self.temp_dir / "empty.txt"
        test_file.write_text("")
        
        result = self.validator.validate(test_file)
        
        assert result.is_valid
        # Empty files may be detected as various types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])