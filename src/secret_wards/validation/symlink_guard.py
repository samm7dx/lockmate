"""
LOCKMATE — Symlink Security Guard

Validates symlinks to prevent directory traversal via symlinks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union, Optional, List

from ..exceptions import PathTraversalError
from ..utils.logging import get_logger

logger = get_logger("validation.symlink_guard")


class SymlinkError(Exception):
    """Raised when a symlink violation is detected."""
    def __init__(self, path: Path, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Symlink violation for {path}: {reason}")


class SymlinkGuard:
    """
    Validates symlinks to prevent directory traversal via symlinks.
    
    By default, blocks all symlinks. Can be configured to follow symlinks
    only if they resolve within allowed roots.
    """
    
    def __init__(
        self, 
        enabled: bool = True,
        allowed_roots: Optional[List[Path]] = None,
        follow_allowed: bool = False
    ) -> None:
        """
        Initialize symlink guard.
        
        Args:
            enabled: Whether to check symlinks (default: True)
            allowed_roots: Roots within which symlinks can resolve (for follow mode)
            follow_allowed: If True, allow symlinks that resolve within allowed_roots
        """
        self.enabled = enabled
        self.allowed_roots = [r.resolve() for r in (allowed_roots or [])]
        self.follow_allowed = follow_allowed
    
    def check(self, path: Union[str, Path]) -> None:
        """
        Check if path or any parent is a symlink.
        
        Args:
            path: Path to check
            
        Raises:
            PathTraversalError: If symlink found and not allowed
        """
        if not self.enabled:
            return
            
        path = Path(path)
        
        # Check if path itself is a symlink
        if path.is_symlink():
            self._handle_symlink(path, "path")
        
        # Check parents for symlinks (defense in depth)
        for parent in path.parents:
            if parent.is_symlink():
                self._handle_symlink(parent, "parent")
    
    def _handle_symlink(self, symlink_path: Path, location: str) -> None:
        """Handle a detected symlink."""
        target = symlink_path.resolve()
        
        logger.warning(
            "symlink.detected",
            symlink=str(symlink_path),
            target=str(target),
            location=location
        )
        
        if self.follow_allowed:
            # Check if target is within allowed roots
            if self._is_allowed_target(target):
                logger.info("symlink.allowed", symlink=str(symlink_path), target=str(target))
                return
        
        # Block the symlink
        raise PathTraversalError(
            symlink_path,
            f"Symlink at {location} points to {target} (not in allowed roots)"
        )
    
    def _is_allowed_target(self, target: Path) -> bool:
        """Check if symlink target is within allowed roots."""
        for root in self.allowed_roots:
            try:
                target.relative_to(root)
                return True
            except ValueError:
                continue
        return False