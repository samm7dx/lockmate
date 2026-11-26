"""Tests for path_guard module."""

import pytest
import sys
from pathlib import Path
import tempfile
import os

from lockmate.ingestion.validation.path_guard import PathGuard, PathTraversalError


# Skip symlink tests on Windows (requires admin privileges)
IS_WINDOWS = sys.platform == "win32"


class TestPathGuard:
    """Tests for PathGuard."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.guard = PathGuard(allowed_roots=[self.temp_dir])
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_valid_path_within_root(self):
        """Test that valid paths within root are allowed."""
        test_file = self.temp_dir / "subdir" / "file.txt"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("test")
        
        result = self.guard.validate(test_file)
        assert result == test_file.resolve()
    
    def test_path_traversal_with_double_dot(self):
        """Test that ../ traversal is blocked."""
        # Create a file outside temp_dir
        outside_file = Path(tempfile.mkdtemp()) / "secret.txt"
        outside_file.write_text("secret")
        
        # Try to access it via traversal
        traversal_path = self.temp_dir / "subdir" / ".." / ".." / outside_file.name
        
        with pytest.raises(PathTraversalError):
            self.guard.validate(traversal_path)
    
    def test_absolute_path_outside_root(self):
        """Test that absolute paths outside root are blocked."""
        outside_dir = Path(tempfile.mkdtemp())
        outside_file = outside_dir / "secret.txt"
        outside_file.write_text("secret")
        
        with pytest.raises(PathTraversalError):
            self.guard.validate(outside_file)
    
    def test_null_byte_in_path(self):
        """Test that null bytes are rejected."""
        with pytest.raises(PathTraversalError):
            self.guard.validate(self.temp_dir / "file\x00.txt")
    
    @pytest.mark.skipif(IS_WINDOWS, reason="Symlinks require admin privileges on Windows")
    def test_symlink_resolution(self):
        """Test that symlinks are resolved for validation."""
        # Create a real file
        real_file = self.temp_dir / "real.txt"
        real_file.write_text("real")
        
        # Create symlink
        link_file = self.temp_dir / "link.txt"
        link_file.symlink_to(real_file)
        
        # Should resolve and validate successfully
        result = self.guard.validate(link_file)
        assert result == real_file.resolve()
    
    @pytest.mark.skipif(IS_WINDOWS, reason="Symlinks require admin privileges on Windows")
    def test_symlink_outside_root(self):
        """Test that symlinks pointing outside are blocked."""
        outside_dir = Path(tempfile.mkdtemp())
        outside_file = outside_dir / "secret.txt"
        outside_file.write_text("secret")
        
        # Create symlink pointing outside
        link_file = self.temp_dir / "link.txt"
        link_file.symlink_to(outside_file)
        
        with pytest.raises(PathTraversalError):
            self.guard.validate(link_file)
    
    def test_multiple_allowed_roots(self):
        """Test with multiple allowed roots."""
        root2 = Path(tempfile.mkdtemp())
        guard = PathGuard(allowed_roots=[self.temp_dir, root2])
        
        file2 = root2 / "file.txt"
        file2.write_text("test")
        
        result = guard.validate(file2)
        assert result == file2.resolve()
        
        import shutil
        shutil.rmtree(root2, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])