"""
LOCKMATE — Text Replacer with Offset Map Awareness

Performs safe in-place text replacement using offset maps
to handle Unicode normalization correctly.
"""

from __future__ import annotations

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from ..contracts import UnifiedRecord, PIISpan, SanitizedRecord, PIIType
from ..utils.logging import get_logger

logger = get_logger("transform.replacer")


# Default replacement tokens by PII type
DEFAULT_REPLACEMENTS = {
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
    PIIType.URL: "[URL]",
    PIIType.OTHER: "[REDACTED]",
}


@dataclass
class Replacement:
    """A single text replacement operation."""
    start: int           # Start offset in original text
    end: int             # End offset in original text
    replacement: str     # Replacement text
    original_text: str   # Original text being replaced
    pii_type: Optional[object] = None  # PIIType for reference


def apply_replacements(
    text: str,
    replacements: List[Replacement],
    offset_map: Optional[List[Tuple[int, int]]] = None
) -> Tuple[str, List[Tuple[int, int]]]:
    """
    Apply replacements to text using offset maps for correct positioning.
    
    This handles the complexity of replacing text after Unicode normalization
    by working with the original text offsets.
    
    Args:
        text: Original text (not normalized)
        replacements: List of Replacement objects with original offsets
        offset_map: Optional list of (norm_start, norm_end) -> (orig_start, orig_end)
                   mappings from normalization step
        
    Returns:
        Tuple of (transformed_text, new_offset_map)
    """
    if not replacements:
        return text, offset_map or []
    
    # Sort replacements by start offset (descending) for correct indexing
    sorted_replacements = sorted(replacements, key=lambda r: r.start, reverse=True)
    
    # Convert text to list for efficient mutation
    chars = list(text)
    
    # Apply replacements in reverse order to maintain correct indices
    for repl in sorted_replacements:
        # Clamp to valid range
        start = max(0, min(repl.start, len(chars)))
        end = max(start, min(repl.end, len(chars)))
        
        # Replace
        replacement_chars = list(repl.replacement)
        chars[start:end] = replacement_chars
    
    transformed = "".join(chars)
    
    # If we had an offset map, we'd need to update it
    # For Phase 3, we return the original offset_map unchanged
    # (full offset map updating happens in Phase 4 with normalization)
    new_offset_map = offset_map or []
    
    return transformed, new_offset_map


def create_replacements_from_spans(
    record,
    pii_spans,
    replacement_map: Optional[Dict] = None
) -> List:
    """
    Create Replacement objects from PII spans.
    
    Uses the record's offset_map to map normalized offsets back to original text.
    
    Args:
        record: UnifiedRecord with offset_map
        pii_spans: List of PIISpan objects (offsets in normalized_text)
        replacement_map: Optional custom replacement tokens by PIIType
        
    Returns:
        List of Replacement objects with original text offsets
    """
    if replacement_map is None:
        replacement_map = DEFAULT_REPLACEMENTS
    
    replacements = []
    
    # Build reverse offset map: norm_offset -> orig_offset
    norm_to_orig = {}
    for norm_start, norm_end, orig_start, orig_end in record.offset_map:
        norm_to_orig[norm_start] = orig_start
        norm_to_orig[norm_end] = orig_end
    
    for span in pii_spans:
        # Map normalized offsets to original offsets
        orig_start = norm_to_orig.get(span.start, span.start)
        orig_end = norm_to_orig.get(span.end, span.end)
        
        # Get replacement token
        replacement = replacement_map.get(span.pii_type, "[REDACTED]")
        
        replacements.append(Replacement(
            start=orig_start,
            end=orig_end,
            replacement=replacement,
            original_text=span.original_text,
            pii_type=span.pii_type
        ))
    
    return replacements


def replace_in_structured_fields(
    record,
    pii_spans,
    replacement_map: Optional[Dict] = None
) -> Dict[str, str]:
    """
    Replace PII in structured fields using field-level spans.
    
    For Phase 3, this is a placeholder - full implementation in Phase 4
    when we have field-level span tracking.
    
    Args:
        record: UnifiedRecord with fields
        pii_spans: List of PIISpan objects
        replacement_map: Optional custom replacement tokens
        
    Returns:
        Dict of field_path -> sanitized_value
    """
    if replacement_map is None:
        replacement_map = DEFAULT_REPLACEMENTS
    
    # For Phase 3: simple text-based replacement on raw_text
    # Full field-level replacement in Phase 4
    sanitized_text = record.raw_text
    replacements = create_replacements_from_spans(record, pii_spans, replacement_map)
    sanitized_text, _ = apply_replacements(sanitized_text, replacements)
    
    # Update fields that match the replaced text
    sanitized_fields = {}
    for field_name, field_value in record.fields.items():
        if isinstance(field_value.value, str):
            # Simple text replacement in field value
            field_text = field_value.value
            for span in pii_spans:
                if span.original_text in field_text:
                    replacement = replacement_map.get(span.pii_type, "[REDACTED]")
                    field_text = field_text.replace(span.original_text, replacement)
            sanitized_fields[field_name] = field_text
        else:
            sanitized_fields[field_name] = field_value.value
    
    return sanitized_fields


def sanitize_record_text(
    record,
    pii_spans,
    replacement_map: Optional[Dict] = None
) -> SanitizedRecord:
    """
    Main entry point: sanitize a record's text content.
    
    Args:
        record: UnifiedRecord to sanitize
        pii_spans: PII spans detected in record
        replacement_map: Optional custom replacement tokens
        
    Returns:
        SanitizedRecord with transformed text and fields
    """
    if replacement_map is None:
        replacement_map = DEFAULT_REPLACEMENTS
    
    # Create replacements using offset maps
    replacements = create_replacements_from_spans(record, pii_spans, replacement_map)
    
    # Apply to raw text
    transformed_text, _ = apply_replacements(record.raw_text, replacements)
    
    # Sanitize structured fields
    transformed_fields = replace_in_structured_fields(record, pii_spans, replacement_map)
    
    # Determine pseudonym if available
    pseudonym = getattr(record, 'pseudonym', None)
    
    return SanitizedRecord(
        record=record,
        transformed_text=transformed_text,
        transformed_fields=transformed_fields,
        pseudonym=pseudonym
    )