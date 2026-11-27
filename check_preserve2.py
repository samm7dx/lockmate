import json
with open('C:/Users/samri/Secret-Wards-ToolKit/dev/truth/truth.json', encoding='utf-8') as f:
    truth = json.load(f)

# Find preserve entities - count by type
preserve_by_type = {}
preserve_count = 0
for f_name, f_data in truth['files'].items():
    for loc, u in f_data['units'].items():
        preserve_list = u.get('preserve', [])
        if preserve_list:
            preserve_count += len(preserve_list)
            for pv in preserve_list:
                pv_type = pv.get('type', 'None')
                pv_text = pv.get('text', '')
                if pv_type not in preserve_by_type:
                    preserve_by_type[pv_type] = []
                preserve_by_type[pv_type].append(pv_text)

print(f'Total preserve entries: {preserve_count}')
for pv_type, texts in preserve_by_type.items():
    print(f'\nType: {pv_type} ({len(texts)} entries)')
    unique_texts = set(texts)
    for t in sorted(unique_texts)[:10]:
        print(f'  "{t}" (x{texts.count(t)})')
    if len(unique_texts) > 10:
        print(f'  ... and {len(unique_texts) - 10} more unique values')