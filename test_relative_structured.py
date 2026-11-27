import sys
sys.path.insert(0, '.')
from secret_wards.detection.structured import scan_structured_fields
from secret_wards.detection.normalize import apply_normalization
from secret_wards.contracts import UnifiedRecord, RecordLocation, RecordStatus, FieldValue, FieldType

text = 'Naseem'

rec = UnifiedRecord(
    record_id='test',
    location=RecordLocation.from_doc(),
    fields={'Relative Name': FieldValue(value=text, field_type=FieldType.STRING, path='Relative Name', original_text=text)},
    raw_text=text,
    normalized_text=text,
    offset_map=[],
    status=RecordStatus.PENDING
)

normalized_text, offset_map = apply_normalization(rec)
rec.normalized_text = normalized_text
rec.offset_map = offset_map

spans = scan_structured_fields(rec)
print(f'Structured spans: {len(spans)}')
for s in spans:
    print(f'  {s.pii_type}: "{s.original_text}" at {s.start}-{s.end} (conf: {s.confidence}, detector: {s.detector})')