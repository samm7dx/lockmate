import json

# Load truth and check what preserve values exist
with open('C:/Users/samri/Secret-Wards-ToolKit/dev/truth/truth.json', encoding='utf-8') as f:
    truth = json.load(f)

# Collect all preserve values
all_preserve = []
for f_name, f_data in truth['files'].items():
    for loc, u in f_data['units'].items():
        preserve_list = u.get('preserve', [])
        for pv in preserve_list:
            all_preserve.append({
                'file': f_name,
                'loc': loc,
                'text': pv.get('text', '')
            })

print(f'Total preserve entries: {len(all_preserve)}')

# Group by text value
from collections import Counter
preserve_counter = Counter(p['text'] for p in all_preserve)
print('\nTop preserve values by frequency:')
for text, count in preserve_counter.most_common(30):
    print(f'  {count}x: "{text}"')