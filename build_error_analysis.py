#!/usr/bin/env python3
"""
LOCKMATE — Exact Error Analysis System (Task 1)

Identifies every remaining leaked entity and missing medical preservation probe.
Classifies errors by entity type, script, hiding channel, hospital, parser, 
detection module, transformation module, and serialization.
"""

import json
import unicodedata
import re
from pathlib import Path
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import hashlib

# Load truth data
TRUTH_PATH = Path("C:/Users/samri/Secret-Wards-ToolKit/dev/truth/truth.json")
OUTPUT_DIR = Path(".artifacts/toolkit/phase4-output-final")
INPUT_DIR = Path("C:/Users/samri/Secret-Wards-ToolKit/dev/input")

def norm(s: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", s).casefold().split())

def read_text_safe(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

def get_file_sha256(p: Path) -> str:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except Exception:
        return ""

@dataclass
class LeakError:
    entity_type: str
    surface: str
    norm_surface: str
    script: str
    channel: str
    input_file: str
    location: str
    output_file: str
    root_cause: str
    parser: str
    detection_module: str
    transformation_module: str

@dataclass
class MedicalMissError:
    preserve_text: str
    norm_preserve: str
    preserve_type: str
    input_file: str
    location: str
    output_file: str
    root_cause: str
    parser: str
    clinical_module: str
    transformation_module: str

def load_truth():
    with open(TRUTH_PATH, encoding="utf-8") as f:
        return json.load(f)

def build_output_file_map():
    """Map input file SHA256 to output file path."""
    mapping = {}
    report_path = OUTPUT_DIR / "report.json"
    if report_path.exists():
        with open(report_path, encoding="utf-8") as f:
            report = json.load(f)
        for entry in report.get("files", []):
            if entry.get("output"):
                mapping[entry["input_sha256"]] = entry["output"]
    return mapping

def classify_script(text: str) -> str:
    """Classify script of text."""
    if not text:
        return "unknown"
    deva = sum(1 for c in text if '\u0900' <= c <= '\u097F')
    latin = sum(1 for c in text if c.isascii() and c.isalpha())
    if deva > latin:
        return "deva"
    elif latin > 0:
        return "latin"
    return "other"

def find_leaks():
    """Find all PII leaks in output."""
    truth = load_truth()
    output_map = build_output_file_map()
    
    # Read all output files
    output_texts = {}
    for f in OUTPUT_DIR.rglob("*"):
        if f.is_file() and f.name not in ("report.json", "records.jsonl"):
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                output_texts[str(f.relative_to(OUTPUT_DIR))] = content
            except Exception:
                pass
    
    leaks = []
    
    for rel_path, f_data in truth["files"].items():
        sha256 = f_data.get("sha256", "")
        out_rel = output_map.get(sha256, rel_path)
        
        # Get output text - check both the mapped file and the sanitized directory
        hay = ""
        # Check the mapped output file
        if out_rel in output_texts:
            hay = output_texts[out_rel]
        else:
            # Also check if there's a file in sanitized with the sha256 name
            sanitized_file = OUTPUT_DIR / "sanitized" / out_rel
            if sanitized_file.exists():
                try:
                    hay = sanitized_file.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    pass
        
        norm_hay = norm(hay)
        
        for loc, u in f_data["units"].items():
            for e in u["entities"]:
                if e.get("type") == "CANARY":
                    continue
                
                surface = e.get("surface", "")
                if not surface:
                    continue
                
                norm_surface = norm(surface)
                
                if norm_surface and norm_surface in norm(hay):
                    # This is a leak
                    script = e.get("script", "unknown")
                    channel = e.get("channel", "unknown")
                    parser = f_data.get("format", "unknown")  # Use format as parser
                    
                    # Determine root cause
                    root_cause = classify_leak_root_cause(e, f_data, out_rel)
                    
                    leaks.append(LeakError(
                        entity_type=e.get("type", "UNKNOWN"),
                        surface=surface,
                        norm_surface=norm_surface,
                        script=script,
                        channel=channel,
                        input_file=rel_path,
                        location=loc,
                        output_file=out_rel,
                        root_cause=root_cause,
                        parser=parser,
                        detection_module="unknown",
                        transformation_module="unknown"
                    ))
    
    return leaks

def classify_leak_root_cause(entity, file_data, output_file):
    """Classify the root cause of a leak."""
    e_type = entity.get("type", "")
    channel = entity.get("channel", "")
    parser = file_data.get("format", "")  # Use format field as parser
    
    if channel == "filename":
        return "filename_not_sanitized"
    elif channel == "base64":
        return "base64_not_decoded_in_sanitizer"
    elif channel == "header":
        return "header_not_sanitized"
    elif channel == "key":
        return "json_key_not_scanned"
    elif e_type in ("MRN", "UHID") and parser in ("csv", "tsv"):
        return "csv_mrn_pattern_not_detected"
    elif e_type == "INSURANCE_ID":
        return "insurance_id_pattern_not_comprehensive"
    elif e_type == "VILLAGE":
        return "village_field_not_detected"
    elif e_type == "PATIENT_NAME":
        return "name_not_detected_in_context"
    elif e_type == "RELATIVE_NAME":
        return "relative_name_field_not_comprehensive"
    elif e_type == "AADHAAR":
        return "aadhaar_verhoeff_rejected_valid_format"
    else:
        return f"unclassified_{e_type}_{channel}_{parser}"

def find_medical_misses():
    """Find all missing medical preservation values."""
    truth = load_truth()
    output_map = build_output_file_map()
    
    # Read all output files
    output_texts = {}
    for f in OUTPUT_DIR.rglob("*"):
        if f.is_file() and f.name not in ("report.json", "records.jsonl"):
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                output_texts[str(f.relative_to(OUTPUT_DIR))] = content
            except Exception:
                pass
    
    misses = []
    
    for rel_path, f_data in truth["files"].items():
        sha256 = f_data.get("sha256", "")
        out_rel = output_map.get(sha256, rel_path)
        
        # Get output text
        hay = ""
        if out_rel in output_texts:
            hay = output_texts[out_rel]
        else:
            # Also check sanitized directory
            sanitized_file = OUTPUT_DIR / "sanitized" / out_rel
            if sanitized_file.exists():
                try:
                    hay = sanitized_file.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    pass
        
        norm_hay = norm(hay)
        
        for loc, u in f_data["units"].items():
            preserve_list = u.get("preserve", [])
            for pv in preserve_list:
                preserve_text = pv.get("text", "")
                preserve_type = pv.get("type", "unknown")
                
                if not preserve_text:
                    continue
                
                # Infer type if null
                if preserve_type is None:
                    preserve_type = infer_preserve_type(preserve_text)
                
                norm_preserve = norm(preserve_text)
                if norm_preserve and norm_preserve not in norm(hay):
                    parser = f_data.get("format", "unknown")
                    root_cause = classify_medical_miss_root_cause(pv, f_data)
                    
                    misses.append(MedicalMissError(
                        preserve_text=preserve_text,
                        norm_preserve=norm_preserve,
                        preserve_type=preserve_type,
                        input_file=rel_path,
                        location=loc,
                        output_file=out_rel,
                        root_cause=root_cause,
                        parser=parser,
                        clinical_module="unknown",
                        transformation_module="unknown"
                    ))
    
    return misses

def infer_preserve_type(text: str) -> str:
    """Infer medical preserve type from text content."""
    text_lower = text.lower()
    
    # Doctor names
    if text.startswith("Dr.") or text.startswith("Dr ") or "Dr." in text or "Dr " in text:
        return "DOCTOR"
    
    # ICD codes
    import re
    if re.match(r'^[A-Z]\d{2}(\.\d+)?$', text):
        return "ICD_CODE"
    
    # Dosage patterns
    if re.search(r'\d+\s*(mg|ml|g|mcg|iu)', text_lower):
        return "DOSAGE"
    
    # Frequency patterns
    if re.search(r'\d+-\d+-\d+|once|twice|thrice|daily|weekly|monthly|od|bd|tds|qid|hs|sos', text_lower):
        return "FREQUENCY"
    
    # Duration patterns
    if re.search(r'\d+\s*(day|week|month|year|hr|hour|min)', text_lower):
        return "DURATION"
    
    # Vitals
    if any(v in text_lower for v in ['bp', 'blood pressure', 'pulse', 'temp', 'temperature', 'spo2', 'sp02']):
        return "VITAL"
    
    # Lab values
    if any(l in text_lower for l in ['haemoglobin', 'hemoglobin', 'creatinine', 'sugar', 'glucose', 'wbc', 'rbc', 'platelet', 'sodium', 'potassium', 'urea', 'bilirubin', 'alt', 'ast', 'alp', 'ggt', 'tsh', 'hba1c']):
        return "LAB_VALUE"
    
    # Diagnosis
    if any(d in text_lower for d in ['diabetes', 'hypertension', 'uti', 'infection', 'fever', 'cough', 'pain', 'syndrome', 'disease', 'disorder', 'cancer', 'carcinoma', 'tumor', 'anemia', 'thyroid', 'asthma', 'copd']):
        return "DIAGNOSIS"
    
    # Medicine/Drug names (common patterns)
    if re.search(r'\b(tab|cap|inj|syrup|drop|ointment|cream|gel)\b', text_lower):
        return "DRUG"
    
    # Route
    if re.search(r'\b(oral|iv|im|sc|subcut|topical|inhalation|sublingual)\b', text_lower):
        return "ROUTE"
    
    # Procedure
    if any(p in text_lower for p in ['surgery', 'operation', 'procedure', 'biopsy', 'endoscopy', 'colonoscopy', 'ecg', 'echo', 'xray', 'x-ray', 'ct', 'mri', 'ultrasound', 'ultrasonography']):
        return "PROCEDURE"
    
    return "UNKNOWN"


def classify_medical_miss_root_cause(pv, file_data):
    """Classify root cause of medical preservation miss."""
    p_type = pv.get("type")
    text = pv.get("text", "")
    parser = file_data.get("parser", "")
    
    # Handle None type - infer from text
    if p_type is None:
        p_type = infer_preserve_type(pv.get("text", ""))
    
    if p_type == "DOCTOR":
        return "doctor_not_recognized_in_clinical_context"
    elif p_type in ("DRUG", "MEDICINE"):
        return "drug_not_in_gazetteer"
    elif p_type in ("DOSAGE", "FREQUENCY", "DURATION"):
        return "dosage_pattern_not_recognized"
    elif p_type in ("VITAL", "LAB_VALUE", "LAB"):
        return "vital_lab_pattern_not_recognized"
    elif p_type in ("DIAGNOSIS", "ICD_CODE"):
        return "diagnosis_icd_pattern_not_recognized"
    elif p_type in ("MEDICAL_HISTORY", "COMPLAINT"):
        return "medical_history_not_preserved"
    elif "Dr." in text or "Dr " in text:
        return "doctor_name_redacted_as_name"
    else:
        return f"unclassified_medical_{p_type}_{parser}"

def main():
    print("=" * 80)
    print("LOCKMATE ERROR ANALYSIS SYSTEM - Task 1")
    print("=" * 80)
    
    print("\n[1/3] Finding PII leaks...")
    leaks = find_leaks()
    print(f"Found {len(leaks)} leaked entities")
    
    # Classify by type
    by_type = Counter(l.entity_type for l in leaks)
    print("\nLeaks by entity type:")
    for t, c in by_type.most_common():
        print(f"  {t}: {c}")
    
    by_script = Counter(l.script for l in leaks)
    print("\nLeaks by script:")
    for s, c in by_script.most_common():
        print(f"  {s}: {c}")
    
    by_channel = Counter(l.channel for l in leaks)
    print("\nLeaks by channel:")
    for c, count in by_channel.most_common():
        print(f"  {c}: {count}")
    
    by_root = Counter(l.root_cause for l in leaks)
    print("\nLeaks by root cause:")
    for r, count in by_root.most_common():
        print(f"  {r}: {count}")
    
    by_parser = Counter(l.parser for l in leaks)
    print("\nLeaks by parser:")
    for p, c in by_parser.most_common():
        print(f"  {p}: {c}")
    
    # Classify by hospital (from filename)
    by_hospital = Counter()
    for l in leaks:
        fname = l.input_file.lower()
        if "sanjeevani" in fname:
            by_hospital["sanjeevani"] += 1
        elif "jeevanjyoti" in fname:
            by_hospital["jeevanjyoti"] += 1
        elif "arogya" in fname:
            by_hospital["arogya"] += 1
        elif "dhhardoi" in fname or "dhh" in fname:
            by_hospital["dhhardoi"] += 1
        elif "city" in fname or "pathkind" in fname or "lifeline" in fname:
            by_hospital["labs"] += 1
        elif "discharge" in fname:
            by_hospital["discharge"] += 1
        else:
            by_hospital["other"] += 1
    print("\nLeaks by hospital:")
    for h, c in by_hospital.most_common():
        print(f"  {h}: {c}")
    
    print("\n[2/3] Finding medical preservation misses...")
    misses = find_medical_misses()
    print(f"Found {len(misses)} missing medical values")
    
    by_preserve_type = Counter(m.preserve_type for m in misses)
    print("\nMedical misses by type:")
    for t, c in by_preserve_type.most_common():
        print(f"  {t}: {c}")
    
    by_medical_root = Counter(m.root_cause for m in misses)
    print("\nMedical misses by root cause:")
    for r, c in by_medical_root.most_common():
        print(f"  {r}: {c}")
    
    by_medical_parser = Counter(m.parser for m in misses)
    print("\nMedical misses by parser:")
    for p, c in by_medical_parser.most_common():
        print(f"  {p}: {c}")
    
    print("\n[3/3] Saving detailed error reports...")
    
    # Save detailed reports
    leaks_report = {
        "summary": {
            "total_leaks": len(leaks),
            "by_type": dict(by_type),
            "by_script": dict(by_script),
            "by_channel": dict(by_channel),
            "by_root_cause": dict(by_root),
            "by_parser": dict(by_parser),
            "by_hospital": dict(by_hospital)
        },
        "leaks": [asdict(l) for l in leaks]
    }
    
    misses_report = {
        "summary": {
            "total_misses": len(misses),
            "by_preserve_type": dict(by_preserve_type),
            "by_root_cause": dict(by_medical_root),
            "by_parser": dict(by_medical_parser)
        },
        "misses": [asdict(m) for m in misses]
    }
    
    with open("error_analysis_leaks.json", "w", encoding="utf-8") as f:
        json.dump(leaks_report, f, indent=2, ensure_ascii=False)
    
    with open("error_analysis_medical_misses.json", "w", encoding="utf-8") as f:
        json.dump(misses_report, f, indent=2, ensure_ascii=False)
    
    print("Saved: error_analysis_leaks.json")
    print("Saved: error_analysis_medical_misses.json")
    
    print("\n" + "=" * 80)
    print("ERROR ANALYSIS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()