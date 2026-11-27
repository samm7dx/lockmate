import sys
sys.path.insert(0, '.')
from secret_wards.detection.structured import _scan_string_value

# Test bare relative name in Relative Name field
text = 'Naseem'
spans = _scan_string_value(text, 'Relative Name', text)
print(f'Relative Name field "Naseem":')
for s in spans:
    print(f'  {s.pii_type}: "{s.original_text}" (conf: {s.confidence}, detector: {s.detector})')

print()

# Test relative name with prefix
text2 = 'W/o Naseem'
spans2 = _scan_string_value(text2, 'Relative Name', text2)
print(f'Relative Name field "W/o Naseem":')
for s in spans2:
    print(f'  {s.pii_type}: "{s.original_text}" (conf: {s.confidence}, detector: {s.detector})')

print()

# Test full name
text3 = 'Naresh Chauhan'
spans3 = _scan_string_value(text3, 'Relative Name', text3)
print(f'Relative Name field "Naresh Chauhan":')
for s in spans3:
    print(f'  {s.pii_type}: "{s.original_text}" (conf: {s.confidence}, detector: {s.detector})')