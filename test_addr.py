import sys
sys.path.insert(0, '.')
from secret_wards.detection.identifiers import detect_identifiers
from secret_wards.detection.normalize import apply_normalization
from secret_wards.contracts import UnifiedRecord, RecordLocation, RecordStatus, FieldValue, FieldType

text = 'C/O Naresh Chauhan, H.No. 364, Ward 20, Mohalla Raja Bazar, near Pani Tanki, Tehsil Lalganj, Distt. Rae Bareli'

rec = UnifiedRecord(
    record_id='test',
    location=RecordLocation.from_doc(),
    fields={'address': FieldValue(value=text, field_type=FieldType.STRING, path='address', original_text=text)},
    raw_text=text,
    normalized_text=text,
    offset_map=[],
    status=RecordStatus.PENDING
)

normalized_text, offset_map = apply_normalization(rec)
rec.normalized_text = normalized_text
rec.offset_map = offset_map

spans = detect_identifiers(rec)
print(f'Identifier spans: {len(spans)}')
for s in spans:
    print(f'  {s.pii_type}: "{s.original_text}" at {s.start}-{s.end} (conf: {s.confidence}, detector: {s.detector})')