import json
with open('C:/Users/samri/Secret-Wards-ToolKit/dev/truth/truth.json', encoding='utf-8') as f:
    truth = json.load(f)

# Find preserve entities
preserve_count = 0
for f_name, f_data in truth['files'].items():
    for loc, u in f_data['units'].items():
        preserve_list = u.get('preserve', [])
        if preserve_list:
            preserve_count += len(preserve_list)
            print(f'File: {f_name}, Loc: {loc}')
            for pv in preserve_list:
                print(f'  Preserve: "{pv.get("text")}" type: {pv.get("type")}')

print(f'\nTotal preserve entries: {preserve_count}')