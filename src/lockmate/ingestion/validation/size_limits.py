"""File size and resource limits."""

from pathlib import Path
from typing import Union
import structlog

logger = structlog.get_logger()


class SizeLimitExceeded(Exception):
    """Raised when a file exceeds size limits."""
    def __init__(self, path: Path, size: int, limit: int, limit_type: str):
        self.path = path
        self.size = size
        self.limit = limit
        self.limit_type = limit_type
        super().__init__(
            f"{limit_type} size limit exceeded for {path}: "
            f"{size} bytes > {limit} bytes"
        )


class SizeLimitConfig:
    """Configuration for size limits."""
    
    def __init__(
        self,
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        max_total_size: int = 1024 * 1024 * 1024,  # 1GB
        max_memory: int = 512 * 1024 * 1024,  # 512MB
    ) -> None:
        self.max_file_size = max_file_size
        self.max_total_size = max_total_size
        self.max_memory = max_memory


class SizeLimiter:
    """Enforces file size and resource limits."""
    
    def __init__(
        self,
        max_file_size: int = 100 * 1024 * 1024,
        max_total_size: int = 1024 * 1024 * 1024,
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
            SizeLimitExceeded: If file exceeds limits
        """
        path = Path(path)
        size = path.stat().st_size
        
        # Check individual file limit
        if size > self.max_file_size:
            raise SizeLimitExceeded(
                path, size, self.max_file_size, "file"
            )
        
        # Check total size limit
        if self._total_size + size > self.max_total_size:
            raise SizeLimitExceeded(
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
            SizeLimitExceeded: If memory limit would be exceeded
        """
        if requested > 512 * 1024 * 1024:  # Hardcoded for now
            raise SizeLimitExceeded(
                Path("memory"), requested, 512 * 1024 * 1024, "memory"
            )