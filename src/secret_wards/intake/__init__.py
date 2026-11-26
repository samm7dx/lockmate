"""
LOCKMATE — Intake Package
"""

from .discovery import discover_files, _walk_safe, _compute_sha256_streaming, _classify_format, _detect_encoding
from .hashing import compute_sha256, compute_sha256_from_stream, verify_sha256, compute_sha256_incremental
from .classifier import classify_format, classify_stream
from .encoding import detect_encoding, _normalize_encoding, _find_fallback_encoding, validate_encoding, get_bom_encoding
from .quarantine import quarantine_file, create_quarantine_entry, get_reason_details
from .pipeline import IntakePipeline

__all__ = [
    "discover_files",
    "compute_sha256",
    "classify_format",
    "detect_encoding",
    "quarantine_file",
    "IntakePipeline",
]