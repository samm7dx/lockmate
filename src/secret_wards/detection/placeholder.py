"""
LOCKMATE — Placeholder PII Detection (Phase 3)

Basic regex-based PII detection for initial pipeline validation.
Replaced by production-grade detection in Phase 4.
"""

from __future__ import annotations

import re
from typing import List, Optional

from ..contracts import UnifiedRecord, PIISpan, PIIType
from ..utils.logging import get_logger

logger = get_logger("detection.placeholder")


# Pre-compiled regex patterns for performance
EMAIL_PATTERN = re.compile(
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
)

# Indian phone: +91/0 prefix optional, 10 digits starting 6-9
PHONE_PATTERN = re.compile(
    r'(?:\+91[\-\s]?|0[\-\s]?)?[6-9]\d{9}\b'
)

# PAN: 5 letters + 4 digits + 1 letter
PAN_PATTERN = re.compile(
    r'\b[A-Z]{5}\d{4}[A-Z]\b'
)

# 12-digit numbers (potential Aadhaar)
AADHAAR_PATTERN = re.compile(
    r'\b\d{12}\b'
)

# Date patterns (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, etc.)
DATE_PATTERNS = [
    re.compile(r'\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b'),  # DD/MM/YYYY or DD-MM-YYYY
    re.compile(r'\b\d{4}[/\-]\d{1,2}[/\-]\d{1,2}\b'),    # YYYY-MM-DD
    re.compile(r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}\b', re.IGNORECASE),  # DD Mon YYYY
]


def detect_pii_placeholder(record: UnifiedRecord) -> List[PIISpan]:
    """
    Detect PII using simple regex patterns (placeholder implementation).
    
    Detects: email, phone, PAN, 12-digit numbers, dates
    
    Args:
        record: UnifiedRecord with normalized_text
        
    Returns:
        List of PIISpan objects
    """
    spans = []
    text = record.normalized_text
    
    if not text:
        return spans
    
    # Email detection
    for match in EMAIL_PATTERN.finditer(text):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.EMAIL,
            confidence=0.95,
            original_text=match.group(),
            context=text[max(0, match.start()-50):match.end()+50],
            detector="placeholder_email"
        ))
    
    # Phone detection
    for match in PHONE_PATTERN.finditer(text):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.PHONE,
            confidence=0.85,
            original_text=match.group(),
            context=text[max(0, match.start()-50):match.end()+50],
            detector="placeholder_phone"
        ))
    
    # PAN detection
    for match in PAN_PATTERN.finditer(text):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.PAN,
            confidence=0.98,
            original_text=match.group(),
            context=text[max(0, match.start()-50):match.end()+50],
            detector="placeholder_pan"
        ))
    
    # 12-digit number detection (potential Aadhaar)
    for match in AADHAAR_PATTERN.finditer(text):
        # Avoid overlapping with phone numbers
        matched_text = match.group()
        is_phone = bool(PHONE_PATTERN.match(matched_text))
        if not is_phone:
            spans.append(PIISpan(
                start=match.start(),
                end=match.end(),
                pii_type=PIIType.AADHAAR,
                confidence=0.7,
                original_text=matched_text,
                context=text[max(0, match.start()-50):match.end()+50],
                detector="placeholder_aadhaar"
            ))
    
    # Date detection
    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(text):
            spans.append(PIISpan(
                start=match.start(),
                end=match.end(),
                pii_type=PIIType.DATE,
                confidence=0.8,
                original_text=match.group(),
                context=text[max(0, match.start()-50):match.end()+50],
                detector="placeholder_date"
            ))
    
    logger.debug("placeholder_pii_detected", 
                record_id=record.record_id,
                span_count=len(spans))
    
    return spans


def detect_medical_placeholder(record: UnifiedRecord) -> List:
    """
    Detect medical expressions that should be preserved (placeholder).
    
    Detects: dosages (N mg), frequencies (OD, BD, TDS), disease names (Parkinson's)
    
    Returns:
        List of MedicalSpan objects (using PIISpan for now, will be replaced)
    """
    from ..contracts import MedicalSpan, MedicalType
    
    spans = []
    text = record.normalized_text
    
    if not text:
        return spans
    
    # Dosage pattern: N mg, N g, N mL, N mcg, N IU, N U
    dosage_pattern = re.compile(
        r'\b\d+(?:\.\d+)?\s*(?:mg|g|mL|mcg|IU|U)\b',
        re.IGNORECASE
    )
    for match in dosage_pattern.finditer(text):
        spans.append(MedicalSpan(
            start=match.start(),
            end=match.end(),
            medical_type=MedicalType.DOSAGE,
            confidence=0.95,
            original_text=match.group()
        ))
    
    # Frequency patterns
    freq_pattern = re.compile(
        r'\b(?:OD|BD|TDS|QID|SOS|once\s+daily|twice\s+daily|thrice\s+daily|once\s+a\s+day|twice\s+a\s+day|three\s+times\s+a\s+day)\b',
        re.IGNORECASE
    )
    for match in freq_pattern.finditer(text):
        spans.append(MedicalSpan(
            start=match.start(),
            end=match.end(),
            medical_type=MedicalType.FREQUENCY,
            confidence=0.95,
            original_text=match.group()
        ))
    
    # Disease names (eponyms that look like names)
    disease_pattern = re.compile(
        r"\b(?:Parkinson's|Alzheimer's|Crohn's|Diabetes|Hypertension|TB|HIV|AIDS|Cancer|Asthma|Arthritis|Osteoporosis|Anemia|Leukemia|Lymphoma|Melanoma|Carcinoma|Sarcoma)\b",
        re.IGNORECASE
    )
    for match in disease_pattern.finditer(text):
        spans.append(MedicalSpan(
            start=match.start(),
            end=match.end(),
            medical_type=MedicalType.DIAGNOSIS,
            confidence=0.98,
            original_text=match.group()
        ))
    
    # Drug names (common Indian brands + INN)
    drug_pattern = re.compile(
        r'\b(?:Paracetamol|Dolo|Crocin|Calpol|Metformin|Aspirin|Ibuprofen|Diclofenac|Amoxicillin|Azithromycin|Ciprofloxacin|Metronidazole|Omeprazole|Ranitidine|Pantoprazole|Atorvastatin|Amlodipine|Losartan|Metoprolol|Insulin|Glimepiride|Gliclazide|Pioglitazone|Sitagliptin|Linagliptin|Empagliflozin|Dapagliflozin|Canagliflozin)\b',
        re.IGNORECASE
    )
    for match in drug_pattern.finditer(text):
        spans.append(MedicalSpan(
            start=match.start(),
            end=match.end(),
            medical_type=MedicalType.DRUG,
            confidence=0.95,
            original_text=match.group()
        ))
    
    return spans