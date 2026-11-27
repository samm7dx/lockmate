"""
LOCKMATE — Diagnosis and Procedure Detection

Detects diagnoses, procedures, and disease names including eponyms.
"""

from __future__ import annotations

import re
from typing import List

from ..contracts import MedicalSpan, MedicalType
from ..utils.logging import get_logger_adapter
from ..detection.gazetteer import get_gazetteer

logger = get_logger_adapter("clinical.diagnoses")


def detect_diagnoses(record) -> List:
    """
    Detect diagnoses, procedures, and disease names.
    
    Args:
        record: UnifiedRecord with normalized_text
        
    Returns:
        List of MedicalSpan objects
    """
    spans = []
    text = record.normalized_text
    
    if not text:
        return spans
    
    gazetteer = get_gazetteer()
    
    # Disease names (from gazetteer - ICD-10 derived + eponyms)
    diagnoses = gazetteer.get("medical_diagnoses")
    for diagnosis in diagnoses:
        pattern = re.compile(r'\b' + re.escape(diagnosis) + r'\b', re.IGNORECASE)
        for match in pattern.finditer(record.normalized_text):
            spans.append(MedicalSpan(
                start=match.start(),
                end=match.end(),
                medical_type=MedicalType.DIAGNOSIS,
                confidence=0.95,
                original_text=match.group()
            ))
    
    # ICD-10 code patterns (e.g., E11.9, I10, N39.0, A01.0)
    # Only match in clear medical context (near diagnosis/condition terms)
    icd10_pattern = re.compile(
        r'\b[A-Z]\d{2}(?:\.\d+)?\b'
    )
    for match in icd10_pattern.finditer(record.normalized_text):
        # Validate it looks like an ICD code (letter + 2 digits + optional decimal)
        code = match.group()
        if re.match(r'^[A-Z]\d{2}(?:\.\d+)?$', code):
            # Additional validation: exclude common false positives
            if code not in ['BP', 'HR', 'RR', 'IV', 'IM', 'PO', 'IV', 'IO']:
                # Check for medical context nearby
                context = record.normalized_text[max(0, match.start()-50):match.end()+50]
                medical_context = any(term in context.lower() for term in [
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
    
    # Procedure names (common procedures)
    procedures = {
        "angiography", "angioplasty", "stent", "bypass", "cabg",
        "dialysis", "chemotherapy", "radiotherapy", "surgery",
        "appendectomy", "cholecystectomy", "hysterectomy",
        "biopsy", "endoscopy", "colonoscopy", "gastroscopy",
        "mri", "ct scan", "ct-scan", "x-ray", "xray", "ultrasound",
        "ecg", "ekg", "echocardiogram", "stress test",
        "cardiac catheterization", "coronary angiogram", "pci", "pta",
        "laparoscopy", "laparotomy", "thoracotomy", "craniotomy",
        "amputation", "debridement", "excision", "incision and drainage",
        "tracheostomy", "intubation", "ventilation", "cpr",
        "pacemaker", "defibrillator", "ablation", "cardioversion",
    }
    
    for proc in procedures:
        pattern = re.compile(r'\b' + re.escape(proc) + r'\b', re.IGNORECASE)
        for match in pattern.finditer(record.normalized_text):
            spans.append(MedicalSpan(
                start=match.start(),
                end=match.end(),
                medical_type=MedicalType.PROCEDURE,
                confidence=0.9,
                original_text=match.group()
            ))
    
    # Eponymous diseases (Parkinson's, Alzheimer's, Crohn's, etc.)
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