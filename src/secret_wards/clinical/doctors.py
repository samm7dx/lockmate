"""
LOCKMATE — Doctor Context Detection

Detects doctor names in clinical context vs patient/relative names.
"""

from __future__ import annotations

import re
from typing import List, Optional

from ..contracts import MedicalSpan, MedicalType, UnifiedRecord
from ..utils.logging import get_logger_adapter
from ..detection.transliterate import devanagari_to_latin, is_devanagari_text

logger = get_logger_adapter("clinical.doctors")

# Doctor prefixes
DOCTOR_PREFIXES = {
    'dr', 'dr.', 'doctor', 'डॉ', 'डॉ.', 'डॉक्टर',
    'dr ', 'dr.', 'doctor',
}

# Clinical context indicators (doctor is acting in clinical capacity)
CLINICAL_CONTEXT_INDICATORS = {
    'prescribed', 'advised', 'recommended', 'treated',
    'diagnosed', 'examined', 'consulted', 'referred', 'admitted',
    'discharged', 'followup', 'follow-up', 'review', 'checkup',
    'prescription', 'medication', 'dosage', 'dosage', 'mg', 'ml',
    'tablet', 'capsule', 'injection', 'syrup', 'drops',
    'advised', 'ordered', 'started', 'stopped', 'continued',
    'increased', 'decreased', 'adjusted', 'titrated',
}

# Patient context indicators (name is patient, not doctor)
PATIENT_CONTEXT_INDICATORS = {
    'patient', 'suffering', 'suffering from', 'diagnosed with',
    'admitted', 'discharged', 'complained of', 'history of',
    'allergic to', 'allergy', 'under treatment', 'on medication',
    'complained of', 'presented with', 'presenting with',
}


def detect_doctors(record) -> List:
    """
    Detect doctor names in clinical context.
    
    Args:
        record: UnifiedRecord with normalized_text
        
    Returns:
        List of MedicalSpan objects for doctor names
    """
    from ..contracts import MedicalSpan, MedicalType
    
    spans = []
    text = record.normalized_text
    
    if not text:
        return []
    
    # Pattern: Dr./Doctor + name + clinical verb
    # Dr. Rajesh prescribed...
    # Doctor Rajesh prescribed...
    # डॉ. राजेश ने लिखा...
    
    # Pattern 1: Dr./Doctor + name + clinical verb
    # Dr. Rajesh prescribed / Doctor Rajesh prescribed
    clinical_verbs = [
        'prescribed', 'advised', 'recommended', 'treated',
        'diagnosed', 'examined', 'consulted', 'referred', 'admitted',
        'discharged', 'followup', 'follow-up', 'review', 'checkup',
        'prescription', 'medication', 'dosage', 'dosage', 'mg', 'ml',
        'tablet', 'capsule', 'injection', 'syrup', 'drops',
        'advised', 'ordered', 'started', 'stopped', 'continued',
        'increased', 'decreased', 'adjusted', 'titrated',
    ]
    
    # Pattern 1: Dr./Doctor + name + clinical verb
    # Dr. Rajesh prescribed / Doctor Rajesh prescribed
    # Pattern: Dr./Doctor + name + clinical verb
    
    # Build pattern for: Dr./Doctor + name + clinical verb
    clinical_verbs_pattern = '|'.join(re.escape(v) for v in [
        'prescribed', 'advised', 'recommended', 'treated',
        'diagnosed', 'examined', 'consulted', 'referred', 'admitted',
        'discharged', 'followup', 'follow-up', 'review', 'checkup',
        'prescription', 'medication', 'dosage', 'tablet', 'capsule',
        'injection', 'syrup', 'drops', 'advised', 'ordered', 'started',
        'stopped', 'continued', 'increased', 'decreased', 'adjusted',
        'titrated', 'monitored', 'assessed',
    ])
    
    # Pattern: Dr./Doctor + name + clinical verb
    doctor_pattern = re.compile(
        r'\b(?:Dr\.?|Doctor)\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)*[A-Z][a-z]+)\s+(?:' + '|'.join(re.escape(v) for v in [
            'prescribed', 'advised', 'recommended', 'treated',
            'diagnosed', 'examined', 'consulted', 'referred', 'admitted',
            'discharged', 'followup', 'follow-up', 'review', 'checkup',
            'prescription', 'medication', 'dosage', 'tablet', 'capsule',
            'injection', 'syrup', 'drops', 'advised', 'ordered', 'started',
            'stopped', 'continued', 'increased', 'decreased',
            'adjusted', 'titrated', 'monitored', 'assessed',
        ]) + r')\b',
        re.IGNORECASE
    )
    
    # Also check Devanagari: डॉ. राजेश ने लिखा...
    # Pattern for Devanagari doctor names
    devanagari_doctor_pattern = re.compile(
        r'(?:डॉ\.?|डॉक्टर)\s+([\u0900-\u097F]{2,}(?:\s+[\u0900-\u097F]{2,})+)',
        re.IGNORECASE
    )
    
    spans = []
    text = record.normalized_text
    
    if not text:
        return []
    
    # Pattern 1: English doctor names with clinical verbs
    # Dr. Name prescribed / Doctor Name prescribed
    clinical_verbs_pattern = '|'.join([
        'prescribed', 'advised', 'recommended', 'treated',
        'diagnosed', 'examined', 'consulted', 'referred', 'admitted',
        'discharged', 'followup', 'follow-up', 'review', 'checkup',
        'prescription', 'medication', 'dosage', 'tablet', 'capsule',
        'injection', 'syrup', 'drops', 'advised', 'ordered', 'started',
        'stopped', 'continued', 'increased', 'decreased', 'adjusted', 'titrated'
    ])
    
    # Pattern: Dr. Name verb / Doctor Name verb
    doctor_verb_pattern = re.compile(
        r'\b(?:Dr\.?|Doctor)\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)*[A-Z][a-z]+)\s+(?:' + '|'.join([
            'prescribed', 'advised', 'recommended', 'treated',
            'diagnosed', 'examined', 'consulted', 'referred', 'admitted',
            'discharged', 'followup', 'follow-up', 'review', 'checkup',
            'prescription', 'medication', 'dosage', 'tablet', 'capsule',
            'injection', 'syrup', 'drops', 'advised', 'ordered', 'started',
            'stopped', 'continued', 'increased', 'decreased', 'adjusted', 'titrated'
        ]) + r')\b',
        re.IGNORECASE
    )
    
    for match in re.finditer(doctor_verb_pattern, record.normalized_text):
        name_start = match.start(1)
        name_end = match.end(1)
        
        spans.append(MedicalSpan(
            start=name_start,
            end=name_end,
            medical_type=MedicalType.DOCTOR,
            confidence=0.95,
            original_text=record.normalized_text[name_start:name_end]
        ))
    
    # Pattern 2: Devanagari doctor names (डॉ. राजेश ने लिखा...)
    # डॉ. राजेश ने लिखा / डॉ. राजेश ने लिखा
    devanagari_doctor_pattern = re.compile(
        r'(?:डॉ\.?|डॉक्टर)\s+([\u0900-\u097F]{2,}(?:\s+[\u0900-\u097F]{2,})+)',
        re.IGNORECASE
    )
    
    for match in re.finditer(r'(?:डॉ\.?|डॉक्टर)\s+([\u0900-\u097F]{2,}(?:\s+[\u0900-\u097F]{2,})+)', record.normalized_text):
        name_start = match.start(1)
        name_end = match.end(1)
        
        # Check clinical context nearby
        context = record.normalized_text[max(0, match.start()-50):match.end()+50]
        is_clinical = any(verb in context.lower() for verb in [
            'लिखा', 'लिखी', 'दिया', 'दिया', 'सुझाया', 'बताया',
            'prescribed', 'advised', 'recommended', 'treated',
            'diagnosed', 'examined', 'consulted', 'referred'
        ])
        
        if is_clinical:
            spans.append(MedicalSpan(
                start=name_start,
                end=name_end,
                medical_type=MedicalType.DOCTOR,
                confidence=0.95,
                original_text=record.normalized_text[name_start:name_end]
            ))
    
    # Pattern 3: "Dr. Name prescribed" / "Dr. Name advised"
    # Check for "Dr. Name prescribed/advised/recommended" pattern
    for match in re.finditer(
        r'\b(?:Dr\.?|Doctor)\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)*[A-Z][a-z]+)\s+(?:prescribed|advised|recommended|treated|diagnosed|examined|consulted|referred|admitted|discharged)\b',
        record.normalized_text,
        re.IGNORECASE
    ):
        name_start = match.start(1)
        name_end = match.end(1)
        spans.append(MedicalSpan(
            start=name_start,
            end=name_end,
            medical_type=MedicalType.DOCTOR,
            confidence=0.95,
            original_text=record.normalized_text[name_start:name_end]
        ))
    
    # Pattern 4: Devanagari doctor names with clinical verbs
    # Check for डॉ./डॉक्टर followed by Devanagari name and clinical verb
    for match in re.finditer(r'(?:डॉ\.?|डॉक्टर)\s+([\u0900-\u097F]{2,}(?:\s+[\u0900-\u097F]{2,})+)', record.normalized_text):
        name_start = match.start(1)
        name_end = match.end(1)
        
        context = record.normalized_text[max(0, match.start()-50):match.end()+50]
        is_clinical = any(verb in context.lower() for verb in [
            'लिखा', 'लिखी', 'दिया', 'दिया', 'सुझाया', 'बताया',
            'prescribed', 'advised', 'recommended', 'treated',
            'diagnosed', 'examined', 'consulted', 'referred'
        ])
        
        if is_clinical:
            spans.append(MedicalSpan(
                start=name_start,
                end=name_end,
                medical_type=MedicalType.DOCTOR,
                confidence=0.95,
                original_text=record.normalized_text[name_start:name_end]
            ))
    
    # Pattern 5: "Dr. Name prescribed" / "Dr. Name advised" - Latin script
    for match in re.finditer(
        r'\b(?:Dr\.?|Doctor)\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)*[A-Z][a-z]+)\s+(?:prescribed|advised|recommended|treated|diagnosed|examined|consulted|referred|admitted|discharged)\b',
        record.normalized_text,
        re.IGNORECASE
    ):
        name_start = match.start(1)
        name_end = match.end(1)
        spans.append(MedicalSpan(
            start=name_start,
            end=name_end,
            medical_type=MedicalType.DOCTOR,
            confidence=0.95,
            original_text=record.normalized_text[name_start:name_end]
        ))
    
    # Pattern 6: Doctor names in field contexts (referred_by, doctor, consultant, etc.)
    # Matches patterns like: "referred_by: Dr. Name", "doctor: Dr. Name", "Consultant: Dr. Name"
    # Only match specific field names, not generic "doctor" word
    field_doctor_pattern = re.compile(
        r'(?:referred_by|referring_doctor|ref_doctor|referring doctor|attending_doctor|treating_doctor|consulting_doctor|consultant)\s*[:=]\s*(?:Dr\.?|Doctor)\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)*[A-Z][a-z]+)',
        re.IGNORECASE
    )
    for match in field_doctor_pattern.finditer(record.normalized_text):
        name_start = match.start(1)
        name_end = match.end(1)
        spans.append(MedicalSpan(
            start=name_start,
            end=name_end,
            medical_type=MedicalType.DOCTOR,
            confidence=0.9,
            original_text=record.normalized_text[name_start:name_end]
        ))
    
    # Pattern 7: "Consultant: Dr. Name" or "Consultant: Dr. Name (MD ...)"
    consultant_pattern = re.compile(
        r'\bConsultant\s*:\s*(?:Dr\.?|Doctor)\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)*[A-Z][a-z]+)',
        re.IGNORECASE
    )
    for match in consultant_pattern.finditer(record.normalized_text):
        name_start = match.start(1)
        name_end = match.end(1)
        spans.append(MedicalSpan(
            start=name_start,
            end=name_end,
            medical_type=MedicalType.DOCTOR,
            confidence=0.9,
            original_text=record.normalized_text[name_start:name_end]
        ))
    
    # Pattern 8: "with Dr. Name" or "with Doctor Name" in follow-up/review context
    # Matches: "with Dr. Vandana Kulshrestha", "with Doctor Smith", etc.
    with_doctor_pattern = re.compile(
        r'\bwith\s+(?:Dr\.?|Doctor)\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)*[A-Z][a-z]+)\b',
        re.IGNORECASE
    )
    for match in with_doctor_pattern.finditer(record.normalized_text):
        name_start = match.start(1)
        name_end = match.end(1)
        spans.append(MedicalSpan(
            start=name_start,
            end=name_end,
            medical_type=MedicalType.DOCTOR,
            confidence=0.85,
            original_text=record.normalized_text[name_start:name_end]
        ))
    
    # Pattern 9: "Dr. Name" at end of sentence or before punctuation in clinical context
    # Matches standalone "Dr. Name" that appears in clinical text
    # Only match if there's clinical context nearby
    standalone_doctor_pattern = re.compile(
        r'\b(?:Dr\.?|Doctor)\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)*[A-Z][a-z]+)\b',
        re.IGNORECASE
    )
    for match in standalone_doctor_pattern.finditer(record.normalized_text):
        name_start = match.start(1)
        name_end = match.end(1)
        # Check if this is in clinical context (near medical terms)
        context = record.normalized_text[max(0, match.start()-100):match.end()+100]
        clinical_context = any(term in context.lower() for term in [
            'prescribed', 'advised', 'recommended', 'treated', 'diagnosed',
            'examined', 'consulted', 'referred', 'admitted', 'discharged',
            'followup', 'follow-up', 'review', 'checkup', 'opd', 'ipd',
            'consultant', 'attending', 'treating', 'consulting',
            'diagnosis', 'medication', 'prescription', 'dosage',
            'mg', 'ml', 'tablet', 'capsule', 'injection',
            'bp', 'blood pressure', 'pulse', 'temperature', 'spo2',
            'haemoglobin', 'creatinine', 'sugar', 'sodium',
            'discharge', 'admission', 'ward', 'bed', 'hospital',
            'medicine', 'treatment', 'therapy', 'procedure',
            'review', 'follow', 'weeks', 'days', 'months'
        ])
        if clinical_context:
            spans.append(MedicalSpan(
                start=name_start,
                end=name_end,
                medical_type=MedicalType.DOCTOR,
                confidence=0.75,
                original_text=record.normalized_text[name_start:name_end]
            ))
    
    # Pattern 10: "referred by Dr. Name", "referred by Doctor Name"
    referred_by_pattern = re.compile(
        r'\breferred\s+by\s+(?:Dr\.?|Doctor)\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)*[A-Z][a-z]+)\b',
        re.IGNORECASE
    )
    for match in referred_by_pattern.finditer(record.normalized_text):
        name_start = match.start(1)
        name_end = match.end(1)
        spans.append(MedicalSpan(
            start=name_start,
            end=name_end,
            medical_type=MedicalType.DOCTOR,
            confidence=0.9,
            original_text=record.normalized_text[name_start:name_end]
        ))
    
    # Pattern 11: "under Dr. Name", "under Doctor Name"
    under_pattern = re.compile(
        r'\bunder\s+(?:Dr\.?|Doctor)\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)*[A-Z][a-z]+)\b',
        re.IGNORECASE
    )
    for match in under_pattern.finditer(record.normalized_text):
        name_start = match.start(1)
        name_end = match.end(1)
        spans.append(MedicalSpan(
            start=name_start,
            end=name_end,
            medical_type=MedicalType.DOCTOR,
            confidence=0.9,
            original_text=record.normalized_text[name_start:name_end]
        ))
    
    # Pattern 12: "by Dr. Name", "by Doctor Name" (in context of procedure/consultation)
    by_doctor_pattern = re.compile(
        r'\bby\s+(?:Dr\.?|Doctor)\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)*[A-Z][a-z]+)\b',
        re.IGNORECASE
    )
    for match in by_doctor_pattern.finditer(record.normalized_text):
        name_start = match.start(1)
        name_end = match.end(1)
        context = record.normalized_text[max(0, match.start()-50):match.end()+50]
        # Only if clinical context
        if any(term in context.lower() for term in ['procedure', 'surgery', 'operation', 'consult', 'refer', 'admit', 'discharge', 'treat', 'manage']):
            spans.append(MedicalSpan(
                start=name_start,
                end=name_end,
                medical_type=MedicalType.DOCTOR,
                confidence=0.85,
                original_text=record.normalized_text[name_start:name_end]
            ))
    
    # Pattern 13: "Dr. Name (MD/MS/DNB/DM/MCh/PhD/FRCS/MRCP/etc.)"
    doctor_degree_pattern = re.compile(
        r'\b(?:Dr\.?|Doctor)\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)*[A-Z][a-z]+)\s*\((?:MD|MS|DNB|DM|MCh|PhD|FRCS|MRCP|MRCOG|FACP|FACC|FSCAI|FAAN|FCCP|FASN|FAHA)\s*(?:,\s*(?:MD|MS|DNB|DM|MCh|PhD|FRCS|MRCP|MRCOG|FACP|FACC|FSCAI|FAAN|FCCP|FASN|FAHA))*\)',
        re.IGNORECASE
    )
    for match in doctor_degree_pattern.finditer(record.normalized_text):
        name_start = match.start(1)
        name_end = match.end(1)
        spans.append(MedicalSpan(
            start=name_start,
            end=name_end,
            medical_type=MedicalType.DOCTOR,
            confidence=0.95,
            original_text=record.normalized_text[name_start:name_end]
        ))
    
    return spans