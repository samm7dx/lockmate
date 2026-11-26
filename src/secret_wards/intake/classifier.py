"""
LOCKMATE — Format Classifier

Classifies files by format using extension and content sniffing.
"""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from ..contracts import FormatType


def classify_format(file_path: Path) -> FormatType:
    """
    Classify file format by extension and content sniffing.
    
    Args:
        file_path: Path to file
        
    Returns:
        FormatType enum value
    """
    suffix = file_path.suffix.lower()
    
    # Extension-based classification (high confidence)
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
    
    # Content sniffing for extensionless/ambiguous files
    return _classify_by_content(file_path)


def classify_stream(stream: BinaryIO) -> FormatType:
    """
    Classify format by reading stream header.
    
    Note: Consumes up to 1KB from stream. Caller should seek back if needed.
    """
    pos = stream.tell()
    header = stream.read(1024)
    stream.seek(pos)
    return _classify_header(header)


def _classify_by_content(file_path: Path) -> FormatType:
    """Classify by reading file header."""
    try:
        with file_path.open("rb") as f:
            header = f.read(1024)
        return _classify_header(header)
    except Exception:
        return FormatType.UNKNOWN


def _classify_header(header: bytes) -> FormatType:
    """
    Classify format from header bytes.
    
    Args:
        header: First 1024 bytes of file
        
    Returns:
        FormatType enum
    """
    if not header:
        return FormatType.UNKNOWN
    
    stripped = header.lstrip()
    
    # JSON detection
    if stripped.startswith((b"{", b"[")):
        return FormatType.JSON
    
    # XML/FHIR detection
    if stripped.startswith(b"<?xml"):
        # Check for FHIR-specific elements
        if b"xmlns=\"http://hl7.org/fhir\"" in header[:2048] or b"fhir" in header[:2048].lower():
            return FormatType.FHIR
        return FormatType.FHIR  # Default XML to FHIR for safety
    
    if b"<Bundle" in header[:512] or b"<Patient" in header[:512] or b"<Observation" in header[:512]:
        return FormatType.FHIR
    
    # CSV/TSV heuristic
    text_header = header[:512].decode("utf-8", errors="ignore")
    lines = text_header.splitlines()[:10]
    
    if len(lines) >= 2:
        # Count delimiters
        comma_counts = [line.count(",") for line in lines]
        tab_counts = [line.count("\t") for line in lines]
        pipe_counts = [line.count("|") for line in lines]
        semicolon_counts = [line.count(";") for line in lines]
        
        avg_commas = sum(comma_counts) / len(lines)
        avg_tabs = sum(tab_counts) / len(lines)
        avg_pipes = sum(pipe_counts) / len(lines)
        avg_semicolons = sum(semicolon_counts) / len(lines)
        
        # Heuristic: consistent delimiter across lines suggests structured format
        if avg_tabs > 1 and all(c > 0 for c in tab_counts):
            return FormatType.TSV
        elif avg_commas > 1 and all(c > 0 for c in comma_counts):
            return FormatType.CSV
        elif avg_pipes > 1 and all(c > 0 for c in pipe_counts):
            return FormatType.CSV  # Treat pipe as CSV variant
        elif avg_semicolons > 1 and all(c > 0 for c in semicolon_counts):
            return FormatType.CSV  # Treat semicolon as CSV variant
    
    # Default to text
    return FormatType.TEXT