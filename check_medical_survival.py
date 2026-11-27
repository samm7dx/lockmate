import json
import sys
sys.path.insert(0, '.')

from secret_wards.intake.pipeline import IntakePipeline
from secret_wards.pipeline.full import _sanitize_document
from secret_wards.utils.metrics import ProcessingMetricsCollector
from pathlib import Path

# Load a document and check medical value preservation
intake = IntakePipeline(Path('C:/Users/samri/Secret-Wards-ToolKit/dev/input'))
docs, quarantine = intake.process_directory(Path('C:/Users/samri/Secret-Wards-ToolKit/dev/input'))

# Load truth
with open('C:/Users/samri/Secret-Wards-ToolKit/dev/truth/truth.json', encoding='utf-8') as f:
    truth = json.load(f)

# Get preserve values for registration/sanjeevani_registration.csv
f_name = 'registration/sanjeevani_registration.csv'
f_data = truth['files'][f_name]

preserve_values = []
for loc, u in f_data['units'].items():
    preserve_list = u.get('preserve', [])
    for pv in preserve_list:
        preserve_values.append(pv.get('text', ''))

print(f'Preserve values for {f_name}: {len(preserve_values)}')
for v in preserve_values[:20]:
    print(f'  "{v}"')

# Find the document
doc = None
for d in docs:
    if d.source_file.path.name == 'sanjeevani_registration.csv':
        doc = d
        break

if doc:
    print(f'\nFound document with {len(doc.records)} records')
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
    sanitized = _sanitize_document(doc, secret, stage)
    
    # Check sanitized output for preserve values
    all_sanitized_text = ""
    for sr in sanitized:
        all_sanitized_text += sr.transformed_text + "\n"
    
    print('\nChecking preservation in sanitized output:')
    for pv in preserve_values[:20]:
        found = pv in all_sanitized_text
        if not found:
            print(f'  MISSING: "{pv}"')
        else:
            print(f'  OK: "{pv}"')
    
    # Count missing
    missing = sum(1 for pv in preserve_values if pv not in all_sanitized_text)
    print(f'\nMissing: {missing}/{len(preserve_values)} = {missing/len(preserve_values)*100:.1f}%')