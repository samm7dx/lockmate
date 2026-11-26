"""
LOCKMATE — Path Guard Tests

Tests for PathGuard path traversal protection.
"""

import pytest
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from secret_wards.validation import PathGuard, PathTraversalError


skip_on_windows = pytest.mark.skipif(
    sys.platform == "win32",
    reason="Symlink creation requires admin privileges on Windows"
)


class TestPathGuard:
    """Test PathGuard path traversal protection."""
    
    def test_valid_path_within_root(self):
        """Test that paths within allowed root pass validation."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            test_file = root / "subdir" / "file.txt"
            test_file.parent.mkdir(parents=True)
            test_file.write_text("test")
            
            guard = PathGuard([root])
            result = guard.validate(test_file)
            
            assert result == test_file.resolve()
    
    def test_path_outside_root_rejected(self):
        """Test that paths outside allowed root are rejected."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "allowed"
            outside = Path(tmpdir) / "outside"
            root.mkdir()
            outside.mkdir()
            
            test_file = outside / "file.txt"
            test_file.write_text("test")
            
            guard = PathGuard([root])
            
            with pytest.raises(PathTraversalError):
                guard.validate(test_file)
    
    def test_path_traversal_blocked(self):
        """Test that path traversal sequences are blocked."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "allowed"
            root.mkdir()
            
            # Create a file inside
            safe_file = root / "safe.txt"
            safe_file.write_text("safe")
            
            # Try to traverse out
            traversal_path = root / "subdir" / ".." / ".." / "etc" / "passwd"
            traversal_path.parent.mkdir(parents=True)
            
            guard = PathGuard([root])
            
            # The traversal should be detected and blocked
            with pytest.raises(PathTraversalError):
                guard.validate(traversal_path)
    
    def test_null_byte_rejected(self):
        """Test that null bytes in path are rejected."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # TemporaryDirectory already creates the directory
            
            guard = PathGuard([root])
            
            # Path with null byte
            bad_path = Path("safe.txt\x00.exe")
            
            with pytest.raises(PathTraversalError) as exc_info:
                guard.validate(bad_path)
            
            assert "Null byte" in str(exc_info.value)
    
    def test_url_encoded_traversal_blocked(self):
        """Test that URL-encoded traversal attempts are blocked."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # TemporaryDirectory already creates the directory
            
            guard = PathGuard([root])
            
            # URL-encoded ../ traversal
            bad_path = Path("safe.txt%2e%2e%2f..%2fetc%2fpasswd")
            
            with pytest.raises(PathTraversalError) as exc_info:
                guard.validate(bad_path)
            
            assert "URL-encoded" in str(exc_info.value)
    
    @skip_on_windows
    def test_symlink_outside_root_blocked(self):
        """Test that symlinks pointing outside root are blocked."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "allowed"
            outside = Path(tmpdir) / "outside"
            root.mkdir()
            outside.mkdir()
            
            # Create a symlink inside allowed pointing outside
            link_path = Path(tmpdir) / "allowed" / "link"
            link_path.symlink_to(outside / "target")
            
            guard = PathGuard([Path(tmpdir) / "allowed"])
            
            with pytest.raises(PathTraversalError):
                guard.validate(link_path)


class TestPathGuardMultipleRoots:
    """Test PathGuard with multiple allowed roots."""
    
    def test_multiple_allowed_roots(self):
        """Test validation with multiple allowed roots."""
        with TemporaryDirectory() as tmpdir:
            root1 = Path(tmpdir) / "root1"
            root2 = Path(tmpdir) / "root2"
            root1.mkdir()
            root2.mkdir()
            
            file1 = root1 / "file1.txt"
            file2 = root2 / "file2.txt"
            file1.write_text("test1")
            file2.write_text("test2")
            
            guard = PathGuard([root1, root2])
            
            result1 = guard.validate(file1)
            result2 = guard.validate(file2)
            
            assert result1 == file1.resolve()
            assert result2 == file2.resolve()
    
    def test_add_remove_allowed_root(self):
        """Test adding and removing allowed roots dynamically."""
        with TemporaryDirectory() as tmpdir:
            root1 = Path(tmpdir) / "root1"
            root2 = Path(tmpdir) / "root2"
            root1.mkdir()
            root2.mkdir()
            
            file1 = root1 / "file1.txt"
            file2 = root2 / "file2.txt"
            file1.write_text("test1")
            file2.write_text("test2")
            
            guard = PathGuard([root1])
            
            # Should work for root1
            guard.validate(file1)
            
            # Should fail for root2 initially
            from secret_wards.exceptions import PathTraversalError
            with pytest.raises(PathTraversalError):
                guard.validate(file2)
            
            # Add root2
            guard.add_allowed_root(root2)
            guard.validate(file2)  # Should work now
            
            # Remove root1
            guard.remove_allowed_root(root1)
            with pytest.raises(PathTraversalError):
                guard.validate(file1)
            guard.validate(file2)  # Should still work