"""
LOCKMATE — Size Limits Tests

Tests for SizeLimiter resource limits enforcement.
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from secret_wards.validation import SizeLimiter, ResourceLimitExceeded


class TestSizeLimiter:
    """Test SizeLimiter resource limits enforcement."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.input_dir = Path(self.temp_path) / "input"
        self.input_dir.mkdir()
    
    def teardown_method(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()
    
    def test_file_size_within_limit(self):
        """Test that files within size limit pass."""
        limiter = SizeLimiter(max_file_size=1024, max_total_size=10240)
        
        test_file = Path(self.temp_path) / "small.txt"
        test_file.write_text("x" * 100)  # 100 bytes
        
        size = limiter.check(test_file)
        assert size == 100
        assert limiter.total_size == 100
    
    def test_file_size_exceeds_limit(self):
        """Test that files exceeding size limit are rejected."""
        limiter = SizeLimiter(max_file_size=100, max_total_size=10240)
        
        test_file = Path(self.temp_path) / "large.txt"
        test_file.write_text("x" * 200)  # 200 bytes > 100 limit
        
        with pytest.raises(ResourceLimitExceeded) as exc_info:
            limiter.check(test_file)
        
        assert exc_info.value.size == 200
        assert exc_info.value.limit == 100
        assert exc_info.value.limit_type == "file"
        assert "200 bytes > 100 bytes" in str(exc_info.value)
    
    def test_total_size_limit(self):
        """Test that total size limit is enforced."""
        limiter = SizeLimiter(max_file_size=1000, max_total_size=100)
        
        file1 = Path(self.temp_path) / "file1.txt"
        file1.write_text("x" * 60)  # 60 bytes
        
        file2 = Path(self.temp_path) / "file2.txt"
        file2.write_text("x" * 50)  # 50 bytes, total would be 110 > 100
        
        # First file should pass
        size1 = limiter.check(Path(self.temp_path) / "file1.txt")
        assert size1 == 60
        assert limiter.total_size == 60
        
        # Second file should exceed total limit
        with pytest.raises(ResourceLimitExceeded) as exc_info:
            limiter.check(Path(self.temp_path) / "file2.txt")
        
        assert exc_info.value.limit_type == "total"
        assert exc_info.value.limit == 100
    
    def test_total_reset(self):
        """Test that total counter can be reset."""
        limiter = SizeLimiter(max_file_size=1000, max_total_size=100)
        
        file1 = Path(self.temp_path) / "file1.txt"
        file1.write_text("x" * 60)
        
        limiter.check(Path(self.temp_path) / "file1.txt")
        assert limiter.total_size == 60
        
        limiter.reset_total()
        assert limiter.total_size == 0
        
        # Should be able to add same file again
        size = limiter.check(Path(self.temp_path) / "file1.txt")
        assert size == 60
        assert limiter.total_size == 60
    
    def test_empty_file(self):
        """Test that empty files are handled correctly."""
        limiter = SizeLimiter(max_file_size=100, max_total_size=1024)
        
        empty_file = Path(self.temp_path) / "empty.txt"
        empty_file.write_text("")
        
        size = limiter.check(empty_file)
        assert size == 0
        assert limiter.total_size == 0
    
    def test_memory_limit(self):
        """Test memory limit checking."""
        limiter = SizeLimiter(max_file_size=1000, max_total_size=10000)
        
        # Should pass for reasonable memory requests
        limiter.check_memory(1024 * 1024)  # 1MB
        limiter.check_memory(512 * 1024 * 1024)  # 512MB
        
        # Should fail for excessive memory requests
        with pytest.raises(ResourceLimitExceeded) as exc_info:
            limiter.check_memory(5 * 1024 * 1024 * 1024)  # 5GB > 4GB limit
        
        assert exc_info.value.limit_type == "memory"
        assert exc_info.value.limit == 4 * 1024 * 1024 * 1024
    
    def test_error_details(self):
        """Test that error contains all relevant details."""
        limiter = SizeLimiter(max_file_size=100, max_total_size=1000)
        
        test_file = Path(self.temp_path) / "large.txt"
        test_file.write_text("x" * 200)
        
        with pytest.raises(ResourceLimitExceeded) as exc_info:
            limiter.check(test_file)
        
        exc = exc_info.value
        assert exc.path == Path(self.temp_path) / "large.txt"
        assert exc.size == 200
        assert exc.limit == 100
        assert exc.limit_type == "file"