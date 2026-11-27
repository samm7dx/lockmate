import sys
sys.path.insert(0, '.')

import json
import re
import unicodedata
from pathlib import Path
from secret_wards.intake.pipeline import IntakePipeline
from secret_wards.pipeline.full import _sanitize_document
from secret_wards.utils.metrics import ProcessingMetricsCollector

def norm(s: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", s).casefold().split())

# Load truth
with open('C:/Users/samri/Secret-Wards-ToolKit/dev/truth/truth.json', encoding='utf-8') as f:
    truth = json.load(f)

# Get all RELATIVE_NAME entities
relative_entities = []
for f_name, f_data in truth['files'].items():
    for loc, u in f_data['units'].items():
        for e in u['entities']:
            if e.get('type') == 'RELATIVE_NAME':
                relative_entities.append({
                    'file': f_name,
                    'loc': loc,
                    'surface': e.get('surface'),
                    'norm_surface': norm(e.get('surface'))
                })

print(f'Total RELATIVE_NAME entities: {len(relative_entities)}')

# Load all sanitized output files
sanitized_dir = Path('.artifacts/toolkit/phase4-output-final/sanitized')
file_texts = {}
for f in sanitized_dir.rglob('*'):
    if f.is_file() and f.name not in ('report.json', 'records.jsonl'):
        try:
            text = f.read_text(encoding='utf-8')
            file_texts[f.name] = norm(text)
        except UnicodeDecodeError:
            pass

# Check each entity
missing = []
for rel in relative_entities:
    # Find the sanitized file for this input file
    # The output files have SHA256 names, need to map
    # For now, just check all sanitized files
    found = False
    for fname, text in file_texts.items():
        if rel['norm_surface'] in text:
            found = True
            break
    if not found:
        missing.append(rel)

print(f'\nMissing RELATIVE_NAME values: {len(missing)}/{len(relative_entities)}')
for m in missing[:20]:
    print(f'  MISSING: "{m["surface"]}" in {m["file"]}@{m["loc"]}')