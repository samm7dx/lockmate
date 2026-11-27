import re
AADHAAR_PATTERN = re.compile(r'\b\d{4}[\-\s]?\d{4}[\-\s]?\d{4}\b')
test_strings = [
    '8799 6191 4045',
    '7718 8403 6220',
    '5901 8983 5611',
    '8725 3246 8886',
    '606602802404',
    '8265 7330 7111',
    '4710 2018 2204',
    '8265 7330 7111',
]
for s in test_strings:
    matches = list(AADHAAR_PATTERN.finditer(s))
    print(f'{s}: {len(matches)} matches')
    for m in matches:
        print(f'  Match: "{m.group()}" at {m.start()}-{m.end()}')