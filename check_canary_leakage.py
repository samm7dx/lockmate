import sys
sys.path.insert(0, '.')

import json
from pathlib import Path

# Load canary values
with open('C:/Users/samri/Secret-Wards-ToolKit/dev/truth/truth.json', encoding='utf-8') as f:
    truth = json.load(f)

canary_values = set()
if 'canaries' in truth:
    for canary in truth['canaries']:
        if isinstance(canary, str):
            canary_values.add(canary)
        elif isinstance(canary, dict):
            canary_values.add(canary.get('value', ''))
            canary_values.add(canary.get('encoded', ''))
            canary_values.add(canary.get('base64', ''))

print(f"Canary values: {len(canary_values)}")
for c in sorted(canary_values):
    if c:
        print(f"  {c[:50]}...")

# Check output files
print("\n=== Checking output files ===")
output_dir = Path('.artifacts/toolkit/phase4-output-final')
sanitized_dir = Path('.artifacts/toolkit/phase4-output-final/sanitized')

for f in sanitized_dir.rglob('*'):
    if f.is_file() and f.name not in ('report.json', 'records.jsonl'):
        try:
            content = f.read_text(encoding='utf-8')
            for canary in canary_values:
                if canary and canary in content:
                    print(f"  CANARY IN FILE: {f.name} -> {canary[:50]}...")
        except UnicodeDecodeError:
            pass

# Check records.jsonl
print("\n=== Checking records.jsonl ===")
records_file = Path('.artifacts/toolkit/phase4-output-final/records.jsonl')
if records_file.exists():
    with open(records_file, encoding='utf-8') as f:
        for i, line in enumerate(f):
            for canary in canary_values:
                if canary and canary in line:
                    print(f"  CANARY IN RECORDS LINE {i+1}: {canary[:50]}...")

# Check report.json
print("\n=== Checking report.json ===")
report_file = Path('.artifacts/toolkit/phase4-output-final/report.json')
if records_file.exists():
    with open('.artifacts/toolkit/phase4-output-final/report.json', encoding='utf-8') as f:
        content = f.read()
        for canary in canary_values:
            if canary and canary in content:
                print(f"  CANARY IN REPORT: {canary[:50]}...")

print("\n=== Done ===")