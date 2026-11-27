import sys
sys.path.insert(0, '.')
from secret_wards.detection.structured import _scan_string_value

# Test Village field
text = 'Durgamau Kalan'
spans = _scan_string_value(text, 'Village/Mohalla', text)
print(f'Village spans: {len(spans)}')
for s in spans:
    print(f'  {s.pii_type}: "{s.original_text}" at {s.start}-{s.end} (conf: {s.confidence}, detector: {s.detector})')

# Test UHID field
text2 = 'SNJ/26/064127'
spans2 = _scan_string_value(text2, 'UHID', text2)
print(f'\nUHID spans: {len(spans2)}')
for s in spans2:
    print(f'  {s.pii_type}: "{s.original_text}" at {s.start}-{s.end} (conf: {s.confidence}, detector: {s.detector})')

# Test Address field
text3 = 'C/O Naresh Chauhan, H.No. 364, Ward 20, Mohalla Raja Bazar, near Pani Tanki, Tehsil Lalganj, Distt. Rae Bareli'
spans3 = _scan_string_value(text3, 'Address', text3)
print(f'\nAddress spans: {len(spans3)}')
for s in spans3:
    print(f'  {s.pii_type}: "{s.original_text}" at {s.start}-{s.end} (conf: {s.confidence}, detector: {s.detector})')