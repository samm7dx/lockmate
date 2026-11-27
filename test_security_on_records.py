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
from secret_wards.output.security_gate import ResidualPIIGate
from secret_wards.contracts import UnifiedRecord, RecordLocation, RecordStatus, FieldValue, FieldType
from secret_wards.utils.metrics import ProcessingMetricsCollector

# Parse the CSV file
intake = IntakePipeline(Path('.artifacts/toolkit/phase4-output-reg'))
docs, quarantine = intake.process_directory(Path('C:/Users/samri/Secret-Wards-ToolKit/dev/input/registration'))

for doc in docs:
    if '2d11b4b60e5d2aaa' in doc.source_file.sha256:
        print(f'Found CSV doc: {doc.source_file.sha256[:16]}')
        print(f'Records: {len(doc.records)}')
        
        # Sanitize all records
        sanitized_records = []
        for rec in doc.records:
            # Apply normalization
            normalized_text, offset_map = apply_normalization(rec)
            rec.normalized_text = normalized_text
            rec.offset_map = offset_map
            
            # Run detection
            pii_spans = []
            pii_spans.extend(detect_pii_placeholder(rec))
            pii_spans.extend(detect_identifiers(rec))
            pii_spans.extend(scan_structured_fields(rec))
            
            name_spans = detect_names(rec)
            pii_spans.extend(name_spans)
            
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
            sanitized_records.append(sanitized)
        
        print(f'\nSanitized {len(sanitized_records)} records')
        
        # Run security gate on sanitized records
        gate = ResidualPIIGate()
        gate_passed, residual_spans = gate.validate_output(sanitized_records, Path('.'))
        
        print(f'\nSecurity gate passed: {gate_passed}')
        print(f'Residual PII spans: {len(residual_spans)}')
        for s in residual_spans:
            print(f'  {s.pii_type}: "{s.original_text}" at {s.start}-{s.end} (detector: {s.detector})')
            print(f'  Context: {s.context[:100]}')
        
        break