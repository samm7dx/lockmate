import sys
sys.path.insert(0, '.')
from secret_wards.intake.pipeline import IntakePipeline
from secret_wards.pipeline.full import _sanitize_document
from secret_wards.utils.metrics import ProcessingMetricsCollector
from pathlib import Path

intake = IntakePipeline(Path('C:/Users/samri/Secret-Wards-ToolKit/dev/input'))
docs, quarantine = intake.process_directory(Path('C:/Users/samri/Secret-Wards-ToolKit/dev/input'))

# Find a document with doctor names
for doc in docs:
    if doc.source_file.path.name == 'jeevanjyoti_patients.tsv':
        print(f'Found document: {doc.source_file.path.name}')
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
        
        all_text = ''
        for sr in sanitized:
            all_text += sr.transformed_text + '\n'
        
        # Check for doctor names
        for name in ['Dr. Vandana Kulshrestha', 'Dr. Ramesh Srivastava', 'Dr. Harjeet Bedi', 'Dr. Imtiaz Ahmed']:
            found = name in all_text
            print(f'{name}: {"FOUND" if found else "MISSING"}')
        break