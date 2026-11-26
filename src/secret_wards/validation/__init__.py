"""
LOCKMATE — Validation Package

File validation, path guards, size limits, symlink guards, and quarantine management.
"""

from .path_guard import PathGuard, PathTraversalError
from .quarantine import QuarantineManager, QuarantineConfig, QuarantineEntry
from .size_limits import SizeLimiter, SizeLimitConfig, ResourceLimitExceeded
from .symlink_guard import SymlinkGuard, SymlinkError
from .file_validator import FileValidator, ValidationConfig, ValidationResult

__all__ = [
    "PathGuard",
    "PathTraversalError",
    "QuarantineManager",
    "QuarantineConfig",
    "QuarantineEntry",
    "SizeLimiter",
    "SizeLimitConfig",
    "ResourceLimitExceeded",
    "SymlinkGuard",
    "SymlinkError",
    "FileValidator",
    "ValidationConfig",
    "ValidationResult",
]