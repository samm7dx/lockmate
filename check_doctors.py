import sys
sys.path.insert(0, '.')
from secret_wards.detection.identifiers import detect_identifiers
from secret_wards.detection.normalize import apply_normalization
from secret_wards.detection.structured import scan_structured_fields
from secret_wards.detection.placeholder import detect_pii_placeholder
from secret_wards.detection.names import detect_names
from secret_wards.clinical.doctors import detect_doctors
from secret_wards.contracts import UnifiedRecord, RecordLocation, RecordStatus, FieldValue, FieldType

# Test doctor name detection
text = 'Dr. Vandana Kulshrestha'

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

# Run all detectors
all_spans = []
all_spans.extend(detect_pii_placeholder(rec))
all_spans.extend(detect_identifiers(rec))
all_spans.extend(scan_structured_fields(rec))
all_spans.extend(detect_names(rec))
all_spans.extend(detect_doctors(rec))

print(f'Total spans: {len(all_spans)}')
for s in all_spans:
    print(f'  {s.pii_type}: "{s.original_text}" at {s.start}-{s.end} (conf: {s.confidence}, detector: {s.detector})')

print('\n--- Testing dosage "1-0-0" ---')
text2 = '1-0-0'
rec2 = UnifiedRecord(
    record_id='test2',
    location=RecordLocation.from_doc(),
    fields={'content': FieldValue(value=text2, field_type=FieldType.STRING, path='content', original_text=text2)},
    raw_text=text2,
    normalized_text=text2,
    offset_map=[],
    status=RecordStatus.PENDING
)

normalized_text2, offset_map2 = apply_normalization(rec2)
rec2.normalized_text = normalized_text2
rec2.offset_map = offset_map2

all_spans2 = []
all_spans2.extend(detect_pii_placeholder(rec2))
all_spans2.extend(detect_identifiers(rec2))
all_spans2.extend(scan_structured_fields(rec2))
all_spans2.extend(detect_names(rec2))
all_spans2.extend(detect_doctors(rec2))

print(f'Total spans: {len(all_spans2)}')
for s in all_spans2:
    print(f'  {s.pii_type}: "{s.original_text}" at {s.start}-{s.end} (conf: {s.confidence}, detector: {s.detector})')