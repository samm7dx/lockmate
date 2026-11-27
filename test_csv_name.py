import sys
sys.path.insert(0, '.')

from secret_wards.detection.names import detect_names
from secret_wards.detection.normalize import apply_normalization
from secret_wards.contracts import UnifiedRecord, RecordLocation, RecordStatus, FieldValue, FieldType

# Test with the CSV text
text = """trip,from,to,remarks
AMB-410,Sitapur,Lucknow,oxygen given en route
AMB-284,Sitapur,Lucknow,oxygen given en route
AMB-436,Sitapur,Lucknow,called by Kaveri Nambiar 94054-71434
AMB-318,Sitapur,Lucknow,oxygen given en route"""

rec = UnifiedRecord(
    record_id='test',
    location=RecordLocation.from_doc(),
    fields={'content': FieldValue(value=text, field_type=FieldType.STRING, path='content', original_text=text)},
    raw_text=text,
    normalized_text=text,
    offset_map=[],
    status=RecordStatus.PENDING
)

normalized_text, offset_map = apply_normalization(rec)
rec.normalized_text = normalized_text
rec.offset_map = offset_map

from secret_wards.detection.names import detect_names
name_spans = detect_names(rec)
print(f'Name spans: {len(name_spans)}')
for s in name_spans:
    print(f'  Name: "{s.original_text}" at {s.start}-{s.end} (conf: {s.confidence}, detector: {s.detector})')