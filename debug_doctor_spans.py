import sys
sys.path.insert(0, '.')
from secret_wards.intake.pipeline import IntakePipeline
from secret_wards.pipeline.full import _sanitize_document
from secret_wards.utils.metrics import ProcessingMetricsCollector
from pathlib import Path

intake = IntakePipeline(Path('C:/Users/samri/Secret-Wards-ToolKit/dev/input'))
docs, quarantine = intake.process_directory(Path('C:/Users/samri/Secret-Wards-ToolKit/dev/input'))

# Find a document with doctor names
for doc in docs:
    if doc.source_file.path.name == 'jeevanjyoti_patients.tsv':
        print(f'Found document: {doc.source_file.path.name} with {len(doc.records)} records')
        
        # Check first few records for doctor names
        for i, record in enumerate(doc.records[:5]):
            print(f'\nRecord {i}: {record.record_id}')
            print(f'  Raw text: {record.raw_text[:200]}')
            
            # Check fields
            for fname, fval in record.fields.items():
                if 'doctor' in fname.lower() or 'ref' in fname.lower():
                    print(f'  Field {fname}: {fval.value}')
        
        secret = b'practicesecretkeyfordevelopmenttestingonly123456'
        
        class MockStage:
            def __init__(self):
                self.records_processed = 0
                self.identifiers_detected = 0
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
        
        stage = MockStage()
        
        # Manually run the detection pipeline to debug
        from secret_wards.detection.normalize import apply_normalization
        from secret_wards.detection.names import detect_names
        from secret_wards.detection.identifiers import detect_identifiers
        from secret_wards.detection.structured import scan_structured_fields
        from secret_wards.detection.placeholder import detect_pii_placeholder
        from secret_wards.clinical.drugs import detect_drugs
        from secret_wards.clinical.labs import detect_labs
        from secret_wards.clinical.diagnoses import detect_diagnoses
        from secret_wards.clinical.doctors import detect_doctors
        from secret_wards.clinical.veto import merge_spans_with_veto, detect_all_medical_spans
        from secret_wards.transform.structured import sanitize_record
        from secret_wards.contracts import PIIType
        
        record = doc.records[0]
        print(f'\n--- Processing record {record.record_id} ---')
        
        # Normalize
        normalized_text, offset_map = apply_normalization(record)
        record.normalized_text = normalized_text
        record.offset_map = offset_map
        print(f'Normalized text: {normalized_text[:300]}')
        
        # Detect
        name_spans = detect_names(record)
        print(f'Name spans: {len(name_spans)}')
        for s in name_spans:
            print(f'  {s.pii_type}: "{s.original_text}" (conf: {s.confidence}, detector: {s.detector})')
        
        struct_spans = scan_structured_fields(record)
        print(f'Struct spans: {len(struct_spans)}')
        for s in struct_spans:
            print(f'  {s.pii_type}: "{s.original_text}" (conf: {s.confidence}, detector: {s.detector})')
        
        doctor_spans = detect_doctors(record)
        print(f'Doctor spans (clinical): {len(doctor_spans)}')
        for s in doctor_spans:
            print(f'  {s.medical_type}: "{s.original_text}" (conf: {s.confidence})')
        
        # Check for doctor spans in struct_spans
        doctor_struct = [s for s in struct_spans if s.pii_type == PIIType.DOCTOR]
        print(f'Doctor spans (struct): {len(doctor_struct)}')
        for s in doctor_struct:
            print(f'  {s.pii_type}: "{s.original_text}" (conf: {s.confidence}, detector: {s.detector})')
        
        break