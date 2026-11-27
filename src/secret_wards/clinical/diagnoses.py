"""
LOCKMATE — Diagnosis and Procedure Detection

Detects diagnoses, procedures, and disease names including eponyms.
"""

from __future__ import annotations

import re
from typing import List

from ..contracts import MedicalSpan, MedicalType

logger = get_logger_adapter("clinical.diagnoses")


# Module-level cached patterns
_diag_cache: dict = {}


def _get_cached_patterns():
    """Get or create cached regex patterns and diagnosis names."""
    global _diag_cache
    if not _diag_cache:
        from ..detection.gazetteer import get_gazetteer
        gazetteer = get_gazetteer()
        _diag_cache = {
            'diagnoses': frozenset(gazetteer.get("medical_diagnoses")),
            'icd10_pattern': re.compile(r'\b[A-Z]\d{2}(?:\.\d+)?\b'),
            'proc_pattern': re.compile(r'\b(?:appendectomy|cholecystectomy|herniorrhaphy|mastectomy|hysterectomy|prostatectomy|thyroidectomy|tonsillectomy|adenoidectomy|laparoscopy|endoscopy|colonoscopy|biopsy|cath(?:eteriz(?:ation)?)?|angioplasty|stent|bypass|transplant|dialysis|chemotherapy|radiotherapy)\b', re.IGNORECASE),
        }
    return _diag_cache


def detect_diagnoses(record) -> List:
    """
    Detect diagnoses, procedures, and disease names.
    
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
    diagnoses = cache['diagnoses']
    
    # Disease names (from gazetteer - ICD-10 derived + eponyms)
    for diagnosis in diagnoses:
        for match in re.finditer(r'\b' + re.escape(diagnosis) + r'\b', text, re.IGNORECASE):
            spans.append(MedicalSpan(
                start=match.start(),
                end=match.end(),
                medical_type=MedicalType.DIAGNOSIS,
                confidence=0.95,
                original_text=match.group()
            ))
    
    # ICD-10 code patterns (e.g., E11.9, I10, N39.0, A01.0)
    # Use cached pattern
    for match in cache['icd10_pattern'].finditer(text):
        code = match.group()
        if re.match(r'^[A-Z]\d{2}(?:\.\d+)?$', code):
            # Additional validation: exclude common false positives
            if code not in {'BP', 'HR', 'RR', 'IV', 'IM', 'PO', 'IO'}:
                # Check for medical context nearby
                context = text[max(0, match.start()-50):match.end()+50].lower()
                medical_context = any(term in context for term in [
                    'diagnosis', 'diagnosed', 'condition', 'disease', 'disorder',
                    'icd', 'code', 'icd-10', 'icd10', 'principal', 'secondary',
                    'comorbidity', 'complication', 'history', 'hx', 'h/o',
                    'diabetes', 'hypertension', 'cancer', 'infection', 'stroke',
                    'mi', 'cva', 'stroke', 'chf', 'copd', 'uti', 'pneumonia'
                ])
                if medical_context:
                    spans.append(MedicalSpan(
                        start=match.start(),
                        end=match.end(),
                        medical_type=MedicalType.ICD_CODE,
                        confidence=0.9,
                        original_text=match.group()
                    ))
    
    # Procedure names - use cached pattern
    for match in cache['proc_pattern'].finditer(text):
        spans.append(MedicalSpan(
            start=match.start(),
            end=match.end(),
            medical_type=MedicalType.PROCEDURE,
            confidence=0.9,
            original_text=match.group()
        ))
    
    # Eponymous diseases
    eponyms = {
        "parkinson's", "alzheimer's", "crohn's", "huntington's",
        "als", "ms", "multiple sclerosis", "lupus", "sle",
        "rheumatoid arthritis", "osteoarthritis", "gout",
        "tuberculosis", "tb", "hiv", "aids", "hepatitis",
        "diabetes mellitus", "type 1 diabetes", "type 2 diabetes",
        "hypertension", "hypothyroidism", "hyperthyroidism",
        "copd", "asthma", "pneumonia", "bronchitis",
        "myocardial infarction", "mi", "stroke", "cva", "tia",
        "heart failure", "chf", "atrial fibrillation", "afib",
        "deep vein thrombosis", "dvt", "pulmonary embolism", "pe",
    }
    
    for eponym in eponyms:
        for match in re.finditer(r'\b' + re.escape(eponym) + r'\b', text, re.IGNORECASE):
            spans.append(MedicalSpan(
                start=match.start(),
                end=match.end(),
                medical_type=MedicalType.DIAGNOSIS,
                confidence=0.95,
                original_text=match.group()
            ))
    
    for eponym in eponyms:
        pattern = re.compile(r'\b' + re.escape(eponym) + r'\b', re.IGNORECASE)
        for match in pattern.finditer(record.normalized_text):
            spans.append(MedicalSpan(
                start=match.start(),
                end=match.end(),
                medical_type=MedicalType.DIAGNOSIS,
                confidence=0.98,
                original_text=match.group()
            ))
    
    # Medical history patterns (history of..., h/o, hx of)
    history_pattern = re.compile(
        r'\b(?:hx|h/o|history\s+of)\s+(?:of\s+)?(?:diabetes|hypertension|htn|mi|mi|cva|stroke|mi|chf|copd|asthma|diabetes|dm|htn|tb|hepatitis|cancer|surgery|mi|cva|pe|dvt|afib|mi)\b',
        re.IGNORECASE
    )
    for match in history_pattern.finditer(record.normalized_text):
        spans.append(MedicalSpan(
            start=match.start(),
            end=match.end(),
            medical_type=MedicalType.DIAGNOSIS,
            confidence=0.9,
            original_text=match.group()
        ))
    
    # Presenting complaints (complaining of, c/o, presenting with)
    complaint_pattern = re.compile(
        r'\b(?:c/o|complain(?:ing\s+of|s)|presenting\s+with|presents\s+with)\s+[\w\s,]+(?:fever|pain|cough|dyspnea|shortness\s+of\s+breath|sob|nausea|vomiting|diarrhea|headache|chest\s+pain|abdominal\s+pain|back\s+pain|weakness|fatigue|dizziness|syncope|palpitation|edema|rash|itching)\b',
        re.IGNORECASE
    )
    for match in complaint_pattern.finditer(record.normalized_text):
        spans.append(MedicalSpan(
            start=match.start(),
            end=match.end(),
            medical_type=MedicalType.DIAGNOSIS,
            confidence=0.9,
            original_text=match.group()
        ))
    
    return spans