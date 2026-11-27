import sys
sys.path.insert(0, '.')

from pathlib import Path
from secret_wards.output.security_gate import scan_output_directory

result = scan_output_directory(Path('.artifacts/toolkit/phase4-output-final'))
print(f'Clean: {result[0]}')
print(f'Spans: {len(result[1])}')
for s in result[1][:20]:
    print(f'  {s.pii_type}: "{s.original_text}" at {s.start}-{s.end} (detector: {s.detector})')
    print(f'  Context: {s.context[:100]}')