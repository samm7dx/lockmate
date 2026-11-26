"""
LOCKMATE — FHIR Metadata Scanner

Scans FHIR Resource.meta, Bundle.metadata for PII in tags, profiles, security labels.
"""

from __future__ import annotations

from typing import Any, Dict, Generator, List

from ..contracts import PIISpan, PIIType
from ..utils.logging import get_logger

logger = get_logger("parsers.fhir_meta")


def scan_fhir_metadata(resource: Dict) -> List[PIISpan]:
    """
    Scan FHIR resource metadata for PII.
    
    Scans:
    - Resource.meta.tag
    - Resource.meta.profile
    - Resource.meta.security
    - Bundle.metadata (if present)
    
    Args:
        resource: FHIR resource or Bundle dict
        
    Returns:
        List of PIISpan objects
    """
    spans = []
    
    def scan_meta(obj: Any, path: str = "") -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                
                if key == "meta" and isinstance(value, dict):
                    # Scan meta element
                    spans.extend(_scan_meta_element(value, f"{path}.meta"))
                elif key == "metadata" and isinstance(value, dict):
                    # Bundle metadata
                    spans.extend(_scan_metadata_element(value, f"{path}.metadata"))
                else:
                    scan_meta(value, f"{path}.{key}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                scan_meta(item, f"{path}[{i}]")
    
    scan_meta(resource)
    return spans


def _scan_meta_element(meta: Dict, base_path: str) -> List[PIISpan]:
    """Scan FHIR Resource.meta element."""
    import re
    
    spans = []
    
    # Scan tags
    tags = meta.get("tag", [])
    if isinstance(tags, list):
        for i, tag in enumerate(tags):
            if isinstance(tag, dict):
                code = tag.get("code", "")
                display = tag.get("display", "")
                system = tag.get("system", "")
                
                # Check for PII in tag code/display
                for field_name, field_value in [("code", code), ("display", display)]:
                    if isinstance(field_value, str):
                        # Check for name-like patterns
                        if _looks_like_name(field_value):
                            spans.append(PIISpan(
                                start=0,
                                end=len(field_value),
                                pii_type=PIIType.NAME,
                                confidence=0.7,
                                original_text=field_value,
                                context=f"FHIR meta.tag.{field_name} at {base_path}[{i}]",
                                detector="fhir_meta_scanner"
                            ))
    
    # Scan security labels
    security = meta.get("security", [])
    if isinstance(security, list):
        for i, sec in enumerate(security):
            if isinstance(sec, dict):
                code = sec.get("code", "")
                if isinstance(code, str) and _looks_like_name(code):
                    spans.append(PIISpan(
                        start=0,
                        end=len(code),
                        pii_type=PIIType.NAME,
                        confidence=0.6,
                        original_text=code,
                        context=f"FHIR meta.security.code at {base_path}[{i}]",
                        detector="fhir_meta_scanner"
                    ))
    
    return spans


def _scan_metadata_element(metadata: Dict, base_path: str) -> List[PIISpan]:
    """Scan Bundle.metadata element."""
    import re
    
    spans = []
    
    # Bundle metadata can contain various fields
    # Check common fields that might contain PII
    for key, value in metadata.items():
        if isinstance(value, str):
            if _looks_like_name(value):
                spans.append(PIISpan(
                    start=0,
                    end=len(value),
                    pii_type=PIIType.NAME,
                    confidence=0.6,
                    original_text=value,
                    context=f"FHIR Bundle.metadata.{key} at {base_path}",
                    detector="fhir_meta_scanner"
                ))
    
    return spans


def _looks_like_name(value: str) -> bool:
    """Heuristic to detect if string looks like a person name."""
    import re
    
    if not value or len(value) < 2:
        return False
    
    # Check for name patterns
    # - Contains space or hyphen between capitalized words
    # - Not a UUID, not all digits, not a code system URL
    
    if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', value, re.I):
        return False  # UUID
    
    if re.match(r'^\d+$', value):
        return False  # All digits
    
    if value.startswith("http://") or value.startswith("https://") or value.startswith("urn:"):
        return False  # URL/URN
    
    # Check for name pattern: capitalized words separated by space/hyphen
    words = re.split(r'[\s\-]+', value)
    if len(words) >= 2:
        capitalized_count = sum(1 for w in words if w and w[0].isupper())
        if capitalized_count >= 2:
            return True
    
    # Single capitalized word could be a name
    if len(words) == 1 and words[0] and words[0][0].isupper() and len(words[0]) > 2:
        # Could be a surname
        return True
    
    return False