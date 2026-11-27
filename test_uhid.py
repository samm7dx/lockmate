import re
UHID_MRN_PATTERN_V2 = re.compile(
    r'\b(?:UHID|MRN|UHID/MRN|CRNO|IPNO|OPNO|REGNO|REG\s+NO|PATIENT\s+ID|PATIENT\s+NO\.?)\s*[:\-]?\s*([A-Za-z0-9]{6,20})\b',
    re.IGNORECASE
)
test = 'UHID: adm000162'
matches = list(UHID_MRN_PATTERN_V2.finditer(test))
for m in matches:
    print('Full match: "' + m.group() + '" at ' + str(m.start()) + '-' + str(m.end()))
    print('Group 1: "' + m.group(1) + '" at ' + str(m.start(1)) + '-' + str(m.end(1)))