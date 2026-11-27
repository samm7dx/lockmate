import json
with open('C:/Users/samri/Secret-Wards-ToolKit/dev/truth/truth.json', encoding='utf-8') as f:
    truth = json.load(f)

# Find medical entities
medical_entities = []
for f_name, f_data in truth['files'].items():
    for loc, u in f_data['units'].items():
        for e in u['entities']:
            if e.get('type') in ['DRUG', 'DOSAGE', 'VITAL', 'LAB', 'DIAGNOSIS', 'PROCEDURE', 'UNIT', 'FREQUENCY', 'ROUTE', 'DURATION', 'ICD_CODE', 'MEDICAL_HISTORY', 'COMPLAINT']:
                medical_entities.append({
                    'file': f_name,
                    'loc': loc,
                    'type': e.get('type'),
                    'surface': e.get('surface')
                })

print(f'Total medical entities in truth: {len(medical_entities)}')
for m in medical_entities[:30]:
    print(f'  {m["type"]}: "{m["surface"]}" in {m["file"]}@{m["loc"]}')