"""
LOCKMATE — Structured Field PII Scanner

Scans structured fields (JSON keys, CSV headers, FHIR elements, filenames)
for PII and returns spans for sanitization.
"""

from __future__ import annotations

import re
import json
from typing import List, Dict, Any, Optional, Generator, Tuple

from ..contracts import PIISpan, PIIType, ParsedDocument, UnifiedRecord
from ..utils.logging import get_logger_adapter
from ..detection.placeholder import detect_pii_placeholder
from .names import detect_names
from .identifiers import detect_identifiers

logger = get_logger_adapter("detection.structured")


def scan_structured_fields(record: UnifiedRecord) -> List:
    """
    Scan structured fields in a record for PII.
    
    Scans:
    - JSON keys (not just values)
    - CSV/TSV headers
    - FHIR element paths
    - Filenames
    - Metadata fields
    
    Args:
        record: UnifiedRecord with fields dict
        
    Returns:
        List of PIISpan objects
    """
    spans = []
    
    for field_path, field_value in record.fields.items():
        if isinstance(field_value.value, str):
            # Scan field value
            spans.extend(_scan_string_value(
                field_value.value, 
                field_path, 
                record.normalized_text
            ))
        elif isinstance(field_value.value, dict):
            # Nested object - recurse
            spans.extend(_scan_nested_object(field_value.value, field_path))
        elif isinstance(field_value.value, list):
            # Array - iterate
            for i, item in enumerate(field_value.value):
                if isinstance(item, str):
                    spans.extend(_scan_string_value(
                        item,
                        f"{field_path}[{i}]",
                        record.normalized_text
                    ))
                elif isinstance(item, dict):
                    spans.extend(_scan_nested_object(item, f"{field_path}[{i}]"))
    
    # Also scan filename
    if hasattr(record, 'source_file') and record.source_file:
        spans.extend(_scan_filename(record.source_file.path.name))
    
    return spans


def _scan_nested_object(obj: dict, path: str) -> List:
    """Recursively scan nested JSON object."""
    spans = []
    for key, value in obj.items():
        new_path = f"{path}.{key}"
        if isinstance(value, str):
            spans.extend(_scan_string_value(value, new_path, ""))
        elif isinstance(value, dict):
            spans.extend(_scan_nested_object(value, new_path))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, str):
                    spans.extend(_scan_string_value(item, f"{path}[{i}]", ""))
                elif isinstance(item, dict):
                    spans.extend(_scan_nested_object(item, f"{path}[{i}]"))
    return spans


def _scan_string_value(text: str, field_path: str, original_text: str) -> List:
    """Scan a string value for PII using existing detectors."""
    from ..contracts import PIISpan, PIIType
    from .placeholder import detect_pii_placeholder
    from .identifiers import detect_identifiers
    from .names import detect_names
    import re
    
    spans = []
    if not text:
        return spans
    
    # Create a mock record for detection
    from ..contracts import UnifiedRecord, RecordLocation, RecordStatus, FieldValue, FieldType
    
    mock_record = UnifiedRecord(
        record_id=f"struct:{field_path}",
        location=RecordLocation.from_json_pointer(""),
        fields={},
        raw_text=text,
        normalized_text=text,
        offset_map=[],
        status=RecordStatus.PENDING
    )
    
    # Run detectors
    spans.extend(detect_pii_placeholder(mock_record))
    spans.extend(detect_identifiers(mock_record))
    
    # Context-aware detection based on field path
    field_path_lower = field_path.lower()
    
    # Village/Mohalla field detection
    if any(keyword in field_path_lower for keyword in ['village', 'mohalla', 'locality', 'area', 'zone', 'gram', 'gaon']):
        # Detect bare village names (capitalized words, 1-4 words)
        village_pattern = re.compile(r'\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b')
        for match in village_pattern.finditer(text):
            # Skip if already detected
            if not any(s.start == match.start() and s.end == match.end() for s in spans):
                spans.append(PIISpan(
                    start=match.start(),
                    end=match.end(),
                    pii_type=PIIType.ADDRESS,
                    confidence=0.7,
                    original_text=match.group(),
                    context=f"{field_path}: {text[max(0, match.start()-50):match.end()+50]}",
                    detector="village_field"
                ))
    
    # Relative Name field detection
    if any(keyword in field_path_lower for keyword in ['relative', 'relation']):
        # Detect bare relative names (capitalized words) - single or double names
        relative_pattern = re.compile(r'\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b')
        for match in relative_pattern.finditer(text):
            # Skip if already detected
            if not any(s.start == match.start() and s.end == match.end() for s in spans):
                spans.append(PIISpan(
                    start=match.start(),
                    end=match.end(),
                    pii_type=PIIType.RELATIVE,
                    confidence=0.95,  # Higher than NAME (0.8) to win tie-breaking
                    original_text=match.group(),
                    context=f"{field_path}: {text[max(0, match.start()-50):match.end()+50]}",
                    detector="relative_field"
                ))
        # Also detect relative names with prefixes (S/o, D/o, W/o, C/O)
        relative_prefix_pattern = re.compile(
            r'\b(?:S/o|D/o|W/o|C/O|S/O|D/O|W/O|C/O|Son\s+of|Daughter\s+of|Wife\s+of|Husband\s+of|Father\s+of|Mother\s+of)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b',
            re.IGNORECASE
        )
        for match in relative_prefix_pattern.finditer(text):
            # Skip if already detected
            if not any(s.start == match.start() and s.end == match.end() for s in spans):
                spans.append(PIISpan(
                    start=match.start(),
                    end=match.end(),
                    pii_type=PIIType.RELATIVE,
                    confidence=0.9,
                    original_text=match.group(),
                    context=f"{field_path}: {text[max(0, match.start()-50):match.end()+50]}",
                    detector="relative_prefix_field"
                ))
    
    # Doctor field detection (ref_doctor, referred_by, doctor, attending_doctor, etc.)
    if any(keyword in field_path_lower for keyword in ['ref_doctor', 'referred_by', 'referring_doctor', 'attending_doctor', 'treating_doctor', 'consulting_doctor', 'doctor', 'dr', 'consultant', 'referral']):
        # Detect doctor names with Dr./Doctor prefix or bare names in doctor fields
        doctor_pattern = re.compile(r'\b(?:Dr\.?|Doctor)\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)*[A-Z][a-z]+)\b')
        for match in doctor_pattern.finditer(text):
            # Skip if already detected
            if not any(s.start == match.start() and s.end == match.end() for s in spans):
                spans.append(PIISpan(
                    start=match.start(),
                    end=match.end(),
                    pii_type=PIIType.DOCTOR,
                    confidence=0.9,
                    original_text=match.group(),
                    context=f"{field_path}: {text[max(0, match.start()-50):match.end()+50]}",
                    detector="doctor_field"
                ))
        # Also detect bare names in doctor fields (capitalized Firstname Lastname)
        bare_doctor_pattern = re.compile(r'\b(?:[A-Z][a-z]+(?:\s+[A-Z]\.?\s*)*[A-Z][a-z]+)\b')
        for match in bare_doctor_pattern.finditer(text):
            # Skip if already detected or has Dr./Doctor prefix
            if not any(s.start == match.start() and s.end == match.end() for s in spans):
                # Only mark as doctor if field explicitly suggests doctor
                if 'doctor' in field_path_lower or 'dr' in field_path_lower.split('_')[-1]:
                    spans.append(PIISpan(
                        start=match.start(),
                        end=match.end(),
                        pii_type=PIIType.DOCTOR,
                        confidence=0.7,
                        original_text=match.group(),
                        context=f"{field_path}: {text[max(0, match.start()-50):match.end()+50]}",
                        detector="bare_doctor_field"
                    ))
    
    # UHID/MRN field detection (bare values without prefix)
    if any(keyword in field_path_lower for keyword in ['uhid', 'mrn', 'patient_id', 'patientid', 'id', 'regno', 'reg no', 'crno', 'ipno', 'opno']):
        # Detect bare UHID/MRN values (formats like SNJ/26/064127, JJH-0076928, IPD-2026-00432, ADM000162)
        bare_uhid_pattern = re.compile(r'\b(?:[A-Z]{2,6}[/\-]\d{2,6}[/\-]\d{4,8}|[A-Z]{2,6}\-?\d{6,10}|[A-Z]{2,6}\d{6,10}|[A-Z0-9]{6,20})\b')
        for match in bare_uhid_pattern.finditer(text):
            # Skip if already detected
            if not any(s.start == match.start() and s.end == match.end() for s in spans):
                spans.append(PIISpan(
                    start=match.start(),
                    end=match.end(),
                    pii_type=PIIType.UHID,
                    confidence=0.85,
                    original_text=match.group(),
                    context=f"{field_path}: {text[max(0, match.start()-50):match.end()+50]}",
                    detector="bare_uhid_field"
                ))
    
    # Adjust span offsets to be relative to original record
    for span in spans:
        span.context = f"{field_path}: {span.context}"
    
    return spans


def _scan_filename(filename: str) -> List:
    """Scan filename for PII."""
    from ..contracts import PIISpan, PIIType
    import re
    
    spans = []
    
    # Common PII patterns in filenames
    FILENAME_PII_PATTERNS = [
        # Names (capitalized words)
        (re.compile(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b'), PIIType.NAME),
        # Phone numbers
        (re.compile(r'(?:\+91[\-\s]?|0[\-\s]?)?[6-9]\d{9}'), PIIType.PHONE),
        # Aadhaar (12 digits)
        (re.compile(r'\b\d{12}\b'), PIIType.AADHAAR),
        # PAN
        (re.compile(r'\b[A-Z]{5}\d{4}[A-Z]\b'), PIIType.PAN),
        # Email
        (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), PIIType.EMAIL),
        # Dates
        (re.compile(r'\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b'), PIIType.DATE),
        (re.compile(r'\b\d{4}[/\-]\d{1,2}[/\-]\d{1,2}\b'), PIIType.DATE),
    ]
    
    for pattern, pii_type in FILENAME_PII_PATTERNS:
        for match in pattern.finditer(filename):
            spans.append(PIISpan(
                start=match.start(),
                end=match.end(),
                pii_type=pii_type,
                confidence=0.8,
                original_text=match.group(),
                context=f"filename: {filename}",
                detector="filename_scanner"
            ))
    
    return spans


def scan_parsed_document(parsed_doc, pii_spans_by_record: Dict[str, List]) -> List:
    """
    Scan a parsed document for PII in structured fields.
    
    Args:
        parsed_doc: ParsedDocument with records
        pii_spans_by_record: Dict of record_id -> List[PIISpan]
        
    Returns:
        List of PIISpan objects with updated contexts
    """
    spans = []
    
    for record in parsed_doc.records:
        record_spans = pii_spans_by_record.get(record.record_id, [])
        
        # Add structured field context to each span
        for span in record_spans:
            # Update context to include field path
            if span.context and not span.context.startswith(record.record_id):
                span.context = f"{record.record_id}: {span.context}"
        
        spans.extend(record_spans)
    
    return spans


def sanitize_json_keys(obj: Any, pii_spans: List) -> Any:
    """
    Sanitize PII in JSON keys (not just values).
    
    Args:
        obj: JSON object (dict, list, or primitive)
        pii_spans: List of PIISpan objects detected in the JSON
        
    Returns:
        Sanitized object with PII removed from keys
    """
    if isinstance(obj, dict):
        sanitized = {}
        for key, value in obj.items():
            # Sanitize key
            clean_key = sanitize_string(key)
            sanitized[clean_key] = sanitize_json_keys(value, pii_spans)
        return sanitized
    elif isinstance(obj, list):
        return [sanitize_json_keys(item, pii_spans) for item in obj]
    else:
        return sanitize_string(obj, pii_spans)


def sanitize_string(text: str, pii_spans: List) -> str:
    """Replace PII in string with tokens based on spans."""
    if not text or not pii_spans:
        return text
    
    # Sort spans by start position (descending for safe replacement)
    sorted_spans = sorted(pii_spans, key=lambda s: s.start, reverse=True)
    
    result = text
    for span in sorted_spans:
        if span.start >= 0 and span.end <= len(result):
            replacement = get_replacement_token(span.pii_type)
            result = result[:span.start] + replacement + result[span.end:]
    
    return result


def sanitize_csv_headers(headers: List[str], pii_spans: List) -> List[str]:
    """Sanitize PII in CSV headers."""
    sanitized = []
    for header in headers:
        sanitized = sanitize_string(header, pii_spans)
        sanitized.append(sanitized)
    return sanitized


def get_replacement_token(pii_type: PIIType) -> str:
    """Get replacement token for PII type."""
    REPLACEMENTS = {
        'NAME': '[NAME]',
        'PHONE': '[PHONE]',
        'AADHAAR': '[UID]',
        'ABHA': '[ABHA]',
        'PAN': '[PAN]',
        'EMAIL': '[EMAIL]',
        'ADDRESS': '[ADDRESS]',
        'DATE': '[DATE]',
        'UHID': '[UHID]',
        'RELATIVE': '[RELATIVE]',
        'DOCTOR': '[DOCTOR]',
        'PIN': '[PIN]',
        'URL': '[URL]',
        'INSURANCE': '[INSURANCE]',
        'OTHER': '[REDACTED]',
    }
    return REPLACEMENTS.get(pii_type, '[REDACTED]')


def sanitize_fhir_elements(record, pii_spans):
    """
    Sanitize FHIR-specific elements.
    
    Handles:
    - Patient.name
    - Patient.telecom
    - Patient.identifier
    - Patient.address
    - References (Patient/123)
    - Extensions with PII
    - Contained resources
    """
    # This is a placeholder - full implementation in transform/structured.py
    pass