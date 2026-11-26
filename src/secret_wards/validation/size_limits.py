"""
LOCKMATE — File Size and Resource Limits

Enforces file size and resource limits during ingestion.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union
from dataclasses import dataclass

from ..exceptions import ResourceLimitError as ResourceLimitExceeded
from ..utils.logging import get_logger

logger = get_logger("validation.size_limits")


@dataclass
class SizeLimitConfig:
    """Configuration for size limits."""
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    max_total_size: int = 2 * 1024 * 1024 * 1024  # 2GB (organizer limit)
    max_memory: int = 4 * 1024 * 1024 * 1024  # 4GB (organizer limit)


class SizeLimiter:
    """Enforces file size and resource limits."""
    
    def __init__(
        self,
        max_file_size: int = 100 * 1024 * 1024,
        max_total_size: int = 2 * 1024 * 1024 * 1024,
    ) -> None:
        self.max_file_size = max_file_size
        self.max_total_size = max_total_size
        self._total_size = 0
    
    def check(self, path: Union[str, Path]) -> int:
        """
        Check if file size is within limits.
        
        Args:
            path: Path to file
            
        Returns:
            File size in bytes
            
        Raises:
            ResourceLimitExceeded: If file exceeds limits
        """
        path = Path(path)
        size = path.stat().st_size
        
        # Check individual file limit
        if size > self.max_file_size:
            raise ResourceLimitExceeded(
                path, size, self.max_file_size, "file"
            )
        
        # Check total size limit
        if self._total_size + size > self.max_total_size:
            raise ResourceLimitExceeded(
                path, size, self.max_total_size, "total"
            )
        
        self._total_size += size
        logger.debug("size.check_passed", path=str(path), size=size, total=self._total_size)
        
        return size
    
    def reset_total(self) -> None:
        """Reset the total size counter."""
        self._total_size = 0
    
    @property
    def total_size(self) -> int:
        """Get current total size."""
        return self._total_size
    
    def check_memory(self, requested: int) -> None:
        """
        Check if memory allocation is within limits.
        
        Args:
            requested: Requested memory in bytes
            
        Raises:
            ResourceLimitExceeded: If memory limit would be exceeded
        """
        MAX_MEMORY = 4 * 1024 * 1024 * 1024  # 4GB (organizer limit)
        if requested > MAX_MEMORY:
            raise ResourceLimitExceeded(
                Path("memory"), requested, MAX_MEMORY, "memory"
            )