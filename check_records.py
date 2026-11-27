import json
with open('.artifacts/toolkit/phase4-output-final/records.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            r = json.loads(line)
            if 'Discharge' in r.get('file', ''):
                print('File:', r['file'], 'Loc:', r['loc'])