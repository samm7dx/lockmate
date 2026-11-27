"""
LOCKMATE — Lab, Vital, and Unit Detection

Detects laboratory names, vital signs, and clinical units.
"""

from __future__ import annotations

import re
from typing import List

from ..contracts import MedicalSpan, MedicalType
from ..utils.logging import get_logger_adapter
from ..detection.gazetteer import get_gazetteer

logger = get_logger_adapter("clinical.labs")


def detect_labs(record) -> List:
    """
    Detect lab names, vital signs, and units.
    
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
    
    # Lab names (from gazetteer - LOINC-derived)
    lab_names = gazetteer.get("medical_labs")
    for lab in lab_names:
        pattern = re.compile(r'\b' + re.escape(lab) + r'\b', re.IGNORECASE)
        for match in pattern.finditer(record.normalized_text):
            spans.append(MedicalSpan(
                start=match.start(),
                end=match.end(),
                medical_type=MedicalType.LAB,
                confidence=0.9,
                original_text=match.group()
            ))
    
    # Vital patterns (BP, HR, Temp, SpO2, etc.) - only in clear medical context
    # These patterns require clear medical context indicators
    vital_patterns = {
        MedicalType.VITAL: [
            # BP patterns - require "BP" prefix or clear context
            r'\bBP\s+\d{2,3}\s*/\s*\d{2,3}\b',
            r'\bBlood\s+Pressure\s+\d{2,3}\s*/\s*\d{2,3}\b',
            # Heart rate patterns - require HR/Pulse prefix
            r'\b(?:HR|Heart\s+Rate|Pulse)\s*[:]?\s*\d{2,3}\b',
            r'\bPulse\s*[:]?\s*\d{2,3}\b',
            # Respiratory rate
            r'\b(?:RR|Resp(?:iratory)?\s+Rate)\s*[:]?\s*\d{1,2}\b',
            # Temperature - require Temp prefix
            r'\bTemp(?:erature)?\s*[\d.]+\s*(?:°[CF]|[CF])\b',
            # SpO2/SaO2
            r'\b(?:SpO2|SaO2|O2\s+Sat(?:uration)?)\s+\d{2,3}\s*%?\b',
            # Additional vitals with clear prefixes
            r'\bETCO2\s+\d{1,2}\b',
            r'\bCVP\s+\d{1,2}\b',
            r'\bMAP\s+\d{2,3}\b',
        ],
        MedicalType.UNIT: [
            # Only units that appear with values in medical context
            r'\b\d+(?:\.\d+)?\s*(?:mg/dL|mmol/L|U/L|ng/mL|pg/mL|mIU/mL|IU/L|meq/L|mEq/L|mmHg|cmH2O)\b',
        ],
        # Lab values with numbers and units (e.g., "Hb 12.5 g/dL", "Creatinine 1.2 mg/dL")
        MedicalType.LAB: [
            r'\b(?:Hb|Hemoglobin|Haemoglobin|Hct|Hematocrit|RBC|WBC|Platelet|PLT)\s+\d+(?:\.\d+)?\s*(?:g/dL|mg/dL|/uL|/mm3|x10\^?3/uL|%)\b',
            r'\b(?:Creatinine|Cr|BUN|Urea|Glucose|Sugar|Na|Sodium|K|Potassium|Cl|Chloride|Ca|Calcium|Mg|Magnesium|PO4|Phosphate|Albumin|ALB|Bilirubin|Bili|AST|ALT|ALP|GGT|LDH|CK|Troponin|BNP|NT-proBNP|HbA1c|TSH|T3|T4|Free\s+T3|Free\s+T4|Vitamin\s+D|Vitamin\s+B12|Folate|Ferritin|Iron|TIBC|UIBC|Transferrin|PSA|CEA|CA-?125|CA-?19-?9|AFP|Beta\s+hCG)\s+\d+(?:\.\d+)?\s*(?:mg/dL|mmol/L|U/L|ng/mL|pg/mL|mIU/mL|IU/L|%|mEq/L|meq/L|mcmol/L)\b',
            r'\b(?:pH|pCO2|pO2|HCO3|Base\s+Excess|BE|Anion\s+Gap|Osmolality|Lactate|Ammonia|Uric\s+Acid|UA)\s+\d+(?:\.\d+)?\s*(?:mmHg|mmol/L|mg/dL|mEq/L|mOsm/kg)\b',
        ]
    }
    
    for med_type, patterns in vital_patterns.items():
        for pattern_str in patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            for match in pattern.finditer(record.normalized_text):
                spans.append(MedicalSpan(
                    start=match.start(),
                    end=match.end(),
                    medical_type=med_type,
                    confidence=0.9,
                    original_text=match.group()
                ))
    
    # Additional lab value patterns (number + unit combinations) - ONLY with clear lab name prefix
    # e.g., "Hb 12.5 g/dL", "Creatinine 2.4 mg/dL"
    lab_value_pattern = re.compile(
        r'\b(?:Hb|Hemoglobin|Haemoglobin|Hct|Hematocrit|RBC|WBC|Platelet|PLT|Creatinine|Cr|BUN|Urea|Glucose|Sugar|Na|Sodium|K|Potassium|Cl|Chloride|Ca|Calcium|Mg|Magnesium|PO4|Phosphate|Albumin|ALB|Bilirubin|Bili|AST|ALT|ALP|GGT|LDH|CK|Troponin|BNP|NT-proBNP|HbA1c|TSH|T3|T4|Free\s+T3|Free\s+T4|Vitamin\s+D|Vitamin\s+B12|Folate|Ferritin|Iron|TIBC|UIBC|Transferrin|PSA|CEA|CA-?125|CA-?19-?9|AFP|Beta\s+hCG|pH|pCO2|pO2|HCO3|Base\s+Excess|BE|Anion\s+Gap|Osmolality|Lactate|Ammonia|Uric\s+Acid|UA)\s+\d+(?:\.\d+)?\s*(?:g/dL|mg/dL|mmol/L|meq/L|mEq/L|U/L|ng/mL|pg/mL|mIU/mL|IU/L|%|mOsm/kg|mOsm/L)\b',
        re.IGNORECASE
    )
    for match in lab_value_pattern.finditer(record.normalized_text):
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