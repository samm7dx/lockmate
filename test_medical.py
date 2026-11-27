import sys
sys.path.insert(0, '.')
from secret_wards.clinical.veto import detect_all_medical_spans
from secret_wards.detection.normalize import apply_normalization
from secret_wards.contracts import UnifiedRecord, RecordLocation, RecordStatus, FieldValue, FieldType

text = 'Patient was given Tab Paracetamol 500mg and Inj Ceftriaxone 1g. BP 120/80, Pulse 72. Hb 12.5 g/dL. Diagnosed with Type 2 Diabetes (E11.9).'

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

medical_spans = detect_all_medical_spans(rec)
print(f'Medical spans: {len(medical_spans)}')
for s in medical_spans:
    print(f'  {s.medical_type}: "{s.original_text}" at {s.start}-{s.end} (conf: {s.confidence})')