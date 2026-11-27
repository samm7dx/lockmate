import json
with open('.artifacts/toolkit/phase4-output-final/report.json', 'r', encoding='utf-8') as f:
    report = json.load(f)
    for entry in report.get('files', []):
        output = entry.get('output')
        if output and 'discharge' in output.lower():
            print('Output:', output, 'SHA:', entry.get('input_sha256'))