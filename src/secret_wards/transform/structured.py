"""
LOCKMATE — Structured Field Sanitizer

Sanitizes PII in structured fields (CSV columns, JSON values, FHIR elements)
while preserving field structure and types.
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from ..contracts import (
    ParsedDocument, UnifiedRecord, SanitizedRecord, FieldValue,
    PIISpan, PIIType
)
from ..transform.replacer import DEFAULT_REPLACEMENTS, sanitize_record_text
from ..utils.logging import get_logger_adapter

logger = get_logger_adapter("transform.structured")


def sanitize_parsed_document(
    parsed_doc,
    pii_spans_by_record: Dict[str, List],
    replacement_map: Optional[Dict] = None
) -> List:
    """
    Sanitize all records in a parsed document.
    
    Args:
        parsed_doc: ParsedDocument with records
        pii_spans_by_record: Dict of record_id -> List[PIISpan]
        replacement_map: Optional custom replacement tokens
        
    Returns:
        List of SanitizedRecord objects
    """
    if replacement_map is None:
        from ..transform.replacer import DEFAULT_REPLACEMENTS
        replacement_map = DEFAULT_REPLACEMENTS
    
    sanitized_records = []
    
    for record in parsed_doc.records:
        pii_spans = pii_spans_by_record.get(record.record_id, [])
        sanitized = sanitize_record_text(record, pii_spans)
        sanitized_records.append(sanitized)
    
    return sanitized_records


def sanitize_csv_fields(
    record,
    pii_spans,
    replacement_map: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Sanitize CSV/TSV field values.
    
    Args:
        record: UnifiedRecord with CSV fields
        pii_spans: PII spans detected in record
        replacement_map: Optional custom replacement tokens
        
    Returns:
        Dict of field_name -> sanitized_value
    """
    if replacement_map is None:
        replacement_map = DEFAULT_REPLACEMENTS
    
    sanitized = {}
    
    for field_name, field_value in record.fields.items():
        if isinstance(field_value.value, str):
            original = field_value.value
            sanitized_value = original
            
            # Check if any PII span text appears in this field
            for span in pii_spans:
                if span.original_text in original:
                    replacement = DEFAULT_REPLACEMENTS.get(span.pii_type, "[REDACTED]")
                    sanitized_value = sanitized_value.replace(span.original_text, replacement)
            
            sanitized[field_name] = sanitized_value
        else:
            sanitized[field_name] = field_value.value
    
    return sanitized


def sanitize_json_fields(
    record,
    pii_spans,
    replacement_map: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Sanitize JSON field values (including nested structures).
    
    Args:
        record: UnifiedRecord with JSON fields
        pii_spans: PII spans detected in record
        replacement_map: Optional custom replacement tokens
        
    Returns:
        Dict of field_path -> sanitized_value
    """
    if replacement_map is None:
        replacement_map = DEFAULT_REPLACEMENTS
    
    sanitized = {}
    
    for field_path, field_value in record.fields.items():
        sanitized[field_path] = _sanitize_json_value(
            field_value.value, pii_spans, replacement_map
        )
    
    return sanitized


def _sanitize_json_value(
    value: Any,
    pii_spans,
    replacement_map: Dict
) -> Any:
    """Recursively sanitize JSON values."""
    if isinstance(value, str):
        sanitized = value
        for span in pii_spans:
            if span.original_text in sanitized:
                replacement = DEFAULT_REPLACEMENTS.get(span.pii_type, "[REDACTED]")
                sanitized = sanitized.replace(span.original_text, replacement)
        return sanitized
    elif isinstance(value, dict):
        return {k: _sanitize_json_value(v, pii_spans, DEFAULT_REPLACEMENTS) for k, v in value.items()}
    elif isinstance(value, list):
        return [_sanitize_json_value(item, pii_spans, DEFAULT_REPLACEMENTS) for item in value]
    else:
        return value


def sanitize_fhir_elements(
    record,
    pii_spans,
    replacement_map: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Sanitize FHIR resource elements.
    
    Handles FHIR-specific structures like references, extensions, contained resources.
    
    Args:
        record: UnifiedRecord with FHIR fields
        pii_spans: PII spans detected in record
        replacement_map: Optional custom replacement tokens
        
    Returns:
        Dict of field_path -> sanitized_value
    """
    if replacement_map is None:
        replacement_map = DEFAULT_REPLACEMENTS
    
    sanitized = {}
    
    for field_path, field_value in record.fields.items():
        sanitized[field_path] = _sanitize_fhir_value(
            field_value.value, field_path, pii_spans, replacement_map
        )
    
    return sanitized


def _sanitize_fhir_value(
    value: Any,
    field_path: str,
    pii_spans,
    replacement_map: Dict
) -> Any:
    """Sanitize FHIR-specific values with path awareness."""
    if isinstance(value, str):
        # Check for FHIR reference fields
        if field_path.endswith(".reference") or "reference" in field_path:
            # Don't sanitize resource references (e.g., "Patient/123")
            # but do sanitize if they contain PII-like patterns
            sanitized = value
            for span in pii_spans:
                if span.original_text in sanitized:
                    replacement = DEFAULT_REPLACEMENTS.get(span.pii_type, "[REDACTED]")
                    sanitized = sanitized.replace(span.original_text, replacement)
            return sanitized
        
        # Check for FHIR primitive value fields
        if any(field_path.endswith(f".value{suffix}") for suffix in 
               ["String", "Code", "Date", "DateTime", "Instant", "Time", "Uri", "Url", "Canonical", "Oid", "Uuid"]):
            sanitized = value
            for span in pii_spans:
                if span.original_text in sanitized:
                    replacement = DEFAULT_REPLACEMENTS.get(span.pii_type, "[REDACTED]")
                    sanitized = sanitized.replace(span.original_text, replacement)
            return sanitized
        
        # Generic string sanitization
        sanitized = value
        for span in pii_spans:
            if span.original_text in sanitized:
                replacement = DEFAULT_REPLACEMENTS.get(span.pii_type, "[REDACTED]")
                sanitized = sanitized.replace(span.original_text, replacement)
        return sanitized
    
    elif isinstance(value, dict):
        # Handle FHIR complex types (Quantity, Coding, CodeableConcept, etc.)
        if "resourceType" in value:
            # Contained resource - recursively sanitize
            sanitized = {}
            for k, v in value.items():
                sanitized[k] = _sanitize_fhir_value(v, f"{field_path}.{k}", pii_spans, DEFAULT_REPLACEMENTS)
            return sanitized
        else:
            return {k: _sanitize_fhir_value(v, f"{field_path}.{k}", pii_spans, DEFAULT_REPLACEMENTS) 
                    for k, v in value.items()}
    elif isinstance(value, list):
        return [_sanitize_fhir_value(item, f"{field_path}[{i}]", pii_spans, DEFAULT_REPLACEMENTS) 
                for i, item in enumerate(value)]
    else:
        return value


def inject_pseudonym_into_record(
    record,
    sanitized_record,
    pseudonym: str,
    format_type: str
) -> None:
    """
    Inject pseudonym into the sanitized record's structured fields.
    
    Modifies sanitized_record.transformed_fields in place.
    
    Args:
        record: Original UnifiedRecord
        sanitized_record: SanitizedRecord to modify
        pseudonym: Pseudonym string (e.g., "PSN-a1b2c3d4")
        format_type: Source format (csv, tsv, json, fhir, text)
    """
    if not pseudonym:
        return
    
    # CSV/TSV: inject into patient_id or similar field
    if format_type in ("csv", "tsv"):
        for field_name in ["patient_id", "patientid", "id", "subject_id", "mrn", "uhid"]:
            if field_name in sanitized_record.transformed_fields:
                sanitized_record.transformed_fields[field_name] = pseudonym
                break
    
    # JSON: inject into patient.id or subject.reference
    elif format_type == "json":
        if "patient.id" in sanitized_record.transformed_fields:
            sanitized_record.transformed_fields["patient.id"] = pseudonym
        elif "subject.reference" in sanitized_record.transformed_fields:
            sanitized_record.transformed_fields["subject.reference"] = f"Patient/{pseudonym}"
        elif "id" in sanitized_record.transformed_fields:
            sanitized_record.transformed_fields["id"] = pseudonym
    
    # FHIR: inject into Patient.identifier or subject.reference
    elif format_type == "fhir":
        if "Patient.identifier" in sanitized_record.transformed_fields:
            # This would need proper FHIR identifier structure
            sanitized_record.transformed_fields["Patient.identifier"] = [{"value": pseudonym}]
        elif "subject.reference" in sanitized_record.transformed_fields:
            sanitized_record.transformed_fields["subject.reference"] = f"Patient/{pseudonym}"