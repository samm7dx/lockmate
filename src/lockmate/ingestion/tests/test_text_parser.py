"""Tests for text_parser module."""

import pytest
from pathlib import Path
import tempfile

from lockmate.ingestion.parsers.text_parser import TextParser, TextParserConfig


class TestTextParser:
    """Tests for TextParser."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_line_mode(self):
        """Test line-by-line parsing."""
        text_file = self.temp_dir / "test.txt"
        text_file.write_text("Hello\nWorld\nThird line", encoding="utf-8")
        
        parser = TextParser()
        records = list(parser.parse(text_file))
        
        assert len(records) == 3
        assert records[0]["text"] == "Hello"
        assert records[0]["line_number"] == 1
        assert records[1]["text"] == "World"
        assert records[1]["line_number"] == 2
        assert records[2]["text"] == "Third line"
    
    def test_paragraph_mode(self):
        """Test paragraph parsing."""
        text_file = self.temp_dir / "paragraphs.txt"
        text_file.write_text(
            "First paragraph line 1\nFirst paragraph line 2\n\nSecond paragraph\n\nThird paragraph",
            encoding="utf-8"
        )
        
        config = TextParserConfig(line_mode="paragraphs")
        parser = TextParser(config)
        records = list(parser.parse(text_file))
        
        assert len(records) == 3
        assert records[0]["paragraph_number"] == 1
        assert "First paragraph" in records[0]["text"]
        assert records[0]["line_count"] == 2
        assert records[1]["paragraph_number"] == 2
        assert records[2]["paragraph_number"] == 3
    
    def test_whole_mode(self):
        """Test whole-file parsing."""
        text_file = self.temp_dir / "whole.txt"
        text_file.write_text("Line 1\nLine 2\nLine 3", encoding="utf-8")
        
        config = TextParserConfig(line_mode="whole")
        parser = TextParser(config)
        records = list(parser.parse(text_file))
        
        assert len(records) == 1
        assert records[0]["text"] == "Line 1\nLine 2\nLine 3"
        assert records[0]["line_count"] == 3
    
    def test_skip_empty_lines(self):
        """Test skipping empty lines."""
        text_file = self.temp_dir / "empty.txt"
        text_file.write_text("Line 1\n\n\nLine 2\n", encoding="utf-8")
        
        parser = TextParser()
        records = list(parser.parse(text_file))
        
        assert len(records) == 2
        assert records[0]["text"] == "Line 1"
        assert records[1]["text"] == "Line 2"
    
    def test_strip_whitespace(self):
        """Test whitespace stripping."""
        text_file = self.temp_dir / "whitespace.txt"
        text_file.write_text("  Hello  \n\tWorld\t\n", encoding="utf-8")
        
        parser = TextParser()
        records = list(parser.parse(text_file))
        
        assert records[0]["text"] == "Hello"
        assert records[1]["text"] == "World"
    
    def test_max_line_length(self):
        """Test max line length truncation."""
        text_file = self.temp_dir / "long.txt"
        text_file.write_text("a" * 1000, encoding="utf-8")
        
        config = TextParserConfig(max_line_length=100)
        parser = TextParser(config)
        records = list(parser.parse(text_file))
        
        assert len(records[0]["text"]) == 100
    
    def test_encoding(self):
        """Test specific encoding."""
        text_file = self.temp_dir / "encoded.txt"
        text_file.write_bytes("Café".encode("utf-8"))
        
        parser = TextParser()
        records = list(parser.parse(text_file))
        
        assert records[0]["text"] == "Café"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])