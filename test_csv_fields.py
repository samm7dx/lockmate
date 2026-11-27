import sys
sys.path.insert(0, '.')
from secret_wards.detection.structured import _scan_string_value

# Test single-word village names
villages = ['Amardih', 'Govindnagar', 'Jalalpur', 'Rajapur', 'Bhimganj', 'Mohangarh', 'Shivgarh', 'Ramkhera']
for v in villages:
    spans = _scan_string_value(v, 'Village/Mohalla', v)
    print(f'Village "{v}": {len(spans)} spans')
    for s in spans:
        print(f'  {s.pii_type}: "{s.original_text}" (conf: {s.confidence}, detector: {s.detector})')

print()

# Test house patterns
houses = ['House 87', 'House 452', 'House 12', 'House 263', 'House 182', 'House 389', 'House 33']
for h in houses:
    spans = _scan_string_value(h, 'Address', h)
    print(f'House "{h}": {len(spans)} spans')
    for s in spans:
        print(f'  {s.pii_type}: "{s.original_text}" (conf: {s.confidence}, detector: {s.detector})')

print()

# Test relative names
relatives = ['Naseem', 'Zubair']
for r in relatives:
    spans = _scan_string_value(r, 'Relative Name', r)
    print(f'Relative "{r}": {len(spans)} spans')
    for s in spans:
        print(f'  {s.pii_type}: "{s.original_text}" (conf: {s.confidence}, detector: {s.detector})')