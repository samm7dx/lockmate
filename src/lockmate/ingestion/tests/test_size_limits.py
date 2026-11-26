"""Tests for size_limits module."""

import pytest
from pathlib import Path
import tempfile

from lockmate.ingestion.validation.size_limits import SizeLimiter, SizeLimitExceeded


class TestSizeLimiter:
    """Tests for SizeLimiter."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_file_within_limit(self):
        """Test file within size limit passes."""
        limiter = SizeLimiter(max_file_size=1024)  # 1KB
        
        test_file = self.temp_dir / "small.txt"
        test_file.write_text("hello")  # 5 bytes
        
        size = limiter.check(test_file)
        assert size == 5
    
    def test_file_exceeds_limit(self):
        """Test file exceeding size limit raises."""
        limiter = SizeLimiter(max_file_size=10)  # 10 bytes
        
        test_file = self.temp_dir / "large.txt"
        test_file.write_text("hello world")  # 11 bytes
        
        with pytest.raises(SizeLimitExceeded) as exc_info:
            limiter.check(test_file)
        
        assert exc_info.value.limit_type == "file"
        assert exc_info.value.size == 11
        assert exc_info.value.limit == 10
    
    def test_total_size_limit(self):
        """Test total size limit across multiple files."""
        limiter = SizeLimiter(
            max_file_size=1024,
            max_total_size=50  # 50 bytes total
        )
        
        # First file - 30 bytes
        file1 = self.temp_dir / "file1.txt"
        file1.write_text("x" * 30)
        limiter.check(file1)
        
        # Second file - 15 bytes (total 45, still OK)
        file2 = self.temp_dir / "file2.txt"
        file2.write_text("y" * 15)
        limiter.check(file2)
        
        # Third file - 10 bytes (total 55, exceeds)
        file3 = self.temp_dir / "file3.txt"
        file3.write_text("z" * 10)
        
        with pytest.raises(SizeLimitExceeded) as exc_info:
            limiter.check(file3)
        
        assert exc_info.value.limit_type == "total"
    
    def test_reset_total(self):
        """Test resetting total counter."""
        limiter = SizeLimiter(max_file_size=1024, max_total_size=50)
        
        file1 = self.temp_dir / "file1.txt"
        file1.write_text("x" * 30)
        limiter.check(file1)
        
        assert limiter.total_size == 30
        
        limiter.reset_total()
        assert limiter.total_size == 0
    
    def test_memory_check(self):
        """Test memory limit check."""
        limiter = SizeLimiter()
        
        # Should pass for reasonable amounts
        limiter.check_memory(1024 * 1024)  # 1MB
        
        # Should fail for excessive amounts
        with pytest.raises(SizeLimitExceeded):
            limiter.check_memory(1024 * 1024 * 1024)  # 1GB


if __name__ == "__main__":
    pytest.main([__file__, "-v"])