"""
LOCKMATE — Encoding Detector

Detects file encoding using charset-normalizer with safe fallbacks.
Never uses Latin-1 as universal fallback for arbitrary binary.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..contracts import FormatType


# Supported encodings (in priority order)
SUPPORTED_ENCODINGS = [
    "utf-8",
    "utf-8-sig",   # UTF-8 with BOM
    "utf-16",
    "utf-16-le",
    "utf-16-be",
    "cp1252",      # Windows-1252
    "iso-8859-1",  # Latin-1 (only for text files with high confidence)
    "ascii",
]


def detect_encoding(
    file_path: Path,
    format_type: FormatType,
    max_bytes: int = 100_000
) -> str:
    """
    Detect file encoding using charset-normalizer.
    
    For binary/unknown formats, returns 'binary'.
    Never uses Latin-1 as universal fallback for arbitrary binary.
    
    Args:
        file_path: Path to file
        format_type: Detected format type
        max_bytes: Maximum bytes to read for detection
        
    Returns:
        Encoding name (e.g., 'utf-8', 'utf-16-le', 'cp1252')
    """
    # Binary/unsupported formats
    if format_type in (FormatType.UNKNOWN, FormatType.FHIR):
        return "binary"
    
    try:
        import charset_normalizer
        
        # Read sample for detection
        with file_path.open("rb") as f:
            sample = f.read(max_bytes)
        
        if not sample:
            return "utf-8"  # Empty file default
        
        # Use charset-normalizer for detection
        results = charset_normalizer.from_bytes(sample)
        best = results.best()
        
        if best and best.encoding:
            encoding = best.encoding.lower().replace("_", "-")
            
            # Normalize common aliases
            encoding = _normalize_encoding(encoding)
            
            # Validate encoding is supported
            if encoding in SUPPORTED_ENCODINGS:
                return encoding
            
            # If high confidence but unsupported, try fallback
            if best.chaos < 0.2 and best.language:
                # High confidence detection but unsupported encoding
                # Try to find closest supported equivalent
                fallback = _find_fallback_encoding(encoding)
                if fallback:
                    return fallback
        
    except Exception as e:
        # Log but continue with fallback
        pass
    
    # Default fallback for text formats
    return "utf-8"


def _normalize_encoding(encoding: str) -> str:
    """Normalize encoding name to standard form."""
    encoding = encoding.lower().replace("_", "-")
    
    # Common aliases
    aliases = {
        "utf8": "utf-8",
        "utf16": "utf-16",
        "utf16le": "utf-16-le",
        "utf16be": "utf-16-be",
        "utf-8-bom": "utf-8-sig",
        "utf8bom": "utf-8-sig",
        "windows-1252": "cp1252",
        "iso-8859-1": "iso-8859-1",
        "latin1": "iso-8859-1",
        "latin-1": "iso-8859-1",
        "ascii": "ascii",
        "us-ascii": "ascii",
    }
    
    return aliases.get(encoding, encoding)


def _find_fallback_encoding(detected: str) -> Optional[str]:
    """Find closest supported encoding for unsupported but detected encoding."""
    detected = detected.lower()
    
    # Unicode family
    if detected.startswith("utf"):
        return "utf-8"
    
    # ISO-8859 family
    if detected.startswith("iso-8859"):
        return "iso-8859-1"
    
    # Windows code pages
    if detected.startswith("cp") or detected.startswith("windows-"):
        return "cp1252"
    
    # Mac encodings
    if detected.startswith("mac"):
        return "utf-8"
    
    # Default
    return None


def validate_encoding(file_path: Path, encoding: str, max_errors: int = 10) -> bool:
    """
    Validate that a file can be decoded with given encoding.
    
    Args:
        file_path: Path to file
        encoding: Encoding to test
        max_errors: Maximum decoding errors allowed
        
    Returns:
        True if file can be decoded with <= max_errors
    """
    try:
        with file_path.open("r", encoding=encoding, errors="strict") as f:
            for _ in f:
                pass
        return True
    except UnicodeDecodeError:
        # Count errors with replace handler
        try:
            with file_path.open("r", encoding=encoding, errors="replace") as f:
                content = f.read()
            error_count = content.count("\ufffd")
            return error_count <= max_errors
        except Exception:
            return False
    except Exception:
        return False


def get_bom_encoding(file_path: Path) -> Optional[str]:
    """
    Detect BOM (Byte Order Mark) at start of file.
    
    Returns:
        Encoding if BOM found, None otherwise
    """
    try:
        with file_path.open("rb") as f:
            bom = f.read(4)
        
        if bom.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig"
        elif bom.startswith(b"\xff\xfe\x00\x00"):
            return "utf-32-le"
        elif bom.startswith(b"\x00\x00\xfe\xff"):
            return "utf-32-be"
        elif bom.startswith(b"\xff\xfe"):
            return "utf-16-le"
        elif bom.startswith(b"\xfe\xff"):
            return "utf-16-be"
    except Exception:
        pass
    
    return None