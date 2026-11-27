"""
LOCKMATE — Drug and Dosage Detection

Detects drug names, strengths, dosages, frequencies, durations, and routes.
Uses gazetteer for drug names + regex for strengths/frequencies/durations/routes.
"""

from __future__ import annotations

import re
from typing import List

from ..contracts import MedicalSpan, MedicalType
from ..utils.logging import get_logger_adapter
from ..detection.gazetteer import get_gazetteer

logger = get_logger_adapter("clinical.drugs")


# Module-level cached detector state
_drug_cache: dict = {}


def _get_cached_patterns():
    """Get or create cached regex patterns and drug names."""
    global _drug_cache
    if not _drug_cache:
        from ..detection.gazetteer import get_gazetteer
        gazetteer = get_gazetteer()
        drug_names = gazetteer.get("medical_drugs")
        _drug_cache = {
            'drug_names': frozenset(drug_names),
            'dosage_pattern': re.compile(r'\b\d+(?:\.\d+)?\s*(?:mg|g|mL|mcg|IU|U)\b', re.IGNORECASE),
            'frequency_pattern': re.compile(r'\b(?:OD|BD|TID|QID|HS|SOS|PRN|daily|weekly|monthly|stat)\b', re.IGNORECASE),
            'duration_pattern': re.compile(r'\b\d+\s*(?:days?|weeks?|months?|years?)\b', re.IGNORECASE),
            'route_pattern': re.compile(r'\b(?:oral|IV|IM|SC|subcut|inhal|topical|nasal|rectal|vaginal)\b', re.IGNORECASE),
            'strength_pattern': re.compile(r'\b\d+(?:\.\d+)?\s*(?:mg|g|mcg|IU|U)/\s*(?:mL|tablet|cap|caplet)\b', re.IGNORECASE),
        }
    return _drug_cache


def detect_drugs(record) -> List:
    """
    Detect drug names, strengths, dosages, frequencies, durations, and routes.
    
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
    drug_names = cache['drug_names']
    
    # Drug names (from gazetteer) - use pre-compiled patterns
    for drug in drug_names:
        # Use word boundary pattern for drug names
        for match in re.finditer(r'\b' + re.escape(drug) + r'\b', text, re.IGNORECASE):
            spans.append(MedicalSpan(
                start=match.start(),
                end=match.end(),
                medical_type=MedicalType.DRUG,
                confidence=0.95,
                original_text=match.group()
            ))
    
    # Dosage patterns - use cached pattern
    for match in cache['dosage_pattern'].finditer(text):
        spans.append(MedicalSpan(
            start=match.start(),
            end=match.end(),
            medical_type=MedicalType.DOSAGE,
            confidence=0.95,
            original_text=match.group()
        ))
    
    # Frequency patterns - use cached pattern
    for match in cache['frequency_pattern'].finditer(text):
        spans.append(MedicalSpan(
            start=match.start(),
            end=match.end(),
            medical_type=MedicalType.FREQUENCY,
            confidence=0.95,
            original_text=match.group()
        ))
    
    # Duration patterns - use cached pattern
    duration_pattern = re.compile(
        r'\b(?:for\s+)?\d+\s*(?:days?|weeks?|months?|years?)(?=\s*(?:of\s+(?:therapy|treatment|medication)|x\s+\d+|$|,|\.))\b',
        re.IGNORECASE
    )
    for match in duration_pattern.finditer(text):
        spans.append(MedicalSpan(
            start=match.start(),
            end=match.end(),
            medical_type=MedicalType.DURATION,
            confidence=0.9,
            original_text=match.group()
        ))
    
    # Duration patterns with "x" (e.g., "x 5 days", "x 7 days")
    duration_x_pattern = re.compile(
        r'\bx\s+\d+\s*(?:days?|weeks?|months?)\b',
        re.IGNORECASE
    )
    for match in duration_x_pattern.finditer(record.normalized_text):
        spans.append(MedicalSpan(
            start=match.start(),
            end=match.end(),
            medical_type=MedicalType.DURATION,
            confidence=0.9,
            original_text=match.group()
        ))
    
    # Drug strength patterns (e.g., "500 mg", "10 mg/mL", "500mg")
    strength_pattern = re.compile(
        r'\b\d+(?:\.\d+)?\s*(?:mg|g|mL|mcg|IU|U)\b',
        re.IGNORECASE
    )
    for match in strength_pattern.finditer(record.normalized_text):
        spans.append(MedicalSpan(
            start=match.start(),
            end=match.end(),
            medical_type=MedicalType.DOSAGE,
            confidence=0.9,
            original_text=match.group()
        ))
    
    # Route patterns (oral, iv, iv, im, sc, topical, inhalation, sublingual, etc.)
    route_pattern = re.compile(
        r'\b(?:oral|po|iv|i\.v\.|i\.v|im|i\.m\.|sc|s\.c\.|subcut|subcutaneous|topical|inhalation|inhaled|sublingual|sl|rectal|pr|intranasal|intramuscular|intravenous|subcutaneous|transdermal|nasal|ocular|otic|vaginal|buccal|patch|gel|cream|ointment|drops|spray|nebulized|aerosol|suppository|enema)\b',
        re.IGNORECASE
    )
    for match in route_pattern.finditer(record.normalized_text):
        spans.append(MedicalSpan(
            start=match.start(),
            end=match.end(),
            medical_type=MedicalType.ROUTE,
            confidence=0.9,
            original_text=match.group()
        ))
    
    # Combination drug patterns (e.g., "Paracetamol 500mg + Diclofenac 50mg")
    combo_pattern = re.compile(
        r'\b[A-Z][a-z]+(?:\s+\d+(?:\.\d+)?\s*(?:mg|g|mcg|mL))?(?:\s*\+\s*[A-Z][a-z]+(?:\s+\d+(?:\.\d+)?\s*(?:mg|g|mcg|mL))?)+\b'
    )
    for match in combo_pattern.finditer(record.normalized_text):
        spans.append(MedicalSpan(
            start=match.start(),
            end=match.end(),
            medical_type=MedicalType.DRUG,
            confidence=0.9,
            original_text=match.group()
        ))
    
    # Latin dosage abbreviations (e.g., "mane", "nocte", "hora somni", "ante cibum", "post cibum")
    latin_freq_pattern = re.compile(
        r'\b(?:mane|nocte|hora\s+somni|ante\s+cibum|post\s+cibum|ad\s+libitum|s\.o\.s\.|stat|q\.d\.|b\.i\.d\.|t\.i\.d\.|q\.i\.d\.|q\.h\.|q\.2\.h\.|q\.4\.h\.|q\.6\.h\.|q\.8\.h\.|q\.12\.h\.)\b',
        re.IGNORECASE
    )
    for match in latin_freq_pattern.finditer(record.normalized_text):
        spans.append(MedicalSpan(
            start=match.start(),
            end=match.end(),
            medical_type=MedicalType.FREQUENCY,
            confidence=0.95,
            original_text=match.group()
        ))
    
    # Dose with "mg/kg" or "mcg/kg"
    weight_based_dose = re.compile(
        r'\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|mL)\s*/\s*kg\b',
        re.IGNORECASE
    )
    for match in weight_based_dose.finditer(record.normalized_text):
        spans.append(MedicalSpan(
            start=match.start(),
            end=match.end(),
            medical_type=MedicalType.DOSAGE,
            confidence=0.95,
            original_text=match.group()
        ))
    
    return spans