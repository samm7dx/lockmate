import json
import sys
sys.path.insert(0, '.')

from pathlib import Path
from secret_wards.intake.pipeline import IntakePipeline
from secret_wards.pipeline.full import _sanitize_document
from secret_wards.utils.metrics import ProcessingMetricsCollector

# Load all documents
intake = IntakePipeline(Path('C:/Users/samri/Secret-Wards-ToolKit/dev/input'))
docs, quarantine = intake.process_directory(Path('C:/Users/samri/Secret-Wards-ToolKit/dev/input'))

# Load truth
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

# Sanitize all documents and check
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

# Check preservation
missing = []
for pv in all_preserve:
    fname = pv['file']
    text = pv['text']
    
    sanitized_text = sanitized_by_file.get(fname, '')
    if text not in sanitized_text:
        missing.append(pv)

print(f'\nMissing preserve values: {len(missing)}/{len(all_preserve)}')
print(f'Preservation rate: {(len(all_preserve)-len(missing))/len(all_preserve)*100:.1f}%')

# Show missing by file
by_file = {}
for m in missing:
    if m['file'] not in by_file:
        by_file[m['file']] = []
    by_file[m['file']].append(m['text'])

for f, texts in sorted(by_file.items(), key=lambda x: -len(x[1])):
    print(f'\n{f}: {len(texts)} missing')
    unique_texts = set(texts)
    for t in sorted(unique_texts)[:10]:
        print(f'  "{t}" (x{texts.count(t)})')
    if len(unique_texts) > 10:
        print(f'  ... and {len(unique_texts) - 10} more unique values')