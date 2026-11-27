import sys
sys.path.insert(0, '.')

from pathlib import Path
from secret_wards.intake.pipeline import IntakePipeline
from secret_wards.detection.identifiers import detect_identifiers
from secret_wards.detection.normalize import apply_normalization
from secret_wards.transform.structured import _sanitize_field_value
from secret_wards.transform.replacer import DEFAULT_REPLACEMENTS
from secret_wards.contracts import FieldValue, FieldType

# Parse the CSV file
from secret_wards.intake.pipeline import IntakePipeline
from pathlib import Path

intake = IntakePipeline(Path('.artifacts/toolkit/phase4-output-reg'))
docs, quarantine = intake.process_directory(Path('C:/Users/samri/Secret-Wards-ToolKit/dev/input/registration'))

for doc in docs:
    if '2d11b4b60e5d2aaa' in doc.source_file.sha256:
        print(f'Found CSV doc: {doc.source_file.sha256[:16]}')
        
        # Check record 0 (first record)
        rec = doc.records[0]
        print(f'\n=== Record 0 ===')
        
        # Apply normalization
        normalized_text, offset_map = apply_normalization(rec)
        rec.normalized_text = normalized_text
        rec.offset_map = offset_map
        
        # Run identifier detection
        id_spans = detect_identifiers(rec)
        print(f'Identifier spans: {len(id_spans)}')
        for s in id_spans:
            if s.pii_type.name in ['AADHAAR', 'ABHA']:
                print(f'  {s.pii_type}: "{s.original_text}" at {s.start}-{s.end} (detector: {s.detector})')
        
        # Check ABHA No field
        abha_field = None
        for k, v in rec.fields.items():
            if 'ABHA' in k.upper() or 'AADHAAR' in k.upper():
                print(f'\nField: {k} = "{v.value}"')
                # Test sanitization
                from secret_wards.detection.identifiers import detect_identifiers
                from secret_wards.detection.normalize import apply_normalization
                
                # Create a mock record with just this field for testing
                from secret_wards.contracts import UnifiedRecord, RecordLocation, RecordStatus, FieldValue, FieldType
                
                test_rec = UnifiedRecord(
                    record_id="test",
                    location=RecordLocation.from_doc(),
                    fields={k: v},
                    raw_text=v.value,
                    normalized_text=v.value,
                    offset_map=[],
                    status=RecordStatus.PENDING
                )
                
                # Apply normalization
                norm_text, offset_map = apply_normalization(test_rec)
                test_rec.normalized_text = norm_text
                test_rec.offset_map = offset_map
                
                # Detect identifiers
                id_spans = detect_identifiers(test_rec)
                print(f'  Identifier spans for {k}: {len(id_spans)}')
                for s in id_spans:
                    if s.pii_type.name in ['AADHAAR', 'ABHA']:
                        print(f'    {s.pii_type}: "{s.original_text}" at {s.start}-{s.end} (detector: {s.detector})')
                
                # Test sanitization
                from secret_wards.transform.replacer import DEFAULT_REPLACEMENTS
                sanitized = _sanitize_field_value(v, id_spans, DEFAULT_REPLACEMENTS)
                print(f'  Original: "{v.value}"')
                print(f'  Sanitized: "{sanitized}"')
        
        break