import sys
sys.path.insert(0, '.')
from secret_wards.clinical.doctors import detect_doctors
from secret_wards.detection.normalize import apply_normalization
from secret_wards.contracts import UnifiedRecord, RecordLocation, RecordStatus, FieldValue, FieldType

# Test discharge summary text with doctor
text = '''Consultant: Dr. Vandana Kulshrestha (MD Medicine)

Patient admitted with complaints. BP 120/80, Pulse 72.

Advice: Low salt, diabetic diet. Review in OPD after 2 weeks with Dr. Vandana Kulshrestha.'''

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

doctor_spans = detect_doctors(rec)
print(f'Doctor spans: {len(doctor_spans)}')
for s in doctor_spans:
    print(f'  {s.medical_type}: "{s.original_text}" at {s.start}-{s.end} (conf: {s.confidence})')

# Also check the medical span detection
from secret_wards.clinical.veto import detect_all_medical_spans
medical_spans = detect_all_medical_spans(rec)
print(f'\nAll medical spans: {len(medical_spans)}')
for s in medical_spans:
    print(f'  {s.medical_type}: "{s.original_text}" at {s.start}-{s.end} (conf: {s.confidence})')