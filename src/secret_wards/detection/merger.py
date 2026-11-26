"""
LOCKMATE — Span Merger with Medical Veto

Merges PII spans with medical veto logic (Phase 3).
"""

from __future__ import annotations

from typing import List, Optional

from ..contracts import PIISpan, MedicalSpan, PIIType, MedicalType
from ..utils.logging import get_logger

logger = get_logger("detection.merger")


def merge_spans_with_veto(
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


def merge_overlapping_spans(spans: List) -> List:
    """
    Merge overlapping spans of the same type.
    
    Args:
        spans: List of spans (PIISpan or MedicalSpan)
        
    Returns:
        List of merged spans
    """
    if not spans:
        return []
    
    # Sort by start position
    sorted_spans = sorted(spans, key=lambda s: (s.start, s.end))
    
    merged = []
    current = sorted_spans[0]
    
    for span in sorted_spans[1:]:
        # Check if same type and overlapping/adjacent
        if (hasattr(current, 'pii_type') and hasattr(span, 'pii_type') and 
            current.pii_type == span.pii_type and
            span.start <= current.end + 1):
            # Merge: extend end to max of both
            current.end = max(current.end, span.end)
            current.original_text = current.original_text + span.original_text
        elif (hasattr(current, 'medical_type') and hasattr(span, 'medical_type') and
              current.medical_type == span.medical_type and
              span.start <= current.end + 1):
            current.end = max(current.end, span.end)
            current.original_text = current.original_text + span.original_text
        else:
            merged.append(current)
            current = span
    
    merged.append(current)
    return merged


def filter_spans_by_confidence(
    spans: List,
    min_confidence: float = 0.5
) -> List:
    """
    Filter spans by minimum confidence threshold.
    
    Args:
        spans: List of spans with confidence attribute
        min_confidence: Minimum confidence threshold (0.0-1.0)
        
    Returns:
        Filtered list of spans
    """
    filtered = [s for s in spans if getattr(s, 'confidence', 1.0) >= min_confidence]
    
    if len(filtered) < len(spans):
        logger.debug("confidence_filter_applied",
                    original=len(spans),
                    filtered=len(filtered),
                    threshold=min_confidence)
    
    return filtered


def merge_pii_and_medical(
    pii_spans: List,
    medical_spans: List,
    adjacency_threshold: int = 5
) -> List:
    """
    Convenience function: apply medical veto then merge overlapping PII spans.
    
    Args:
        pii_spans: List of PIISpan objects
        medical_spans: List of MedicalSpan objects
        adjacency_threshold: Character distance for adjacency check
        
    Returns:
        Final list of PIISpan objects after veto and merging
    """
    # Step 1: Apply medical veto
    vetoed = merge_spans_with_veto(pii_spans, medical_spans, adjacency_threshold)
    
    # Step 2: Merge overlapping PII spans of same type
    merged = merge_overlapping_spans(vetoed)
    
    return merged