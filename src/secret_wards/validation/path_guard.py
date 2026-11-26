"""
LOCKMATE — Path Traversal Protection

Validates that file paths are within allowed roots and do not attempt
path traversal attacks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union, List

from ..exceptions import PathTraversalError
from ..utils.logging import get_logger_adapter

logger = get_logger_adapter("validation.path_guard")


class PathGuard:
    """
    Validates that file paths are within allowed roots and do not attempt
    path traversal.
    """
    
    def __init__(self, allowed_roots: List[Path]) -> None:
        """
        Initialize with list of allowed root directories.
        
        Args:
            allowed_roots: List of absolute paths that are allowed as roots.
        """
        # Normalize all roots to absolute paths
        self.allowed_roots = [root.resolve() for root in allowed_roots]
        logger.debug("path_guard.initialized", roots=[str(r) for r in self.allowed_roots])
        
    def validate(self, path: Union[str, Path]) -> Path:
        """
        Validate a path is within allowed roots and safe.
        
        Args:
            path: Path to validate
            
        Returns:
            Resolved absolute path if valid
            
        Raises:
            PathTraversalError: If path is outside allowed roots or attempts traversal
        """
        path = Path(path)
        
        # Check for null bytes (classic bypass)
        if "\x00" in str(path):
            raise PathTraversalError(path, "Null byte in path")
        
        # Resolve to absolute path (follows symlinks for validation)
        try:
            resolved = path.resolve(strict=False)
        except Exception as e:
            raise PathTraversalError(path, f"Failed to resolve path: {e}")
        
        # Check if path tries to escape via parent directory references
        self._check_traversal(path, resolved)
        
        # Check if path is within any allowed root
        if not self._is_within_allowed(resolved):
            raise PathTraversalError(
                path, 
                f"Path not within allowed roots: {[str(r) for r in self.allowed_roots]}"
            )
        
        logger.debug("path_guard.validated", path=str(path), resolved=str(resolved))
        return resolved
    
    def _check_traversal(self, original: Path, resolved: Path) -> None:
        """Check for path traversal patterns in the original path."""
        original_str = str(original)
        
        # Check for explicit traversal sequences
        parts = original_str.replace("\\", "/").split("/")
        if ".." in parts:
            # Allow '..' only if it doesn't escape allowed roots (checked later)
            # But we log/flag it
            logger.debug("path_guard.traversal_sequence_detected", path=original_str)
        
        # Check for URL-encoded traversal attempts
        if "%2e%2e" in original_str.lower() or "%2e%2e%2f" in original_str.lower():
            raise PathTraversalError(
                Path(original_str), 
                "URL-encoded path traversal attempt detected"
            )
    
    def _is_within_allowed(self, path: Path) -> bool:
        """Check if path is within any allowed root."""
        for root in self.allowed_roots:
            try:
                path.relative_to(root)
                return True
            except ValueError:
                continue
        return False
    
    def add_allowed_root(self, root: Path) -> None:
        """Add an allowed root directory."""
        self.allowed_roots.append(root.resolve())
        logger.debug("path_guard.root_added", root=str(root))
    
    def remove_allowed_root(self, root: Path) -> None:
        """Remove an allowed root directory."""
        root = root.resolve()
        if root in self.allowed_roots:
            self.allowed_roots.remove(root)
            logger.debug("path_guard.root_removed", root=str(root))