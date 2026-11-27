"""
LOCKMATE — Placeholder PII Detection (Phase 3)

Basic regex-based PII detection for initial pipeline validation.
Replaced by production-grade detection in Phase 4.
"""

from __future__ import annotations

import re
from typing import List, Optional

from ..contracts import UnifiedRecord, PIISpan, PIIType
from ..utils.logging import get_logger_adapter

logger = get_logger_adapter("detection.placeholder")


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

# ABHA: 14 digits
ABHA_PATTERN = re.compile(
    r'\b\d{14}\b'
)

# PIN code: 6 digits
PIN_PATTERN = re.compile(
    r'\b\d{6}\b'
)

# Date patterns (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, etc.)
DATE_PATTERNS = [
    re.compile(r'\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b'),  # DD/MM/YYYY or DD-MM-YYYY
    re.compile(r'\b\d{4}[/\-]\d{1,2}[/\-]\d{1,2}\b'),    # YYYY-MM-DD
    re.compile(r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}\b', re.IGNORECASE),  # DD Mon YYYY
]

# Honorific + name pattern (Mr. Rahul Sharma, Dr. Priya Patel)
HONORIFIC_NAME_PATTERN = re.compile(
    r'\b(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Prof\.?|Shri|Smt)\s+[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})+\b',
    re.IGNORECASE
)

# Initial + surname pattern (R. Sharma, R.K. Sharma)
INITIAL_SURNAME_PATTERN = re.compile(
    r'\b(?:[A-Z]\.\s*){1,3}\s*[A-Z][a-z]{2,}\b'
)

# Relationship marker patterns (S/o, D/o, W/o, C/O)
RELATIVE_PATTERN = re.compile(
    r'\b(?:S/o|D/o|W/o|C/O|Son of|Daughter of|Wife of|Husband of)\s+[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})+\b',
    re.IGNORECASE
)

# Devanagari name pattern (2+ Devanagari words)
DEVANAGARI_NAME_PATTERN = re.compile(
    r'[\u0900-\u097F]{2,}(?:\s+[\u0900-\u097F]{2,})+'
)

# Hinglish name pattern (mixed Latin + Devanagari)
HINGLISH_NAME_PATTERN = re.compile(
    r'(?:[A-Za-z]{2,}\s+[\u0900-\u097F]{2,})|(?:[\u0900-\u097F]{2,}\s+[A-Za-z]{2,})'
)


def detect_pii_placeholder(record: UnifiedRecord) -> List[PIISpan]:
    """
    Detect PII using simple regex patterns (placeholder implementation).

    Detects: email, phone, PAN, Aadhaar, ABHA, PIN, dates, names (Latin, Devanagari, Hinglish)

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

    # 14-digit number detection (potential ABHA)
    for match in ABHA_PATTERN.finditer(text):
        matched_text = match.group()
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.ABHA,
            confidence=0.7,
            original_text=matched_text,
            context=text[max(0, match.start()-50):match.end()+50],
            detector="placeholder_abha"
        ))

    # PIN code detection
    for match in PIN_PATTERN.finditer(text):
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.PIN,
            confidence=0.6,
            original_text=match.group(),
            context=text[max(0, match.start()-50):match.end()+50],
            detector="placeholder_pin"
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

    # Honorific + name (Mr. Rahul Sharma, Dr. Priya Patel)
    for match in HONORIFIC_NAME_PATTERN.finditer(text):
        matched = match.group()
        if _is_medical_term(matched):
            continue
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.NAME,
            confidence=0.85,
            original_text=matched,
            context=text[max(0, match.start()-50):match.end()+50],
            detector="placeholder_honorific_name"
        ))

    # Initial + surname pattern (R. Sharma, R.K. Sharma)
    for match in INITIAL_SURNAME_PATTERN.finditer(text):
        matched = match.group()
        if _is_medical_term(matched):
            continue
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.NAME,
            confidence=0.75,
            original_text=matched,
            context=text[max(0, match.start()-50):match.end()+50],
            detector="placeholder_initial_surname"
        ))

    # Relative names (S/o, D/o, etc.)
    for match in RELATIVE_PATTERN.finditer(text):
        matched = match.group()
        if _is_medical_term(matched):
            continue
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.RELATIVE,
            confidence=0.9,
            original_text=matched,
            context=text[max(0, match.start()-50):match.end()+50],
            detector="placeholder_relative"
        ))

    # Devanagari names
    for match in DEVANAGARI_NAME_PATTERN.finditer(text):
        matched = match.group()
        if _is_medical_term(matched):
            continue
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.NAME,
            confidence=0.8,
            original_text=matched,
            context=text[max(0, match.start()-50):match.end()+50],
            detector="placeholder_devanagari_name"
        ))

    # Hinglish names
    for match in HINGLISH_NAME_PATTERN.finditer(text):
        matched = match.group()
        if _is_medical_term(matched):
            continue
        spans.append(PIISpan(
            start=match.start(),
            end=match.end(),
            pii_type=PIIType.NAME,
            confidence=0.75,
            original_text=matched,
            context=text[max(0, match.start()-50):match.end()+50],
            detector="placeholder_hinglish_name"
        ))

    logger.debug("placeholder_pii_detected",
                record_id=record.record_id,
                span_count=len(spans))

    return spans


def _is_medical_term(text: str) -> bool:
    """Check if text is a known medical term that should not be treated as a name."""
    medical_terms = {
        'diabetes', 'hypertension', 'tb', 'hiv', 'aids', 'cancer',
        'asthma', 'arthritis', 'osteoporosis', 'anemia', 'leukemia',
        'lymphoma', 'melanoma', 'carcinoma', 'sarcoma',
        'parkinson', 'alzheimer', 'crohn', 'dolo', 'paracetamol',
        'metformin', 'aspirin', 'ibuprofen', 'diclofenac',
        'amoxicillin', 'azithromycin', 'ciprofloxacin',
        'metronidazole', 'omeprazole', 'ranitidine', 'pantoprazole',
        'atorvastatin', 'amlodipine', 'losartan', 'metoprolol',
        'insulin', 'glimepiride', 'gliclazide', 'pioglitazone',
        'sitagliptin', 'linagliptin', 'empagliflozin', 'dapagliflozin',
        'canagliflozin', 'ramipril', 'enalapril', 'lisinopril',
        'telmisartan', 'valsartan', 'hydrochlorothiazide',
        'furosemide', 'spironolactone', 'warfarin', 'clopidogrel',
        'simvastatin', 'rosuvastatin'
    }
    return text.lower().strip() in medical_terms


def detect_medical_placeholder(record: UnifiedRecord) -> List:
    """
    Detect medical expressions that should be preserved (placeholder).

    Detects: dosages (N mg), frequencies (OD, BD, TDS), disease names (Parkinson's),
             drug names, lab values, vital signs, units

    Returns:
        List of MedicalSpan objects
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
        r'\b(?:Paracetamol|Dolo|Crocin|Calpol|Metformin|Aspirin|Ibuprofen|Diclofenac|Amoxicillin|Azithromycin|Ciprofloxacin|Metronidazole|Omeprazole|Ranitidine|Pantoprazole|Atorvastatin|Amlodipine|Losartan|Metoprolol|Insulin|Glimepiride|Gliclazide|Pioglitazone|Sitagliptin|Linagliptin|Empagliflozin|Dapagliflozin|Canagliflozin|Ramipril|Enalapril|Lisinopril|Telmisartan|Valsartan|Hydrochlorothiazide|Furosemide|Spironolactone|Warfarin|Clopidogrel|Simvastatin|Rosuvastatin)\b',
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

    # Lab test patterns
    lab_pattern = re.compile(
        r'\b(?:HbA1c|CBC|LFT|KFT|TSH|Hb|WBC|RBC|Platelet|Creatinine|Urea|Glucose|Cholesterol|HDL|LDL|Triglycerides|Bilirubin|ALT|AST|ALP|GGT|Protein|Albumin|Sodium|Potassium|Chloride|Calcium|Magnesium|Phosphate|Uric)\b',
        re.IGNORECASE
    )
    for match in lab_pattern.finditer(text):
        spans.append(MedicalSpan(
            start=match.start(),
            end=match.end(),
            medical_type=MedicalType.LAB,
            confidence=0.95,
            original_text=match.group()
        ))

    # Vital signs patterns (BP, HR, Temp, etc.)
    vital_pattern = re.compile(
        r'\b(?:BP|HR|PR|RR|SpO2|Temp|Temperature|Blood Pressure|Heart Rate|Pulse|Respiratory Rate|Oxygen Saturation)\s*(?:\d+/\d+|\d+\.?\d*)\b',
        re.IGNORECASE
    )
    for match in vital_pattern.finditer(text):
        spans.append(MedicalSpan(
            start=match.start(),
            end=match.end(),
            medical_type=MedicalType.VITAL,
            confidence=0.9,
            original_text=match.group()
        ))

    # Clinical units
    unit_pattern = re.compile(
        r'\b(?:mg|g|mL|mcg|IU|U|mg/dl|mmol/l|°c|bpm|mmhg|cm|kg|years|months|days)\b',
        re.IGNORECASE
    )
    for match in unit_pattern.finditer(text):
        spans.append(MedicalSpan(
            start=match.start(),
            end=match.end(),
            medical_type=MedicalType.UNIT,
            confidence=0.9,
            original_text=match.group()
        ))

    return spans