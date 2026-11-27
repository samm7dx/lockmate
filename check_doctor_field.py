import sys
sys.path.insert(0, '.')
from secret_wards.detection.structured import _scan_string_value

# Test doctor name in doctor field
text = 'Dr. Vandana Kulshrestha'
spans = _scan_string_value(text, 'ref_doctor', text)
print(f'ref_doctor field:')
for s in spans:
    print(f'  {s.pii_type}: "{s.original_text}" (conf: {s.confidence}, detector: {s.detector})')

print()

# Test bare doctor name in doctor field
text2 = 'Vandana Kulshrestha'
spans2 = _scan_string_value(text2, 'ref_doctor', text2)
print(f'ref_doctor field (bare name):')
for s in spans2:
    print(f'  {s.pii_type}: "{s.original_text}" (conf: {s.confidence}, detector: {s.detector})')

print()

# Test doctor name in non-doctor field
text3 = 'Dr. Vandana Kulshrestha'
spans3 = _scan_string_value(text3, 'content', text3)
print(f'content field:')
for s in spans3:
    print(f'  {s.pii_type}: "{s.original_text}" (conf: {s.confidence}, detector: {s.detector})')