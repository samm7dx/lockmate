import json
with open('C:/Users/samri/Secret-Wards-ToolKit/dev/truth/truth.json', encoding='utf-8') as f:
    truth = json.load(f)

# Find all entity types
entity_types = set()
for f_name, f_data in truth['files'].items():
    for loc, u in f_data['units'].items():
        for e in u['entities']:
            entity_types.add(e.get('type'))

print('All entity types in truth:')
for t in sorted(entity_types):
    print(f'  {t}')

# Count medical-related entities
medical_types = ['DRUG', 'DOSAGE', 'VITAL', 'LAB', 'DIAGNOSIS', 'PROCEDURE', 'UNIT', 'FREQUENCY', 'ROUTE', 'DURATION', 'ICD_CODE', 'MEDICAL_HISTORY', 'COMPLAINT', 'MEDICINE', 'VITALS', 'LAB_VALUE', 'DIAGNOSIS_CODE']
for mt in medical_types:
    count = sum(1 for f_name, f_data in truth['files'].items() for loc, u in f_data['units'].items() for e in u['entities'] if e.get('type') == mt)
    if count > 0:
        print(f'  {mt}: {count}')