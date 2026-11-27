import sys
sys.path.insert(0, '.')
from secret_wards.detection.identifiers import detect_identifiers
from secret_wards.detection.normalize import apply_normalization
from secret_wards.detection.names import detect_names
from secret_wards.contracts import UnifiedRecord, RecordLocation, RecordStatus, FieldValue, FieldType

# Test relative name detection
text = 'W/o Naseem'

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

# Run detectors
all_spans = []
from secret_wards.detection.placeholder import detect_pii_placeholder
all_spans.extend(detect_pii_placeholder(rec))
all_spans.extend(detect_identifiers(rec))
all_spans.extend(detect_names(rec))

print(f'Total spans: {len(all_spans)}')
for s in all_spans:
    print(f'  {s.pii_type}: "{s.original_text}" at {s.start}-{s.end} (conf: {s.confidence}, detector: {s.detector})')