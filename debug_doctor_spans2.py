import sys
sys.path.insert(0, '.')
import json
from secret_wards.intake.pipeline import IntakePipeline
from pathlib import Path

intake = IntakePipeline(Path('C:/Users/samri/Secret-Wards-ToolKit/dev/input'))
docs, quarantine = intake.process_directory(Path('C:/Users/samri/Secret-Wards-ToolKit/dev/input'))

# Find a document with doctor names
for doc in docs:
    if doc.source_file.path.name == 'jeevanjyoti_patients.tsv':
        print(f'Found document: {doc.source_file.path.name} with {len(doc.records)} records')
        
        # Check first few records for doctor names
        for i, record in enumerate(doc.records[:5]):
            # Check fields
            for fname, fval in record.fields.items():
                if 'doctor' in fname.lower() or 'ref' in fname.lower():
                    with open('debug_output.txt', 'a', encoding='utf-8') as f:
                        f.write(f'Record {i}: Field {fname}: {fval.value}\n')
        
        # Check all records for doctor fields
        with open('debug_output.txt', 'w', encoding='utf-8') as f:
            for i, record in enumerate(doc.records):
                for fname, fval in record.fields.items():
                    if 'doctor' in fname.lower() or 'ref' in fname.lower():
                        f.write(f'Record {i}: Field {fname}: {fval.value}\n')
        
        print('Done - check debug_output.txt')
        break