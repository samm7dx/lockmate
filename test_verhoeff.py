import sys
sys.path.insert(0, '.')

from secret_wards.detection.identifiers import verhoeff_checksum

test_numbers = [
    '879961914045',
    '771884036220',
    '590189835611',
    '872532468886',
    '606602802404',
    '826573307111',
    '471020182204',
    '826573307111',
]

for num in test_numbers:
    result = verhoeff_checksum(num)
    print(f'{num}: {"VALID" if result else "INVALID"}')