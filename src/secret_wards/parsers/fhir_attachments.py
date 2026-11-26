"""
LOCKMATE — FHIR Attachment Handler

Handles FHIR Binary resources and attachment content.
Base64 PDF/image → quarantine; text/plain → extract + scan.
"""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

from ..contracts import QuarantineResult, QuarantineReason
from ..utils.logging import get_logger_adapter
from ..utils.temp import TempFileManager

logger = get_logger_adapter("parsers.fhir_attachments")


# MIME types that are safe to process as text
SAFE_TEXT_TYPES = {
    "text/plain",
    "text/csv",
    "text/xml",
    "application/json",
    "application/xml",
    "application/csv",
}

# MIME types that should be quarantined
QUARANTINE_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/tiff",
    "image/bmp",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/zip",
    "application/x-tar",
    "application/gzip",
}


def handle_fhir_binary(
    binary_resource: Dict,
    temp_manager: TempFileManager,
    output_dir: Path
) -> Tuple[Optional[str], Optional[QuarantineResult]]:
    """
    Handle FHIR Binary resource.
    
    Args:
        binary_resource: FHIR Binary resource dict
        temp_manager: TempFileManager for secure temp files
        output_dir: Output directory for quarantine
        
    Returns:
        Tuple of (extracted_text, quarantine_result)
        - extracted_text: Text content if safe, None if quarantined
        - quarantine_result: QuarantineResult if quarantined, None if safe
    """
    content_type = binary_resource.get("contentType", "application/octet-stream")
    data_b64 = binary_resource.get("data", "")
    
    if not data_b64:
        logger.warning("binary_no_data", resource_id=binary_resource.get("id"))
        return None, None
    
    # Decode base64
    try:
        binary_data = base64.b64decode(data_b64)
    except Exception as e:
        logger.error("binary_decode_failed", error=str(e))
        return None, None
    
    # Check content type
    mime_type = content_type.lower().split(";")[0].strip()
    
    if mime_type in QUARANTINE_TYPES or mime_type not in SAFE_TEXT_TYPES:
        # Quarantine binary/unsafe content
        quarantine_result = _quarantine_binary(
            binary_data, mime_type, binary_resource, temp_manager, output_dir
        )
        return None, quarantine_result
    
    # Safe text type - try to decode
    try:
        text_content = binary_data.decode("utf-8")
        return text_content, None
    except UnicodeDecodeError:
        # Try other encodings
        for encoding in ["utf-16", "cp1252", "iso-8859-1"]:
            try:
                text_content = binary_data.decode(encoding)
                return text_content, None
            except UnicodeDecodeError:
                continue
        
        # Cannot decode as text - quarantine
        quarantine_result = _quarantine_binary(
            binary_data, "undecodable", binary_resource, temp_manager, output_dir
        )
        return None, quarantine_result


def _quarantine_binary(
    binary_data: bytes,
    mime_type: str,
    binary_resource: Dict,
    temp_manager: TempFileManager,
    output_dir: Path
) -> QuarantineResult:
    """Quarantine binary attachment."""
    from ..contracts import QuarantineResult, QuarantineReason, InputFile
    import hashlib
    
    # Compute hash for filename
    sha256_hash = hashlib.sha256(binary_data).hexdigest()
    
    # Determine extension from MIME type
    ext = mimetypes.guess_extension(mime_type) or ".bin"
    
    quarantine_dir = output_dir / "sanitized" / "quarantined"
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    
    quarantine_filename = f"{sha256_hash}{ext}"
    quarantine_path = quarantine_dir / quarantine_filename
    
    # Write binary data to quarantine
    try:
        with quarantine_path.open("wb") as f:
            f.write(binary_data)
    except Exception as e:
        logger.error("quarantine_write_failed", error=str(e))
    
    # Create mock InputFile for quarantine result
    mock_input = InputFile(
        path=Path(f"Binary/{binary_resource.get('id', 'unknown')}"),
        sha256=sha256_hash,
        size_bytes=len(binary_data),
        format="binary",
        encoding="binary"
    )
    
    return QuarantineResult(
        input_file=mock_input,
        reason=QuarantineReason.BINARY_ATTACHMENT,
        output_path=quarantine_path,
        records_affected=0,
        details=f"FHIR Binary resource quarantined: {mime_type}"
    )


def scan_attachment_content(
    content: str,
    resource_path: str
) -> List[str]:
    """
    Scan attachment text content for PII indicators.
    
    Returns list of detected PII types (for logging/alerting).
    """
    import re
    
    detected = []
    
    # Phone patterns
    if re.search(r'(?:\+91|0)?[6-9]\d{9}', content):
        detected.append("phone")
    
    # Aadhaar (12 digits)
    if re.search(r'\b\d{12}\b', content):
        detected.append("aadhaar")
    
    # PAN
    if re.search(r'\b[A-Z]{5}\d{4}[A-Z]\b', content):
        detected.append("pan")
    
    # Email
    if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content):
        detected.append("email")
    
    # PIN (6 digits)
    if re.search(r'\b\d{6}\b', content):
        detected.append("pin")
    
    return detected