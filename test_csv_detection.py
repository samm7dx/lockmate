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
from secret_wards.contracts import UnifiedRecord, RecordLocation, RecordStatus, FieldValue, FieldType

# Parse the CSV file
intake = IntakePipeline(Path('.artifacts/toolkit/phase4-output-reg'))
docs, quarantine = intake.process_directory(Path('C:/Users/samri/Secret-Wards-ToolKit/dev/input/registration'))

for doc in docs:
    if '2d11b4b60e5d2aaa' in doc.source_file.sha256:
        print(f'Found CSV doc: {doc.source_file.sha256[:16]}')
        print(f'Records: {len(doc.records)}')
        
        for i, rec in enumerate(doc.records[:5]):
            print(f'\n=== Record {i} ===')
            print(f'Record ID: {rec.record_id}')
            print(f'Raw text (first 500): {rec.raw_text[:500].encode("ascii", "replace").decode("ascii")}')
            
            # Apply normalization
            normalized_text, offset_map = apply_normalization(rec)
            rec.normalized_text = normalized_text
            rec.offset_map = offset_map
            print(f'Normalized text (first 500): {normalized_text[:500].encode("ascii", "replace").decode("ascii")}')
            
            # Run detection
            pii_spans = []
            pii_spans.extend(detect_pii_placeholder(rec))
            pii_spans.extend(detect_identifiers(rec))
            pii_spans.extend(scan_structured_fields(rec))
            
            name_spans = detect_names(rec)
            print(f'Name spans: {len(name_spans)}')
            for s in name_spans:
                print(f'  Name: "{s.original_text}" at {s.start}-{s.end} (conf: {s.confidence}, detector: {s.detector})')
            
            pii_spans.extend(name_spans)
            
            # Clinical
            medical_spans = []
            medical_spans.extend(detect_drugs(rec))
            medical_spans.extend(detect_labs(rec))
            medical_spans.extend(detect_diagnoses(rec))
            medical_spans.extend(detect_doctors(rec))
            medical_spans.extend(detect_all_medical_spans(rec))
            
            print(f'Medical spans: {len(medical_spans)}')
            
            # Veto
            filtered = merge_spans_with_veto(pii_spans, medical_spans)
            print(f'Filtered PII spans: {len(filtered)} (from {len(pii_spans)})')
            for s in filtered:
                print(f'  PII: "{s.original_text}" at {s.start}-{s.end} (conf: {s.confidence}, type: {s.pii_type})')
            
            # Sanitize
            sanitized = sanitize_record(rec, filtered)
            print(f'Sanitized text (first 500): {sanitized.transformed_text[:500].encode("ascii", "replace").decode("ascii")}')
            print(f'Sanitized fields:')
            for k, v in sanitized.transformed_fields.items():
                if isinstance(v, str) and v != rec.fields.get(k, FieldValue(value='', field_type=FieldType.STRING, path=k)).value:
                    v_safe = v.encode("ascii", "replace").decode("ascii")
                    print(f'  {k}: "{v_safe}"')
        
        break