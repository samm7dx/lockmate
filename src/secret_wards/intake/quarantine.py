"""
LOCKMATE — Quarantine Classifier

Handles quarantine of unsafe/unsupported files with reason codes.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from ..contracts import InputFile, QuarantineResult, QuarantineReason
from ..utils.logging import get_logger_adapter

logger = get_logger_adapter("intake.quarantine")


def quarantine_file(
    input_file: InputFile,
    output_dir: Path,
    reason: QuarantineReason,
    details: str = ""
) -> QuarantineResult:
    """
    Quarantine a file by copying to quarantine directory.
    
    Args:
        input_file: File to quarantine
        output_dir: Output root directory
        reason: Quarantine reason code
        details: Additional details for audit
        
    Returns:
        QuarantineResult with output path and metadata
    """
    quarantine_dir = output_dir / "quarantined"
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate quarantine filename: sha256 + original extension
    quarantine_filename = f"{input_file.sha256}{input_file.path.suffix}"
    quarantine_path = quarantine_dir / quarantine_filename
    
    # Copy original file to quarantine
    try:
        shutil.copy2(input_file.path, quarantine_path)
        logger.info("file_quarantined", 
                   file_sha256=input_file.sha256[:16],
                   reason=reason.value,
                   quarantine_path=str(quarantine_path))
    except Exception as e:
        logger.error("quarantine_copy_failed", 
                    file_sha256=input_file.sha256[:16],
                    error=str(e))
        # Still return result with error details
        details = f"{details}; copy failed: {e}"
    
    return QuarantineResult(
        input_file=input_file,
        reason=reason,
        output_path=quarantine_path,
        records_affected=0,
        details=details
    )


def create_quarantine_entry(
    input_file: InputFile,
    output_dir: Path,
    reason: QuarantineReason,
    details: str = ""
) -> QuarantineResult:
    """
    Create quarantine entry without copying file (for parse errors during processing).
    
    Used when file was already partially processed but failed.
    """
    quarantine_dir = output_dir / "quarantined"
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    
    quarantine_filename = f"{input_file.sha256}{input_file.path.suffix}"
    quarantine_path = quarantine_dir / quarantine_filename
    
    # Try to copy if not already there
    if not quarantine_path.exists():
        try:
            import shutil
            shutil.copy2(input_file.path, quarantine_path)
        except Exception:
            pass  # File might not be accessible
    
    return QuarantineResult(
        input_file=input_file,
        reason=reason,
        output_path=quarantine_path,
        records_affected=0,
        details=details
    )


def get_reason_details(reason: QuarantineReason) -> str:
    """Get human-readable description for quarantine reason."""
    descriptions = {
        QuarantineReason.UNSUPPORTED_FORMAT: "File format not supported for sanitization",
        QuarantineReason.ENCODING_DETECTION_FAILED: "Unable to detect or validate file encoding",
        QuarantineReason.PARSE_ERROR: "File parsing failed (malformed or corrupted)",
        QuarantineReason.RESOURCE_LIMIT_EXCEEDED: "File exceeds size, nesting, or decompression limits",
        QuarantineReason.RESIDUAL_PII: "Residual high-confidence PII detected after sanitization",
        QuarantineReason.OUTPUT_GATE_FAILED: "Security gate validation failed on sanitized output",
        QuarantineReason.UNCERTAIN_IDENTITY: "Identity resolution uncertain, conservative quarantine",
        QuarantineReason.PATH_TRAVERSAL: "Path traversal attempt detected",
        QuarantineReason.DECOMPRESSION_BOMB: "Decompression bomb detected",
        QuarantineReason.MALFORMED_FHIR: "FHIR resource validation failed",
        QuarantineReason.BINARY_ATTACHMENT: "Binary attachment (PDF/image) in FHIR resource",
    }
    return descriptions.get(reason, "Unknown quarantine reason")