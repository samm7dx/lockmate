"""Tests for symlink_guard module."""

import pytest
import sys
from pathlib import Path
import tempfile
import os

from lockmate.ingestion.validation.symlink_guard import SymlinkGuard, SymlinkError


# Skip symlink tests on Windows (requires admin privileges)
IS_WINDOWS = sys.platform == "win32"


class TestSymlinkGuard:
    """Tests for SymlinkGuard."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.outside_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        shutil.rmtree(self.outside_dir, ignore_errors=True)
    
    def test_no_symlink_allowed(self):
        """Test that regular files pass."""
        guard = SymlinkGuard(enabled=True)
        test_file = self.temp_dir / "file.txt"
        test_file.write_text("test")
        
        # Should not raise
        guard.check(test_file)
    
    @pytest.mark.skipif(IS_WINDOWS, reason="Symlinks require admin privileges on Windows")
    def test_symlink_blocked_by_default(self):
        """Test that symlinks are blocked by default."""
        guard = SymlinkGuard(enabled=True)
        
        # Create target and symlink
        target = self.temp_dir / "target.txt"
        target.write_text("target")
        
        link = self.temp_dir / "link.txt"
        link.symlink_to(target)
        
        with pytest.raises(SymlinkError):
            guard.check(link)
    
    @pytest.mark.skipif(IS_WINDOWS, reason="Symlinks require admin privileges on Windows")
    def test_symlink_follow_allowed_within_root(self):
        """Test that symlinks within allowed roots are allowed when follow_allowed=True."""
        guard = SymlinkGuard(
            enabled=True,
            allowed_roots=[self.temp_dir],
            follow_allowed=True
        )
        
        target = self.temp_dir / "target.txt"
        target.write_text("target")
        
        link = self.temp_dir / "link.txt"
        link.symlink_to(target)
        
        # Should not raise
        guard.check(link)
    
    @pytest.mark.skipif(IS_WINDOWS, reason="Symlinks require admin privileges on Windows")
    def test_symlink_follow_blocked_outside_root(self):
        """Test that symlinks outside allowed roots are blocked even with follow_allowed."""
        guard = SymlinkGuard(
            enabled=True,
            allowed_roots=[self.temp_dir],
            follow_allowed=True
        )
        
        target = self.outside_dir / "secret.txt"
        target.write_text("secret")
        
        link = self.temp_dir / "link.txt"
        link.symlink_to(target)
        
        with pytest.raises(SymlinkError):
            guard.check(link)
    
    @pytest.mark.skipif(IS_WINDOWS, reason="Symlinks require admin privileges on Windows")
    def test_parent_symlink_detected(self):
        """Test that symlinks in parent directories are detected."""
        guard = SymlinkGuard(enabled=True)
        
        # Create subdir structure with symlink in parent
        subdir = self.temp_dir / "subdir"
        subdir.mkdir()
        
        target = self.temp_dir / "target.txt"
        target.write_text("target")
        
        # Make subdir a symlink
        subdir.unlink()
        subdir.symlink_to(self.temp_dir)
        
        test_file = subdir / "file.txt"
        test_file.write_text("test")
        
        with pytest.raises(SymlinkError):
            guard.check(test_file)
    
    @pytest.mark.skipif(IS_WINDOWS, reason="Symlinks require admin privileges on Windows")
    def test_disabled_guard(self):
        """Test that disabled guard allows everything."""
        guard = SymlinkGuard(enabled=False)
        
        target = self.outside_dir / "secret.txt"
        target.write_text("secret")
        
        link = self.temp_dir / "link.txt"
        link.symlink_to(target)
        
        # Should not raise
        guard.check(link)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])