"""
LOCKMATE — File Discovery Walker

Safe file system traversal with symlink resolution, path traversal protection,
and resource limit enforcement.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import List, Generator, Optional

from ..contracts import InputFile, FormatType
from ..utils.logging import get_logger
from ..exceptions import PathTraversalError, ResourceLimitError

logger = get_logger("intake.discovery")


# Resource limits from policy
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB
MAX_TOTAL_INPUT_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB
MAX_NESTING_DEPTH = 50
MAX_DECOMPRESSION_RATIO = 100  # 100:1


def discover_files(
    input_dir: Path,
    max_file_size: int = MAX_FILE_SIZE_BYTES,
    max_total_size: int = MAX_TOTAL_INPUT_BYTES
) -> List[InputFile]:
    """
    Discover all files in input directory with safety checks.
    
    Args:
        input_dir: Root directory to scan
        max_file_size: Maximum individual file size in bytes
        max_total_size: Maximum total input size in bytes
        
    Returns:
        List of InputFile objects sorted by SHA-256 (deterministic order)
        
    Raises:
        PathTraversalError: If symlink points outside input_dir
        ResourceLimitError: If total input exceeds limit
    """
    input_root = input_dir.resolve()
    files: List[InputFile] = []
    total_size = 0
    
    for file_path in _walk_safe(input_root):
        if not file_path.is_file():
            continue
        
        # Check file size
        try:
            stat = file_path.stat()
            file_size = stat.st_size
        except OSError as e:
            logger.warning("file_stat_failed", file=str(file_path), error=str(e))
            continue
        
        if file_size > max_file_size:
            logger.warning("file_too_large", file=str(file_path), size=file_size, limit=max_file_size)
            continue
        
        total_size += file_size
        if total_size > max_total_size:
            raise ResourceLimitError(f"Total input size exceeds {max_total_size} bytes limit")
        
        # Compute SHA-256
        sha256_hash = _compute_sha256_streaming(file_path)
        
        # Classify format
        format_type = _classify_format(file_path)
        
        # Detect encoding for text-based formats
        encoding = _detect_encoding(file_path, format_type)
        
        input_file = InputFile(
            path=file_path,
            sha256=sha256_hash,
            size_bytes=file_size,
            format=format_type,
            encoding=encoding
        )
        files.append(input_file)
    
    # Sort by SHA-256 for deterministic processing order
    files.sort(key=lambda f: f.sha256)
    
    logger.info("discovery_complete", files_found=len(files), total_size_bytes=total_size)
    return files


def _walk_safe(root: Path) -> Generator[Path, None, None]:
    """
    Walk directory tree with symlink and path traversal protection.
    
    Yields:
        Resolved file paths within the root directory
    """
    visited = set()
    
    def _walk(current: Path):
        try:
            current_resolved = current.resolve()
        except OSError:
            return
        
        # Check for path traversal
        try:
            current_resolved.relative_to(root)
        except ValueError:
            logger.warning("path_traversal_blocked", path=str(current))
            raise PathTraversalError(f"Path traversal attempt blocked: {current}")
        
        # Prevent infinite loops from symlink cycles
        if current_resolved in visited:
            return
        visited.add(current_resolved)
        
        try:
            if current_resolved.is_file():
                yield current_resolved
            elif current_resolved.is_dir():
                try:
                    for child in current_resolved.iterdir():
                        yield from _walk(child)
                except PermissionError:
                    logger.warning("permission_denied", path=str(current_resolved))
        except OSError as e:
            logger.warning("walk_error", path=str(current), error=str(e))
    
    yield from _walk(root)


def _compute_sha256_streaming(file_path: Path, chunk_size: int = 8192) -> str:
    """
    Compute SHA-256 hash of a file using streaming (memory efficient).
    
    Args:
        file_path: Path to file
        chunk_size: Read chunk size in bytes
        
    Returns:
        64-character hexadecimal SHA-256 hash
    """
    sha256 = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _classify_format(file_path: Path) -> FormatType:
    """
    Classify file format by extension and content sniffing.
    """
    suffix = file_path.suffix.lower()
    
    # Extension-based classification
    if suffix == ".csv":
        return FormatType.CSV
    elif suffix == ".tsv":
        return FormatType.TSV
    elif suffix == ".json":
        return FormatType.JSON
    elif suffix in [".txt", ".text"]:
        return FormatType.TEXT
    elif suffix in [".xml", ".fhir"]:
        return FormatType.FHIR
    
    # Content sniffing for extensionless or ambiguous files
    try:
        with file_path.open("rb") as f:
            header = f.read(1024)
        
        if not header:
            return FormatType.UNKNOWN
        
        # JSON detection
        stripped = header.lstrip()
        if stripped.startswith((b"{", b"[")):
            return FormatType.JSON
        
        # XML/FHIR detection
        if stripped.startswith(b"<?xml") or b"<Bundle" in header[:512] or b"<Patient" in header[:512]:
            return FormatType.FHIR
        
        # CSV/TSV heuristic: check for delimiters in first few lines
        text_header = header[:512].decode("utf-8", errors="ignore")
        lines = text_header.splitlines()[:5]
        if lines:
            # Check for common delimiters
            comma_count = sum(line.count(",") for line in lines)
            tab_count = sum(line.count("\t") for line in lines)
            if tab_count > comma_count and tab_count > 2:
                return FormatType.TSV
            elif comma_count > 2:
                return FormatType.CSV
        
        return FormatType.TEXT
        
    except Exception:
        return FormatType.UNKNOWN


def _detect_encoding(file_path: Path, format_type: FormatType) -> str:
    """
    Detect file encoding using charset-normalizer.
    
    For binary/unknown formats, returns 'binary'.
    """
    if format_type in (FormatType.UNKNOWN, FormatType.FHIR):
        return "binary"
    
    try:
        import charset_normalizer
        result = charset_normalizer.from_path(str(file_path)).best()
        if result:
            return result.encoding or "utf-8"
    except Exception:
        pass
    
    return "utf-8"