import json
with open('C:/Users/samri/Secret-Wards-ToolKit/dev/truth/truth.json', encoding='utf-8') as f:
    truth = json.load(f)

# Find RELATIVE_NAME entities
relative_entities = []
for f_name, f_data in truth['files'].items():
    for loc, u in f_data['units'].items():
        for e in u['entities']:
            if e.get('type') == 'RELATIVE_NAME':
                relative_entities.append({
                    'file': f_name,
                    'loc': loc,
                    'surface': e.get('surface'),
                    'script': e.get('script'),
                    'channel': e.get('channel')
                })

print(f'Total RELATIVE_NAME entities: {len(relative_entities)}')
for r in relative_entities[:50]:
    print(f'  "{r["surface"]}" in {r["file"]}@{r["loc"]} (script: {r["script"]}, channel: {r["channel"]})')

# Count unique surfaces
from collections import Counter
surfaces = Counter(r['surface'] for r in relative_entities)
print('\nUnique relative name surfaces:')
for surface, count in surfaces.most_common():
    print(f'  {count}x: "{surface}"')