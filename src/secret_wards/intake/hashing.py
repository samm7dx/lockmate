"""
LOCKMATE — Streaming SHA-256 Calculator

Memory-efficient hash computation for large files.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import BinaryIO


def compute_sha256(file_path: Path, chunk_size: int = 8192) -> str:
    """
    Compute SHA-256 hash of a file using streaming.
    
    Args:
        file_path: Path to file
        chunk_size: Read chunk size in bytes (default 8KB)
        
    Returns:
        64-character hexadecimal SHA-256 hash
        
    Raises:
        OSError: If file cannot be read
    """
    sha256 = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def compute_sha256_from_stream(stream: BinaryIO, chunk_size: int = 8192) -> str:
    """
    Compute SHA-256 from a binary stream.
    
    Args:
        stream: Binary stream (must be at position 0 or will read from current position)
        chunk_size: Read chunk size in bytes
        
    Returns:
        64-character hexadecimal SHA-256 hash
    """
    sha256 = hashlib.sha256()
    for chunk in iter(lambda: stream.read(chunk_size), b""):
        sha256.update(chunk)
    return sha256.hexdigest()


def verify_sha256(file_path: Path, expected_hash: str, chunk_size: int = 8192) -> bool:
    """
    Verify file matches expected SHA-256 hash.
    
    Args:
        file_path: Path to file
        expected_hash: Expected 64-char hex hash
        chunk_size: Read chunk size
        
    Returns:
        True if hash matches
    """
    actual = compute_sha256(file_path, chunk_size)
    return actual.lower() == expected_hash.lower()


def compute_sha256_incremental(chunks) -> str:
    """
    Compute SHA-256 from an iterable of byte chunks.
    
    Args:
        chunks: Iterable yielding bytes chunks
        
    Returns:
        64-character hexadecimal SHA-256 hash
    """
    sha256 = hashlib.sha256()
    for chunk in chunks:
        sha256.update(chunk)
    return sha256.hexdigest()