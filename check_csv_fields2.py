import sys
sys.path.insert(0, '.')
from secret_wards.intake.pipeline import IntakePipeline
from pathlib import Path

intake = IntakePipeline(Path('C:/Users/samri/Secret-Wards-ToolKit/dev/input'))
docs, quarantine = intake.process_directory(Path('C:/Users/samri/Secret-Wards-ToolKit/dev/input'))

# Find the sanjeevani_registration.csv document
for doc in docs:
    if 'sanjeevani_registration' in doc.source_file.path.name and not '(1)' in doc.source_file.path.name:
        print('Document:', doc.source_file.path.name)
        print('Records:', len(doc.records))
        if doc.records:
            record = doc.records[0]
            print('Field names:')
            for fname in record.fields.keys():
                print(f'  {fname}')
        break