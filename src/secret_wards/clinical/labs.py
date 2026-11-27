"""
LOCKMATE — Lab, Vital, and Unit Detection

Detects laboratory names, vital signs, and clinical units.
"""

from __future__ import annotations

import re
from typing import List

from ..contracts import MedicalSpan, MedicalType
from ..utils.logging import get_logger_adapter

logger = get_logger_adapter("clinical.labs")


# Module-level cached patterns
_labs_cache: dict = {}


def _get_cached_patterns():
    """Get or create cached regex patterns and lab names."""
    global _labs_cache
    if not _labs_cache:
        from ..detection.gazetteer import get_gazetteer
        gazetteer = get_gazetteer()
        _labs_cache = {
            'lab_names': frozenset(gazetteer.get("medical_labs")),
            'vital_patterns': [
                re.compile(r'\bBP\s+\d{2,3}\s*/\s*\d{2,3}\b', re.IGNORECASE),
                re.compile(r'\bBlood\s+Pressure\s+\d{2,3}\s*/\s*\d{2,3}\b', re.IGNORECASE),
                re.compile(r'\b(?:HR|Heart\s+Rate|Pulse)\s*[:]?\s*\d{2,3}\b', re.IGNORECASE),
                re.compile(r'\bPulse\s*[:]?\s*\d{2,3}\b', re.IGNORECASE),
                re.compile(r'\bRR\s*[:]?\s*\d{1,2}\b', re.IGNORECASE),
                re.compile(r'\bTemp(?:erature)?\s*[:]?\s*\d{2,3}(?:\.\d)?\s*(?:[CF])\b', re.IGNORECASE),
                re.compile(r'\bSpO2\s*[:]?\s*\d{2,3}\b', re.IGNORECASE),
                re.compile(r'\bSAT\s*[:]?\s*\d{2,3}\b', re.IGNORECASE),
            ],
            'unit_patterns': {
                MedicalType.UNIT: re.compile(
                    r'\b(?:mg/dL|mg/dl|mmol/L|mmol/l|mg/mL|mg/ml|IU/L|IU/l|U/L|U/l|ng/mL|ng/ml|pg/mL|pg/ml|mEq/L|meq/L|mEq/L)\b',
                    re.IGNORECASE
                ),
            },
        }
    return _labs_cache


def detect_labs(record) -> List:
    """
    Detect lab names, vital signs, and units.
    
    Args:
        record: UnifiedRecord with normalized_text
        
    Returns:
        List of MedicalSpan objects
    """
    from ..contracts import MedicalSpan, MedicalType
    
    spans = []
    text = record.normalized_text
    
    if not text:
        return spans
    
    cache = _get_cached_patterns()
    lab_names = cache['lab_names']
    
    # Lab names (from gazetteer - LOINC-derived) - use pre-compiled patterns
    for lab in lab_names:
        for match in re.finditer(r'\b' + re.escape(lab) + r'\b', text, re.IGNORECASE):
            spans.append(MedicalSpan(
                start=match.start(),
                end=match.end(),
                medical_type=MedicalType.LAB,
                confidence=0.9,
                original_text=match.group()
            ))
    
    # Vital patterns - use cached patterns
    for med_type, patterns in cache['vital_patterns'].items():
        for pattern in patterns:
            for match in pattern.finditer(text):
                spans.append(MedicalSpan(
                    start=match.start(),
                    end=match.end(),
                    medical_type=med_type,
                    confidence=0.9,
                    original_text=match.group()
                ))
    
    # Unit patterns
    for med_type, pattern in cache['unit_patterns'].items():
        for match in pattern.finditer(text):
            spans.append(MedicalSpan(
                start=match.start(),
                end=match.end(),
                medical_type=med_type,
                confidence=0.9,
                original_text=match.group()
            ))
    
    # Additional lab value patterns - use cached patterns
    # Lab values with numbers and units (e.g., "Hb 12.5 g/dL", "Creatinine 1.2 mg/dL")
    for match in cache.get('lab_value_pattern', re.compile('')).finditer(text):
        spans.append(MedicalSpan(
            start=match.start(),
            end=match.end(),
            medical_type=MedicalType.LAB,
            confidence=0.85,
            original_text=match.group()
        ))
    
    # Additional unit patterns - only with clear numeric values in medical context
    additional_units = [
        r'\b\d+(?:\.\d+)?\s*(?:cc|mL|mL/hr|mL/min|mL/kg|drops?|gtt)\b',  # infusion rates with numbers
    ]
    for pattern_str in additional_units:
        pattern = re.compile(pattern_str, re.IGNORECASE)
        for match in pattern.finditer(record.normalized_text):
            spans.append(MedicalSpan(
                start=match.start(),
                end=match.end(),
                medical_type=MedicalType.UNIT,
                confidence=0.85,
                original_text=match.group()
            ))
    
    return spans