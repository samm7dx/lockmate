import sys
sys.path.insert(0, '.')
from secret_wards.detection.identifiers import detect_identifiers
from secret_wards.detection.normalize import apply_normalization
from secret_wards.contracts import UnifiedRecord, RecordLocation, RecordStatus, FieldValue, FieldType

# Test Village
text = 'Durgamau Kalan'

rec = UnifiedRecord(
    record_id='test',
    location=RecordLocation.from_doc(),
    fields={'village': FieldValue(value=text, field_type=FieldType.STRING, path='village', original_text=text)},
    raw_text=text,
    normalized_text=text,
    offset_map=[],
    status=RecordStatus.PENDING
)

normalized_text, offset_map = apply_normalization(rec)
rec.normalized_text = normalized_text
rec.offset_map = offset_map

spans = detect_identifiers(rec)
print(f'Village spans: {len(spans)}')
for s in spans:
    print(f'  {s.pii_type}: "{s.original_text}" at {s.start}-{s.end} (conf: {s.confidence}, detector: {s.detector})')

# Test UHID
text2 = 'SNJ/26/064127'
rec2 = UnifiedRecord(
    record_id='test2',
    location=RecordLocation.from_doc(),
    fields={'uhid': FieldValue(value=text2, field_type=FieldType.STRING, path='uhid', original_text=text2)},
    raw_text=text2,
    normalized_text=text2,
    offset_map=[],
    status=RecordStatus.PENDING
)

normalized_text2, offset_map2 = apply_normalization(rec2)
rec2.normalized_text = normalized_text2
rec2.offset_map = offset_map2

spans2 = detect_identifiers(rec2)
print(f'\nUHID spans: {len(spans2)}')
for s in spans2:
    print(f'  {s.pii_type}: "{s.original_text}" at {s.start}-{s.end} (conf: {s.confidence}, detector: {s.detector})')