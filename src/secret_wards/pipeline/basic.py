"""
LOCKMATE — Basic Sanitization Pipeline (Phase 3)

End-to-end CSV/JSON/text sanitization with placeholder detection
to validate serialization and output contract.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from ..contracts import (
    InputFile, ParsedDocument, UnifiedRecord, UnifiedRecord,
    PIISpan, MedicalSpan, SanitizedRecord, QuarantineResult,
    QuarantineReason, FormatType, RecordLocation, RecordLocationType,
    FieldValue, FieldType, RecordStatus
)
from ..utils.logging import get_logger_adapter
from ..utils.metrics import FileMetrics
from ..utils.temp import TempFileManager
from ..exceptions import QuarantineAllError

logger = get_logger_adapter("pipeline.basic")


def run_basic_pipeline(
    input_dir: Path,
    output_dir: Path,
    secret: bytes,
    config_path: Path,
    metrics_collector,
    temp_manager: TempFileManager
) -> dict:
    """
    Run basic sanitization pipeline (Phase 3).
    
    Processes CSV/JSON/Text with placeholder PII detection.
    FHIR and advanced detection not included.
    
    Returns:
        Dictionary with pipeline results
    """
    logger.info("basic_pipeline_started", input_dir=str(input_dir))
    
    results = {
        "files_processed": 0,
        "files_sanitized": 0,
        "files_quarantined": 0,
        "errors": []
    }
    
    # This is a scaffold - full implementation in Phase 3
    logger.warning("basic_pipeline_not_fully_implemented")
    
    return results


def placeholder_detect_pii(record: UnifiedRecord) -> List[PIISpan]:
    """
    Placeholder PII detection using simple regex patterns.
    
    Detects: email, phone (simple), PAN, 12-digit numbers, dates
    """
    import re
    
    spans = []
    text = record.normalized_text
    
    # Email pattern
    email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    for match in email_pattern.finditer(text):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.EMAIL,
            confidence=0.9,
            original_text=match.group(),
            context=text[max(0, match.start()-50):match.end()+50],
            detector="placeholder_email"
        ))
    
    # Simple phone pattern (10 digits)
    phone_pattern = re.compile(r'\b\d{10}\b')
    for match in phone_pattern.finditer(text):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.PHONE,
            confidence=0.7,
            original_text=match.group(),
            context=text[max(0, match.start()-50):match.end()+50],
            detector="placeholder_phone"
        ))
    
    # PAN pattern
    pan_pattern = re.compile(r'\b[A-Z]{5}\d{4}[A-Z]\b')
    for match in pan_pattern.finditer(text):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.PAN,
            confidence=0.95,
            original_text=match.group(),
            context=text[max(0, match.start()-50):match.end()+50],
            detector="placeholder_pan"
        ))
    
    # 12-digit numbers (potential Aadhaar)
    aadhaar_pattern = re.compile(r'\b\d{12}\b')
    for match in aadhaar_pattern.finditer(text):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.AADHAAR,
            confidence=0.6,
            original_text=match.group(),
            context=text[max(0, match.start()-50):match.end()+50],
            detector="placeholder_aadhaar"
        ))
    
    # Simple date patterns
    date_pattern = re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b')
    for match in date_pattern.finditer(text):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.DATE,
            confidence=0.7,
            original_text=match.group(),
            context=text[max(0, match.start()-50):match.end()+50],
            detector="placeholder_date"
        ))
    
    return spans


def placeholder_detect_medical(record: UnifiedRecord) -> List[MedicalSpan]:
    """
    Placeholder medical veto detection.
    
    Detects: dosages (N mg), frequencies (OD, BD, TDS), disease names (Parkinson's)
    """
    import re
    
    spans = []
    text = record.normalized_text
    
    # Dosage pattern (e.g., "5 mg", "500mg", "10 mg/mL")
    dosage_pattern = re.compile(r'\b\d+(?:\.\d+)?\s*(?:mg|g|mL|mcg|IU|U)\b', re.IGNORECASE)
    for match in dosage_pattern.finditer(text):
        spans.append(MedicalSpan(
            start=match.start(),
            end=match.end(),
            medical_type=MedicalType.DOSAGE,
            confidence=0.9,
            original_text=match.group()
        ))
    
    # Frequency patterns
    freq_pattern = re.compile(r'\b(?:OD|BD|TDS|QID|SOS|once\s+daily|twice\s+daily|thrice\s+daily)\b', re.IGNORECASE)
    for match in freq_pattern.finditer(text):
        spans.append(MedicalSpan(
            start=match.start(),
            end=match.end(),
            medical_type=MedicalType.FREQUENCY,
            confidence=0.9,
            original_text=match.group()
        ))
    
    # Disease names (basic)
    disease_pattern = re.compile(r"\b(?:Parkinson's|Alzheimer's|Crohn's|Diabetes|Hypertension|TB|HIV)\b", re.IGNORECASE)
    for match in disease_pattern.finditer(text):
        spans.append(MedicalSpan(
            start=match.start(),
            end=match.end(),
            medical_type=MedicalType.DIAGNOSIS,
            confidence=0.95,
            original_text=match.group()
        ))
    
    return spans


def merge_spans_with_veto(
    pii_spans: List[PIISpan],
    medical_spans: List[MedicalSpan]
) -> List[PIISpan]:
    """
    Merge PII spans with medical veto.
    
    Medical spans veto overlapping PII spans.
    """
    filtered = []
    
    for pii in pii_spans:
        # Check if any medical span overlaps or is adjacent
        vetoed = False
        for med in medical_spans:
            if pii.overlaps(med):
                # Medical wins - veto this PII
                vetoed = True
                break
            # Adjacency check (within 5 chars)
            if abs(pii.start - med.end) <= 5 or abs(pii.end - med.start) <= 5:
                # Re-evaluate - could be "Rahul 5 mg" where Rahul is name
                # For placeholder, we'll be conservative and not veto on adjacency
                pass
        
        if not vetoed:
            filtered.append(pii)
    
    return filtered


def replace_spans_in_text(
    record: UnifiedRecord,
    pii_spans: List[PIISpan],
    replacement_map: dict = None
) -> SanitizedRecord:
    """
    Replace PII spans in text using offset maps.
    
    Uses normalized_text offsets to replace in original text.
    """
    if replacement_map is None:
        replacement_map = {
            PIIType.NAME: "[NAME]",
            PIIType.PHONE: "[PHONE]",
            PIIType.AADHAAR: "[UID]",
            PIIType.ABHA: "[ABHA]",
            PIIType.PAN: "[PAN]",
            PIIType.EMAIL: "[EMAIL]",
            PIIType.ADDRESS: "[ADDRESS]",
            PIIType.DATE: "[DATE]",
            PIIType.UHID: "[UHID]",
            PIIType.RELATIVE: "[RELATIVE]",
            PIIType.DOCTOR: "[DOCTOR]",
            PIIType.PIN: "[PIN]",
        }
    
    # Sort spans by start position (descending) for correct replacement
    sorted_spans = sorted(pii_spans, key=lambda s: s.start, reverse=True)
    
    # Work with normalized text first
    normalized = list(record.normalized_text)
    
    for span in sorted_spans:
        replacement = replacement_map.get(span.pii_type, "[REDACTED]")
        # Replace in normalized text
        normalized[span.start:span.end] = list(replacement)
    
    transformed_normalized = "".join(normalized)
    
    # Now map back to original text using offset_map
    # This is simplified - full implementation needs careful offset mapping
    transformed_original = transformed_normalized  # Placeholder
    
    return SanitizedRecord(
        record=record,
        transformed_text=transformed_original,
        transformed_fields={},
        pseudonym=None
    )


def sanitize_structured_fields(
    record: UnifiedRecord,
    pii_spans: List[PIISpan]
) -> dict:
    """
    Sanitize structured fields (CSV columns, JSON values, FHIR elements).
    
    Returns dict of field_path -> sanitized_value
    """
    # This is a stub - full implementation in Phase 3
    return {}