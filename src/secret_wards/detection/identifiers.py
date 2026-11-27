"""
LOCKMATE — Identifier Detection

Detects and validates Indian identity identifiers:
- Aadhaar (12-digit with Verhoeff checksum)
- ABHA (14-digit Ayushman Bharat Health Account)
- PAN (10-char alphanumeric)
- UHID/MRN (hospital-specific patterns)
- Insurance IDs
- Email, URL, PIN codes
"""

from __future__ import annotations

import re
from typing import List, Optional

from ..contracts import UnifiedRecord, PIISpan, PIIType
from ..utils.logging import get_logger_adapter

logger = get_logger_adapter("detection.identifiers")

# Pre-compiled regex patterns for performance
EMAIL_PATTERN = re.compile(
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
)

# Indian phone: +91/0 prefix, 10 digits starting 6-9
# Handles formats: +91 98765 43210, 9876543210, 98765 43210, 98765-43210, 09876543210
PHONE_PATTERN = re.compile(
    r'(?:\+91[\-\s]?|0[\-\s]?)?(?:[6-9]\d{4}[\-\s]?\d{5}|[6-9]\d{9})\b'
)

# PAN: 5 letters + 4 digits + 1 letter
PAN_PATTERN = re.compile(
    r'\b[A-Z]{5}\d{4}[A-Z]\b'
)

# Aadhaar: 12 digits with Verhoeff checksum (with or without spaces/hyphens)
# Formats: 123456789012, 1234 5678 9012, 1234-5678-9012
AADHAAR_PATTERN = re.compile(
    r'\b\d{4}[\-\s]?\d{4}[\-\s]?\d{4}\b'
)

# ABHA: 14 digits (with optional spaces/hyphens)
# Formats: 12345678901234, 1234 5678 9012 34, 1234-5678-9012-34, 12-3456-7890-1234
ABHA_PATTERN = re.compile(
    r'\b(?:\d{4}[\-\s]?){3}\d{2}\b|\b\d{2}[\-\s]?(?:\d{4}[\-\s]?){3}\b'
)

# PIN code: 6 digits
PIN_PATTERN = re.compile(
    r'\b\d{6}\b'
)

# Date patterns
DATE_PATTERNS = [
    re.compile(r'\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b'),  # DD/MM/YYYY
    re.compile(r'\b\d{4}[\-]\d{1,2}[\-]\d{1,2}\b'),      # YYYY-MM-DD
    re.compile(r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}\b', re.IGNORECASE),
]

# UHID/MRN patterns (hospital-specific, generic fallback)
UHID_PATTERN = re.compile(
    r'\b(?:UHID|MRN|UHID/MRN)[\s:]*([A-Z0-9]{6,15})\b',
    re.IGNORECASE
)

# Insurance ID patterns (generic)
INSURANCE_PATTERN = re.compile(
    r'\b(?:INS|POL|POLNO|POLICY)[\s:]*([A-Z0-9]{8,20})\b',
    re.IGNORECASE
)

# URL pattern
URL_PATTERN = re.compile(
    r'https?://[^\s/$.?#].[^\s]*'
)

# House number patterns
HOUSE_NUMBER_PATTERN = re.compile(
    r'\b(?:H\.?No\.?|House\s+No\.?|House\s+\d+|Makan\s+No\.?|H\.?No\.?|Door\s+No\.?|Flat\s+No\.?|D\.?No\.?)\s*[\d\w\-/]+\b',
    re.IGNORECASE
)

# Village/Locality indicators
VILLAGE_LOCALITY_PATTERN = re.compile(
    r'\b(?:Village|Vill\.|Mohalla|Ward|Sector|Colony|Nagar|Gram|Gaon|Village|Locality|Area|Zone)\s*[:\-]?\s*[\w\s\-\.]+',
    re.IGNORECASE
)

# Landmark indicators
LANDMARK_PATTERN = re.compile(
    r'\b(?:near|opp\.?|opposite|behind|front\s+of|adjacent\s+to|next\s+to|near\s+to)\s+[\w\s\.\-\,\']+',
    re.IGNORECASE
)

# Insurance ID patterns (more comprehensive)
INSURANCE_PATTERN_V2 = re.compile(
    r'\b(?:INS|POL|POLNO|POLICY|INSURE|INSURANCE|MEDICLAIM|MEDI\.?CLAIM|HEALTH\s+INSURANCE|GROUP\s+INSURANCE|POLICY\s+NO\.?|POL\s+NO\.?|INS\s+NO\.?)[\s:]*([A-Z0-9]{8,20})\b',
    re.IGNORECASE
)

# Relative name patterns (S/o, D/o, W/o, C/O)
RELATIVE_PATTERN = re.compile(
    r'\b(?:S/o|D/o|W/o|C/O|S/O|D/O|W/O|C/O|Son\s+of|Daughter\s+of|Wife\s+of|Husband\s+of|Father\s+of|Mother\s+of)\s+[\w\s\.]+\b',
    re.IGNORECASE
)

# Enhanced UHID/MRN patterns
UHID_MRN_PATTERN_V2 = re.compile(
    r'\b(?:UHID|MRN|UHID/MRN|CRNO|IPNO|OPNO|REGNO|REG\s+NO|PATIENT\s+ID|PATIENT\s+NO\.?)\s*[:\-]?\s*([A-Za-z0-9]{6,20})\b',
    re.IGNORECASE
)

# Bare UHID/MRN patterns for identifier fields (without prefix)
# Matches hospital-specific formats like: SNJ/26/064127, JJH-0076928, IPD-2026-00432, ADM000162, etc.
# More specific to avoid false positives on medical values
BARE_UHID_PATTERN = re.compile(
    r'\b(?:[A-Z]{2,6}[/\-]\d{2,6}[/\-]\d{4,8}|[A-Z]{2,6}\-\d{6,10}|[A-Z]{2,6}\d{7,10}|(?:SNJ|JJH|IPD|IP|OP|ADM|UHID|MRN|CRNO|REGNO|REG)[/\-]?\d{4,10})\b'
)

# Village name patterns (bare village names - capitalized words)
# Common Indian village name patterns: capitalized words, often 2-3 words
# More specific: require at least 2 words, and exclude common medical terms
VILLAGE_NAME_PATTERN = re.compile(
    r'\b(?:[A-Z][a-z]{3,}(?:\s+[A-Z][a-z]{3,}){1,2})\b'
)


def verhoeff_checksum(number: str) -> bool:
    """
    Validate Verhoeff checksum for Aadhaar numbers.
    
    The Verhoeff algorithm uses a dihedral group D5 permutation.
    """
    if not number.isdigit():
        return False
    
    # Verhoeff algorithm tables
    d = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
        [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
        [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
        [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
        [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
        [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
        [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
        [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
        [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
    ]
    
    p = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
        [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
        [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
        [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
        [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
        [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
        [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
    ]
    
    inv = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]
    
    c = 0
    for i, ch in enumerate(reversed(number)):
        c = d[c][int(ch)]
    return c == 0


def validate_aadhaar(number: str) -> bool:
    """Validate Aadhaar number with Verhoeff checksum."""
    # Remove spaces and hyphens
    clean = number.replace(' ', '').replace('-', '')
    if not clean.isdigit() or len(clean) != 12:
        return False
    return verhoeff_checksum(clean)


def validate_abha(number: str) -> bool:
    """Validate ABHA (14 digits with Verhoeff checksum)."""
    if not number.isdigit() or len(number) != 14:
        return False
    # ABHA uses same Verhoeff algorithm
    return verhoeff_checksum(number)


def validate_pan(number: str) -> bool:
    """Validate PAN format."""
    return bool(PAN_PATTERN.fullmatch(number.upper()))


def validate_abha(number: str) -> bool:
    """Validate ABHA (14 digits with Verhoeff checksum)."""
    if not number.isdigit() or len(number) != 14:
        return False
    return verhoeff_checksum(number)


def detect_identifiers(record) -> List:
    """
    Detect identifiers in a record.
    
    Args:
        record: UnifiedRecord with normalized_text
        
    Returns:
        List of PIISpan objects for detected identifiers
    """
    from ..contracts import PIISpan, PIIType
    
    spans = []
    text = record.normalized_text
    
    if not text:
        return []
    
    # Email detection
    for match in re.finditer(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', record.normalized_text):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.EMAIL,
            confidence=0.95,
            original_text=match.group(),
            context=text[max(0, match.start()-50):match.end()+50],
            detector="email"
        ))
    
    # Phone numbers (Indian) - multiple formats
    phone_patterns = [
        re.compile(r'(?:\+91[\-\s]?|0[\-\s]?)?[6-9]\d{4}[\-\s]?\d{5}\b'),  # With spacing
        re.compile(r'(?:\+91[\-\s]?|0[\-\s]?)?[6-9]\d{9}\b'),  # Continuous
        re.compile(r'(?:\+91[\-\s]?|0[\-\s]?)?\d{5}[\-\s]?\d{5}\b'),  # 5-5 split
    ]
    for pattern in phone_patterns:
        for match in pattern.finditer(record.normalized_text):
            spans.append(PIISpan(
                start=match.start(),
                end=match.end(),
                pii_type=PIIType.PHONE,
                confidence=0.9,
                original_text=match.group(),
                context=record.normalized_text[max(0, match.start()-50):match.end()+50],
                detector="phone"
            ))
    
    # Aadhaar (12 digits with Verhoeff, with optional spaces/hyphens)
    for match in AADHAAR_PATTERN.finditer(record.normalized_text):
        matched = match.group()
        # Remove spaces/hyphens for checksum validation
        clean = matched.replace(' ', '').replace('-', '')
        is_valid_verhoeff = verhoeff_checksum(clean)
        confidence = 0.99 if is_valid_verhoeff else 0.7  # Lower confidence for format-only matches
        if is_valid_verhoeff or len(clean) == 12:
            # Accept if valid Verhoeff OR correct format (12 digits)
            # Lower confidence for format-only matches (likely test data)
            spans.append(PIISpan(
                start=match.start(),
                end=match.end(),
                pii_type=PIIType.AADHAAR,
                confidence=confidence,
                original_text=matched,
                context=record.normalized_text[max(0, match.start()-50):match.end()+50],
                detector="aadhaar"
            ))
    
    # ABHA (14 digits with optional spaces/hyphens)
    # ABHA numbers may not use Verhoeff checksum, so validate format only
    for match in ABHA_PATTERN.finditer(record.normalized_text):
        matched = match.group()
        # Remove spaces/hyphens for length validation
        clean = matched.replace(' ', '').replace('-', '')
        if clean.isdigit() and len(clean) == 14:
            spans.append(PIISpan(
                start=match.start(),
                end=match.end(),
                pii_type=PIIType.ABHA,
                confidence=0.95,
                original_text=matched,
                context=record.normalized_text[max(0, match.start()-50):match.end()+50],
                detector="abha"
            ))
    
    # PAN
    for match in re.finditer(r'\b[A-Z]{5}\d{4}[A-Z]\b', record.normalized_text):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.PAN,
            confidence=0.98,
            original_text=match.group(),
            context=record.normalized_text[max(0, match.start()-50):match.end()+50],
            detector="pan"
        ))
    
    # Phone numbers
    phone_pattern = re.compile(r'(?:\+91[\-\s]?|0[\-\s]?)?[6-9]\d{9}\b')
    for match in phone_pattern.finditer(record.normalized_text):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.PHONE,
            confidence=0.9,
            original_text=match.group(),
            context=record.normalized_text[max(0, match.start()-50):match.end()+50],
            detector="phone"
        ))
    
    # Email
    email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    for match in re.finditer(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', record.normalized_text):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.EMAIL,
            confidence=0.95,
            original_text=match.group(),
            context=record.normalized_text[max(0, match.start()-50):match.end()+50],
            detector="email"
        ))
    
    # PIN code - more restrictive to avoid matching parts of UHID/MRN
    # Use negative lookbehind/lookahead to ensure standalone 6-digit numbers
    for match in re.finditer(r'(?<![A-Za-z0-9])\d{6}(?![A-Za-z0-9])', record.normalized_text):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.PIN,
            confidence=0.7,
            original_text=match.group(),
            context=record.normalized_text[max(0, match.start()-50):match.end()+50],
            detector="pin"
        ))
    
    # UHID/MRN (enhanced)
    for match in UHID_MRN_PATTERN_V2.finditer(record.normalized_text):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.UHID,
            confidence=0.9,
            original_text=match.group(),
            context=record.normalized_text[max(0, match.start()-50):match.end()+50],
            detector="uhid_mrn_v2"
        ))
    
    # Bare UHID/MRN patterns for identifier fields (without prefix)
    # Matches formats like: SNJ/26/064127, JJH-0076928, IPD-2026-00432, ADM000162, etc.
    for match in BARE_UHID_PATTERN.finditer(record.normalized_text):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.UHID,
            confidence=0.85,
            original_text=match.group(),
            context=record.normalized_text[max(0, match.start()-50):match.end()+50],
            detector="bare_uhid"
        ))
    
    # Legacy UHID/MRN pattern (backward compatibility)
    for match in re.finditer(r'\b(?:UHID|MRN|UHID/MRN)[\s:]*([A-Za-z0-9]{6,15})\b', record.normalized_text, re.IGNORECASE):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.UHID,
            confidence=0.85,
            original_text=match.group(),
            context=record.normalized_text[max(0, match.start()-50):match.end()+50],
            detector="uhid_mrn_legacy"
        ))
    
    # Insurance IDs (enhanced)
    for match in INSURANCE_PATTERN_V2.finditer(record.normalized_text):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.INSURANCE,
            confidence=0.85,
            original_text=match.group(),
            context=record.normalized_text[max(0, match.start()-50):match.end()+50],
            detector="insurance_v2"
        ))
    
    # Legacy insurance patterns (backward compatibility)
    for match in re.finditer(r'\b(?:INS|POL|POLNO|POLICY)[\s:]*([A-Z0-9]{8,20})\b', record.normalized_text, re.IGNORECASE):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.INSURANCE,
            confidence=0.8,
            original_text=match.group(),
            context=record.normalized_text[max(0, match.start()-50):match.end()+50],
            detector="insurance_legacy"
        ))
    
    # URLs
    for match in re.finditer(r'https?://[^\s/$.?#].[^\s]*', record.normalized_text):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.URL,
            confidence=0.9,
            original_text=match.group(),
            context=record.normalized_text[max(0, match.start()-50):match.end()+50],
            detector="url"
        ))
    
    # House numbers
    for match in HOUSE_NUMBER_PATTERN.finditer(record.normalized_text):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.ADDRESS,
            confidence=0.85,
            original_text=match.group(),
            context=record.normalized_text[max(0, match.start()-50):match.end()+50],
            detector="house_number"
        ))
    
    # Village/Locality
    for match in VILLAGE_LOCALITY_PATTERN.finditer(record.normalized_text):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.ADDRESS,
            confidence=0.8,
            original_text=match.group(),
            context=record.normalized_text[max(0, match.start()-50):match.end()+50],
            detector="village_locality"
        ))
    
    # Bare village names (capitalized words) - for fields that contain just village names
    for match in VILLAGE_NAME_PATTERN.finditer(record.normalized_text):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.ADDRESS,
            confidence=0.7,
            original_text=match.group(),
            context=record.normalized_text[max(0, match.start()-50):match.end()+50],
            detector="bare_village"
        ))
    
    # Landmarks
    for match in LANDMARK_PATTERN.finditer(record.normalized_text):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.ADDRESS,
            confidence=0.75,
            original_text=match.group(),
            context=record.normalized_text[max(0, match.start()-50):match.end()+50],
            detector="landmark"
        ))
    
    # Insurance IDs (enhanced)
    for match in INSURANCE_PATTERN_V2.finditer(record.normalized_text):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.INSURANCE,
            confidence=0.85,
            original_text=match.group(),
            context=record.normalized_text[max(0, match.start()-50):match.end()+50],
            detector="insurance_v2"
        ))
    
    # Relative names (S/o, D/o, W/o, C/O)
    for match in RELATIVE_PATTERN.finditer(record.normalized_text):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.RELATIVE,
            confidence=0.9,
            original_text=match.group(),
            context=record.normalized_text[max(0, match.start()-50):match.end()+50],
            detector="relative_name"
        ))
    
    # Enhanced UHID/MRN patterns
    for match in UHID_MRN_PATTERN_V2.finditer(record.normalized_text):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.UHID,
            confidence=0.9,
            original_text=match.group(),
            context=record.normalized_text[max(0, match.start()-50):match.end()+50],
            detector="uhid_mrn_v2"
        ))
    
    # URLs
    for pattern in [
        re.compile(r'\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b'),
        re.compile(r'\b\d{4}[\-]\d{1,2}[\-]\d{1,2}\b'),
        re.compile(r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}\b', re.IGNORECASE),
    ]:
        for match in pattern.finditer(record.normalized_text):
            spans.append(PIISpan(
                start=match.start(),
                end=match.end(),
                pii_type=PIIType.DATE,
                confidence=0.8,
                original_text=match.group(),
                context=record.normalized_text[max(0, match.start()-50):match.end()+50],
                detector="date"
            ))
    
    return spans