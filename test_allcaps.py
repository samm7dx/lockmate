import sys
sys.path.insert(0, '.')

from pathlib import Path
from secret_wards.intake.pipeline import IntakePipeline
from secret_wards.detection.names import detect_names
from secret_wards.detection.normalize import apply_normalization

intake = IntakePipeline(Path('.artifacts/toolkit/phase4-output-reg'))
docs, quarantine = intake.process_directory(Path('C:/Users/samri/Secret-Wards-ToolKit/dev/input/registration'))

for doc in docs:
    if '2d11b4b60e5d2aaa' in doc.source_file.sha256:
        print(f'Found CSV doc: {doc.source_file.sha256[:16]}')
        print(f'Records: {len(doc.records)}')
        
        # Check records with ALL CAPS names (indices 3, 9, 13, 26)
        for idx in [3, 9, 13, 26]:
            if idx < len(doc.records):
                rec = doc.records[idx]
                print(f'\n=== Record {idx} ===')
                print(f'Record ID: {rec.record_id}')
                
                # Apply normalization
                normalized_text, offset_map = apply_normalization(rec)
                rec.normalized_text = normalized_text
                rec.offset_map = offset_map
                print(f'Normalized text (first 300): {normalized_text[:300]}')
                
                # Run name detection
                name_spans = detect_names(rec)
                print(f'Name spans: {len(name_spans)}')
                for s in name_spans:
                    print(f'  Name: "{s.original_text}" at {s.start}-{s.end} (conf: {s.confidence}, detector: {s.detector})')
        
        break