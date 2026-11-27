import re

DEVANAGARI_NAME_PATTERN = re.compile(r'[\u0900-\u097F]{2,}(?:\s+[\u0900-\u097F]{2,})+')

# Test with actual Devanagari
text = '\u0935\u093f\u091c\u092f \u092f\u093e\u0926\u0935'  # विजय यादव
matches = list(DEVANAGARI_NAME_PATTERN.finditer(text))
for m in matches:
    with open('regex_output.txt', 'w', encoding='utf-8') as f:
        f.write('Group 0: ' + repr(m.group(0)) + '\n')
        f.write('Groups: ' + str(m.groups()) + '\n')
        try:
            f.write('Group 1: ' + repr(m.group(1)) + '\n')
        except IndexError as e:
            f.write('Group 1 error: ' + str(e) + '\n')

# Also test the CAPS_NAME_PATTERN
CAPS_NAME_PATTERN = re.compile(r'\b([A-Z]{2,}(?:\s+[A-Z]\.?)*\s+[A-Z]{2,})\b')
text2 = 'VIJAY YADAV'
matches2 = list(CAPS_NAME_PATTERN.finditer(text2))
with open('regex_output.txt', 'a', encoding='utf-8') as f:
    for m in matches2:
        f.write('CAPS Group 0: ' + repr(m.group(0)) + '\n')
        f.write('CAPS Group 1: ' + repr(m.group(1)) + '\n')
        f.write('CAPS Groups: ' + str(m.groups()) + '\n')

# Test TITLE_CASE_NAME_PATTERN
TITLE_CASE_NAME_PATTERN = re.compile(r'\b([A-Z][a-z]{2,}(?:\s+[A-Z]\.?)*\s+[A-Z][a-z]{2,})\b')
text3 = 'Vijay Yadav'
matches3 = list(TITLE_CASE_NAME_PATTERN.finditer(text3))
with open('regex_output.txt', 'a', encoding='utf-8') as f:
    for m in matches3:
        f.write('TITLE Group 0: ' + repr(m.group(0)) + '\n')
        f.write('TITLE Group 1: ' + repr(m.group(1)) + '\n')
        f.write('TITLE Groups: ' + str(m.groups()) + '\n')