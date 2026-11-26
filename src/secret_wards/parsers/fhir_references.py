"""
LOCKMATE — FHIR Reference Scanner

Scans FHIR resources for PII in reference fields, contained resources,
and extension URLs/values.
"""

from __future__ import annotations

from typing import Any, Dict, Generator, List, Optional, Set

from ..contracts import PIISpan, PIIType
from ..utils.logging import get_logger

logger = get_logger("parsers.fhir_references")


def scan_fhir_references(resource: Dict) -> List[PIISpan]:
    """
    Scan FHIR resource for PII in reference fields.
    
    Scans:
    - reference fields (Patient, Practitioner, Organization, etc.)
    - contained resources
    - extension URLs and values
    
    Args:
        resource: FHIR resource dict
        
    Returns:
        List of PIISpan objects
    """
    spans = []
    
    def scan_dict(obj: Any, path: str = "") -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                
                if key == "reference" and isinstance(value, str):
                    # Scan reference string for PII
                    spans.extend(_scan_reference_string(value, new_path))
                elif key == "contained" and isinstance(value, list):
                    # Recursively scan contained resources
                    for i, contained in enumerate(value):
                        scan_dict(contained, f"{new_path}[{i}]")
                elif key == "extension" and isinstance(value, list):
                    # Scan extensions
                    for i, ext in enumerate(value):
                        scan_dict(ext, f"{new_path}.extension[{i}]")
                else:
                    scan_dict(value, new_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                scan_dict(item, f"{path}[{i}]")
    
    scan_dict(resource)
    return spans


def _scan_reference_string(reference: str, path: str) -> List[PIISpan]:
    """
    Scan FHIR reference string for PII.
    
    Reference format: "ResourceType/id" or "ResourceType/identifier-system|value"
    May contain names, IDs, etc. in the reference string itself.
    """
    import re
    
    spans = []
    
    # Reference may contain PII in the ID portion
    # e.g., "Patient/rahul-sharma" or "Practitioner/dr-rahul"
    # We'll flag references that appear to contain names
    
    # Check for name-like patterns in reference
    # Simple heuristic: if reference contains lowercase letters and hyphens
    # that look like a name (not a UUID or numeric ID)
    if re.search(r'/[a-z]+(?:-[a-z]+)+$', reference):
        spans.append(PIISpan(
            start=0,  # Will be adjusted by caller
            end=len(reference),
            pii_type=PIIType.NAME,
            confidence=0.6,
            original_text=reference,
            context=f"FHIR reference at {path}",
            detector="fhir_reference_scanner"
        ))
    
    return spans


def extract_references(resource: Dict) -> List[str]:
    """
    Extract all reference strings from a FHIR resource.
    
    Returns:
        List of reference strings (e.g., "Patient/123", "Practitioner/abc")
    """
    references = []
    
    def extract(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "reference" and isinstance(value, str):
                    references.append(value)
                else:
                    extract(value)
        elif isinstance(obj, list):
            for item in obj:
                extract(item)
    
    extract(resource)
    return references


def extract_contained_resources(resource: Dict) -> List[Dict]:
    """
    Extract all contained resources from a FHIR resource.
    
    Returns:
        List of contained resource dicts
    """
    contained = []
    
    def extract(obj: Any) -> None:
        if isinstance(obj, dict):
            if "contained" in obj and isinstance(obj["contained"], list):
                contained.extend(obj["contained"])
            for value in obj.values():
                extract(value)
        elif isinstance(obj, list):
            for item in obj:
                extract(item)
    
    extract(resource)
    return contained