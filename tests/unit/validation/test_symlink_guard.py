"""
LOCKMATE — Symlink Guard Tests

Tests for SymlinkGuard symlink security.
"""

import pytest
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from secret_wards.validation import SymlinkGuard, PathTraversalError


# Skip symlink tests on Windows (requires admin privileges)
skip_on_windows = pytest.mark.skipif(
    sys.platform == "win32",
    reason="Symlink creation requires admin privileges on Windows"
)


class TestSymlinkGuard:
    """Test SymlinkGuard symlink protection."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.root = Path(self.temp_path) / "allowed"
        self.root.mkdir()
        self.outside = Path(self.temp_path) / "outside"
        self.outside.mkdir()
    
    def teardown_method(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()
    
    @skip_on_windows
    def test_disabled_guard_allows_symlinks(self):
        """Test that disabled guard allows all symlinks."""
        guard = SymlinkGuard(enabled=False)
        
        # Create symlink
        target = Path(self.temp_path) / "target.txt"
        target.write_text("target")
        link = Path(self.temp_path) / "link.txt"
        target.write_text("target")
        link.symlink_to(target)
        
        # Should not raise
        guard.check(link)
    
    @skip_on_windows
    def test_symlink_blocked_by_default(self):
        """Test that symlinks are blocked by default."""
        guard = SymlinkGuard(enabled=True)
        
        # Create symlink
        target = Path(self.temp_path) / "target.txt"
        target.write_text("target")
        link = Path(self.temp_path) / "link.txt"
        target.write_text("target")
        link.symlink_to(target)
        
        with pytest.raises(PathTraversalError) as exc_info:
            guard.check(link)
        
        assert "Symlink" in str(exc_info.value)
        assert "link" in str(exc_info.value).lower()
    
    @skip_on_windows
    def test_symlink_in_parent_blocked(self):
        """Test that symlinks in parent directories are detected."""
        # Create structure: temp/link_dir/target.txt -> temp/link_dir/link -> target
        link_dir = Path(self.temp_path) / "link_dir"
        link_dir.mkdir()
        
        target = Path(self.temp_path) / "target.txt"
        target.write_text("target")
        
        link = link_dir / "link.txt"
        link.symlink_to(target)
        
        # Create file inside link_dir that we'll check
        file_in_link_dir = link_dir / "file.txt"
        file_in_link_dir.write_text("test")
        
        guard = SymlinkGuard(enabled=True)
        
        # Should detect symlink in parent
        with pytest.raises(PathTraversalError):
            guard.check(file_in_link_dir)
    
    @skip_on_windows
    def test_allowed_roots_follow_allowed(self):
        """Test that symlinks within allowed roots are followed when allowed."""
        guard = SymlinkGuard(
            enabled=True,
            allowed_roots=[Path("/allowed")],
            follow_allowed=True
        )
        
        with TemporaryDirectory() as tmpdir:
            root = Path("/allowed") / "subdir"
            root.mkdir(parents=True)
            
            target = root / "target.txt"
            target.write_text("target")
            
            link = Path("/allowed") / "link"
            target.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(target)
            
            # Should allow symlink within allowed root
            guard.check(link)
    
    @skip_on_windows
    def test_symlink_outside_allowed_root_blocked(self):
        """Test that symlinks pointing outside allowed roots are blocked even in follow mode."""
        guard = SymlinkGuard(
            enabled=True,
            allowed_roots=[Path("/allowed")],
            follow_allowed=True
        )
        
        with TemporaryDirectory() as tmpdir:
            allowed_root = Path(tmpdir) / "allowed"
            allowed_root.mkdir()
            
            outside_root = Path(tmpdir) / "outside"
            outside_root.mkdir()
            
            target = outside_root / "target.txt"
            target.write_text("target")
            
            link = allowed_root / "link.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(target)
            
            # Should block symlink pointing outside allowed root
            with pytest.raises(PathTraversalError):
                guard.check(link)
    
    @skip_on_windows
    def test_symlink_to_file_vs_directory(self):
        """Test that both file and directory symlinks are handled."""
        guard = SymlinkGuard(enabled=True)
        
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # File symlink
            target_file = tmpdir / "target_file.txt"
            target_file.write_text("file content")
            link_file = tmpdir / "link_file.txt"
            link_file.symlink_to(target_file)
            
            with pytest.raises(PathTraversalError):
                guard.check(link_file)
            
            # Directory symlink
            target_dir = tmpdir / "target_dir"
            target_dir.mkdir()
            (target_dir / "file.txt").write_text("inside dir")
            
            link_dir = tmpdir / "link_dir"
            link_dir.symlink_to(target_dir)
            
            with pytest.raises(PathTraversalError):
                guard.check(link_dir)
    
    @skip_on_windows
    def test_nested_symlinks(self):
        """Test that nested symlinks are detected."""
        guard = SymlinkGuard(enabled=True)
        
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create chain: link1 -> link2 -> target
            target = tmpdir / "target.txt"
            target.write_text("target")
            
            link2 = tmpdir / "link2.txt"
            link2.symlink_to(target)
            
            link1 = tmpdir / "link1.txt"
            link1.symlink_to(link2)
            
            # Both should be detected
            with pytest.raises(PathTraversalError):
                guard.check(link1)
            
            with pytest.raises(PathTraversalError):
                guard.check(link2)
    
    def test_regular_file_passes(self):
        """Test that regular (non-symlink) files pass."""
        guard = SymlinkGuard(enabled=True)
        
        with TemporaryDirectory() as tmpdir:
            regular_file = Path(tmpdir) / "regular.txt"
            regular_file.write_text("regular file")
            
            # Should not raise
            guard.check(regular_file)
    
    @skip_on_windows
    def test_symlink_to_parent_directory(self):
        """Test symlink to parent directory (classic traversal)."""
        guard = SymlinkGuard(enabled=True)
        
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            allowed = tmpdir / "allowed"
            allowed.mkdir()
            
            # Create symlink to parent directory
            link = allowed / "parent_link"
            link.symlink_to(tmpdir)
            
            # Create a file in allowed that we check
            test_file = allowed / "test.txt"
            test_file.write_text("test")
            
            # Should detect symlink in path
            with pytest.raises(PathTraversalError):
                guard.check(test_file)