import re

DEVANAGARI_NAME_PATTERN = re.compile(r'[\u0900-\u097F]{2,}(?:\s+[\u0900-\u097F]{2,})+')

# Test with actual Devanagari
text = 'विजय यादव'
matches = list(DEVANAGARI_NAME_PATTERN.finditer(text))
for m in matches:
    print('Group 0:', repr(m.group(0)))
    print('Groups:', m.groups())
    try:
        print('Group 1:', m.group(1))
    except IndexError as e:
        print('Group 1 error:', e)

# Also test the CAPS_NAME_PATTERN
CAPS_NAME_PATTERN = re.compile(r'\b([A-Z]{2,}(?:\s+[A-Z]\.?)*\s+[A-Z]{2,})\b')
text2 = 'VIJAY YADAV'
matches2 = list(CAPS_NAME_PATTERN.finditer(text2))
for m in matches2:
    print('CAPS Group 0:', repr(m.group(0)))
    print('CAPS Group 1:', repr(m.group(1)))
    print('CAPS Groups:', m.groups())

# Test TITLE_CASE_NAME_PATTERN
TITLE_CASE_NAME_PATTERN = re.compile(r'\b([A-Z][a-z]{2,}(?:\s+[A-Z]\.?)*\s+[A-Z][a-z]{2,})\b')
text3 = 'Vijay Yadav'
matches3 = list(TITLE_CASE_NAME_PATTERN.finditer(text3))
for m in matches3:
    print('TITLE Group 0:', repr(m.group(0)))
    print('TITLE Group 1:', repr(m.group(1)))
    print('TITLE Groups:', m.groups())