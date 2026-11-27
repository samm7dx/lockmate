import sys
sys.path.insert(0, '.')

from pathlib import Path
from secret_wards.intake.pipeline import IntakePipeline
from secret_wards.pipeline.full import _sanitize_document
from secret_wards.utils.metrics import ProcessingMetricsCollector

import json

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
                    'surface': e.get('surface')
                })

print(f'Total RELATIVE_NAME entities: {len(relative_entities)}')

# Sanitize all documents
intake = IntakePipeline(Path('C:/Users/samri/Secret-Wards-ToolKit/dev/input'))
docs, quarantine = intake.process_directory(Path('C:/Users/samri/Secret-Wards-ToolKit/dev/input'))

secret = b'practicesecretkeyfordevelopmenttestingonly123456'

class MockStage:
    def __init__(self):
        self.records_processed = 0
        self.identifiers_detected = 0
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass

stage = MockStage()

# Build sanitized text by file
sanitized_by_file = {}

for doc in docs:
    fname = doc.source_file.path.name
    sanitized = _sanitize_document(doc, secret, stage)
    
    all_sanitized_text = ""
    for sr in sanitized:
        all_sanitized_text += sr.transformed_text + "\n"
    
    sanitized_by_file[fname] = all_sanitized_text

# Check which relative names are missing
missing = []
for rel in relative_entities:
    fname = rel['file']
    surface = rel['surface']
    
    sanitized_text = sanitized_by_file.get(fname, '')
    if surface not in sanitized_text:
        missing.append(rel)

print(f'\nMissing RELATIVE_NAME values: {len(missing)}/{len(relative_entities)}')
for m in missing:
    print(f'  MISSING: "{m["surface"]}" in {m["file"]}@{m["loc"]}')