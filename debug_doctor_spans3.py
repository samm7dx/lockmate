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
        
        # Check all fields in first record
        record = doc.records[0]
        with open('debug_fields.txt', 'w', encoding='utf-8') as f:
            f.write(f'Record 0 fields:\n')
            for fname, fval in record.fields.items():
                f.write(f'  {fname}: {fval.value}\n')
        
        # Check all records for any field containing doctor names
        doctor_names = ['Vandana Kulshrestha', 'Ramesh Srivastava', 'Harjeet Bedi', 'Imtiaz Ahmed']
        with open('debug_doctor_fields.txt', 'w', encoding='utf-8') as f:
            for i, record in enumerate(doc.records):
                for fname, fval in record.fields.items():
                    val_str = str(fval.value)
                    for name in doctor_names:
                        if name in val_str:
                            f.write(f'Record {i}: Field {fname}: {val_str}\n')
        
        print('Done - check debug_fields.txt and debug_doctor_fields.txt')
        break