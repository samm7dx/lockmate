"""
LOCKMATE — Medical Veto Integration

Integrates PII spans with medical spans for contextual veto logic.
"""

from __future__ import annotations

from typing import List

from ..contracts import PIISpan, MedicalSpan, PIIType, MedicalType
from ..utils.logging import get_logger_adapter
from .doctors import detect_doctors
from .drugs import detect_drugs
from .labs import detect_labs
from .diagnoses import detect_diagnoses

logger = get_logger_adapter("clinical.veto")


def _merge_spans_with_veto(
    pii_spans: List,
    medical_spans: List,
    adjacency_threshold: int = 5
) -> List:
    """
    Merge PII spans with medical veto logic.
    
    Rules:
    1. Medical spans veto overlapping PII spans (medical wins)
    2. PII spans adjacent to medical spans (within threshold) are re-evaluated
    3. Non-overlapping, non-adjacent PII spans are kept
    
    Args:
        pii_spans: List of PIISpan objects
        medical_spans: List of MedicalSpan objects
        adjacency_threshold: Character distance for adjacency check
        
    Returns:
        Filtered list of PIISpan objects after medical veto
    """
    if not pii_spans:
        return []
    
    if not medical_spans:
        return pii_spans
    
    # Sort spans by start position for efficient processing
    sorted_pii = sorted(pii_spans, key=lambda s: s.start)
    sorted_medical = sorted(medical_spans, key=lambda s: s.start)
    
    filtered = []
    vetoed_count = 0
    
    for pii in sorted_pii:
        # Check if any medical span overlaps or is adjacent
        vetoed = False
        
        for med in sorted_medical:
            # Medical span ends before PII starts - no overlap possible for later medical spans
            if med.end < pii.start - adjacency_threshold:
                continue
            
            # Medical span starts after PII ends + threshold - no overlap for this or later medical spans
            if med.start > pii.end + adjacency_threshold:
                break
            
            # Check overlap
            if not (pii.end <= med.start or med.end <= pii.start):
                # Overlap detected - medical wins
                vetoed = True
                vetoed_count += 1
                logger.debug("pii_vetoed_by_medical_overlap",
                            pii_type=pii.pii_type.value,
                            pii_text=pii.original_text,
                            med_type=med.medical_type.value,
                            med_text=med.original_text)
                break
            
            # Check adjacency (within threshold chars)
            if abs(pii.start - med.end) <= adjacency_threshold or abs(pii.end - med.start) <= adjacency_threshold:
                # Adjacent - re-evaluate
                # For placeholder: be conservative and DON'T veto on adjacency alone
                # Real implementation would have more sophisticated logic
                pass
        
        if not vetoed:
            filtered.append(pii)
    
    if vetoed_count > 0:
        logger.debug("medical_veto_applied",
                    original_count=len(pii_spans),
                    vetoed_count=vetoed_count,
                    remaining_count=len(filtered))
    
    return filtered


def detect_all_medical_spans(record) -> List:
    """
    Detect all medical spans in a record.
    
    Combines detections from:
    - Drugs/dosages/frequencies/durations
    - Labs/vitals/units
    - Diagnoses/procedures
    - Doctor names in clinical context
    
    Args:
        record: UnifiedRecord with normalized_text
        
    Returns:
        List of MedicalSpan objects
    """
    from .drugs import detect_drugs
    from .labs import detect_labs
    from .diagnoses import detect_diagnoses
    from .doctors import detect_doctors
    
    all_spans = []
    
    # Collect all medical spans
    all_spans.extend(detect_drugs(record))
    all_spans.extend(detect_labs(record))
    all_spans.extend(detect_diagnoses(record))
    all_spans.extend(detect_doctors(record))
    
    # Sort by position
    all_spans.sort(key=lambda s: s.start)
    
    return all_spans


def merge_spans_with_veto(
    pii_spans: List,
    medical_spans: List,
    adjacency_threshold: int = 5
) -> List:
    """
    Merge PII spans with medical veto logic.
    
    This is the main entry point for the medical veto logic.
    """
    return _merge_spans_with_veto(pii_spans, medical_spans, adjacency_threshold)