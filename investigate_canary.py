import sys
sys.path.insert(0, '.')

from pathlib import Path
from secret_wards.intake.pipeline import IntakePipeline
from secret_wards.detection.names import detect_names
from secret_wards.detection.normalize import apply_normalization
from secret_wards.detection.identifiers import detect_identifiers
from secret_wards.detection.structured import scan_structured_fields
from secret_wards.detection.placeholder import detect_pii_placeholder
from secret_wards.clinical.drugs import detect_drugs
from secret_wards.clinical.labs import detect_labs
from secret_wards.clinical.diagnoses import detect_diagnoses
from secret_wards.clinical.doctors import detect_doctors
from secret_wards.clinical.veto import merge_spans_with_veto, detect_all_medical_spans
from secret_wards.transform.structured import sanitize_record
from secret_wards.output.security_gate import scan_output_directory
from secret_wards.contracts import UnifiedRecord, RecordLocation, RecordStatus, FieldValue, FieldType
from secret_wards.utils.metrics import ProcessingMetricsCollector
import hashlib

# Load practice dataset and truth
from secret_wards.intake.pipeline import IntakePipeline
intake = IntakePipeline(Path('C:/Users/samri/Secret-Wards-ToolKit/dev/input'))
docs, quarantine = intake.process_directory(Path('C:/Users/samri/Secret-Wards-ToolKit/dev/input'))

# Load truth
import json
with open('C:/Users/samri/Secret-Wards-ToolKit/dev/truth/truth.json', encoding='utf-8') as f:
    truth = json.load(f)

# Load canary values from truth
canary_values = set()
if 'canaries' in truth:
    for canary in truth['canaries']:
        if isinstance(canary, str):
            canary_values.add(canary)
        elif isinstance(canary, dict):
            canary_values.add(canary.get('value', ''))
            canary_values.add(canary.get('encoded', ''))
            canary_values.add(canary.get('base64', ''))

print(f"Canary values to search for: {len(canary_values)}")
for c in sorted(canary_values):
    if c:
        print(f"  {c[:50]}...")

# Process all docs and check for canaries in output
print("\n=== Scanning all records for canary leakage ===")
collector = ProcessingMetricsCollector()
all_sanitized = []

for doc in docs:
    file_sha256 = doc.source_file.sha256
    
    for rec in doc.records:
        # Normalize
        normalized_text, offset_map = apply_normalization(rec)
        rec.normalized_text = normalized_text
        rec.offset_map = offset_map
        
        # Detection
        pii_spans = []
        pii_spans.extend(detect_pii_placeholder(rec))
        pii_spans.extend(detect_identifiers(rec))
        pii_spans.extend(scan_structured_fields(rec))
        pii_spans.extend(detect_names(rec))
        
        # Clinical
        medical_spans = []
        medical_spans.extend(detect_drugs(rec))
        medical_spans.extend(detect_labs(rec))
        medical_spans.extend(detect_diagnoses(rec))
        medical_spans.extend(detect_doctors(rec))
        medical_spans.extend(detect_all_medical_spans(rec))
        
        # Veto
        filtered = merge_spans_with_veto(pii_spans, medical_spans)
        
        # Sanitize
        sanitized = sanitize_record(rec, filtered)
        all_sanitized.append(sanitized)

# Check sanitized records for canaries
print(f"\nTotal sanitized records: {len(all_sanitized)}")
canary_found = []

for sr in all_sanitized:
    text = sr.transformed_text
    for canary in canary_values:
        if canary and canary in text:
            canary_found.append({
                'record': sr.record.record_id,
                'canary': canary[:50],
                'context': text[max(0, text.index(canary)):text.index(canary)+100]
            })

print(f"\nCanaries found in sanitized text: {len(canary_found)}")
for cf in canary_found:
    print(f"  Record: {cf['record']}")
    print(f"  Canary: {cf['canary']}")
    print(f"  Context: {cf['context']}")

# Check structured fields
print("\n=== Checking structured fields ===")
for sr in all_sanitized:
    for field_path, field_val in sr.transformed_fields.items():
        if isinstance(field_val, str):
            for canary in canary_values:
                if canary and canary in field_val:
                    print(f"  CANARY IN FIELD: {sr.record.record_id}.{field_path} = {canary[:50]}")
        elif isinstance(field_val, dict):
            for k, v in field_val.items():
                if isinstance(v, str):
                    for canary in canary_values:
                        if canary and canary in v:
                            print(f"  CANARY IN NESTED: {sr.record.record_id}.{field_path}.{k} = {canary[:50]}")
        elif isinstance(field_val, list):
            for i, item in enumerate(field_val):
                if isinstance(item, str):
                    for canary in canary_values:
                        if canary and canary in item:
                            print(f"  CANARY IN LIST: {sr.record.record_id}.{field_path}[{i}] = {canary[:50]}")

# Check output files
print("\n=== Checking output files ===")
output_dir = Path('.artifacts/toolkit/phase4-output-final')
sanitized_dir = Path('.artifacts/toolkit/phase4-output-final/sanitized')

for f in sanitized_dir.rglob('*'):
    if f.is_file() and f.name not in ('report.json', 'records.jsonl'):
        try:
            content = f.read_text(encoding='utf-8')
            for canary in canary_values:
                if canary and canary in content:
                    print(f"  CANARY IN FILE: {f.name} -> {canary[:50]}")
        except UnicodeDecodeError:
            pass

print("\n=== Done ===")