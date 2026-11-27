import sys
sys.path.insert(0, '.')
from secret_wards.detection.names import detect_names
from secret_wards.detection.normalize import apply_normalization
from secret_wards.contracts import UnifiedRecord, RecordLocation, RecordStatus, FieldValue, FieldType

text = '''SANJEEVANI MULTISPECIALITY HOSPITAL, LUCKNOW
DISCHARGE SUMMARY

Patient Name: Fatima Bano        Age/Sex: 52 Yrs/F
UHID: SNJ/26/064508        IPD No: IPD-2026-00461
W/o Naseem
Address: Makan No. 143, near Kali Mata Mandir, Vill. Jalalnagar Khurd, Tehsil Dalmau, Distt. Rae Bareli - 229678
Mobile: +91 84631 22585
Consultant: Dr. Vandana Kulshrestha (MD Medicine)
Ward/Bed: Ward 4 (Medicine) / Bed 29
Date of Admission: 07/02/2026
Date of Discharge: 19/02/2026
DOB: 30/10/1973

Diagnosis: Urinary tract infection, site not specified (N39.0); 
Presenting complaints: C/O fever for 6 days, generalised weakness.
History: No K/C/O DM/HTN. No significant past history.
Course in hospital: Patient admitted with above complaints. BP 128/85 mmHg, Pulse 64/min, Temp 99.0 F, SpO2 97%. Haemoglobin 8.2 g/dL. Random Blood Sugar 216 mg/dL. Serum Creatinine 3.2 mg/dL. Treated conservatively. Fatima amma ki condition ab stable hai.

Medications on discharge:
 1. Cap Doxycycline 100 mg 1-0-1 x 15 days

Advice: Low salt, diabetic diet. Review in OPD after 2 weeks with Dr. Vandana Kulshrestha.
Attendant: Naseem, Mob. 8463122585'''

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

name_spans = detect_names(rec)
print(f'Name spans: {len(name_spans)}')
for s in name_spans:
    print(f'  {s.pii_type}: "{s.original_text}" at {s.start}-{s.end} (conf: {s.confidence}, detector: {s.detector})')