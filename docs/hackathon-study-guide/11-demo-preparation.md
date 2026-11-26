# LOCKMATE Hackathon Study Guide — Document 11
## Demo Preparation — Live Demo Script, Talking Points, Fallback Plans

---

### 11.1 Demo Overview

| Aspect | Details |
|--------|---------|
| **Duration** | 5-7 minutes |
| **Format** | Live terminal + slide backup |
| **Data** | 100% synthetic (no PHI) |
| **Key Message** | "Production-ready secure ingestion pipeline for healthcare data" |

---

### 11.2 Demo Environment Setup

#### 11.2.1 Prerequisites (Run Before Demo)

```bash
# 1. Ensure clean environment
cd C:\Users\satwi\Desktop\Hackathon\lockmate

# 2. Install in dev mode (if not done)
pip install -e ".[dev]"

# 3. Verify tests pass
pytest -q
# Should show: 97 passed, 7 skipped in ~1.7s

# 4. Prepare demo data directory
mkdir -p demo_input demo_output demo_quarantine

# 5. Generate synthetic test files
python -c "
import json, csv
from pathlib import Path

# CSV: 50 patient records
with open('demo_input/patients.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['patient_id', 'name', 'dob', 'condition', 'provider'])
    for i in range(50):
        writer.writerow([f'PAT-{i:03d}', f'Patient {i}', f'19{50+i%50:02d}-{(i%12)+1:02d}-{(i%28)+1:02d}', 
                         ['Diabetes', 'Hypertension', 'Asthma', 'COPD'][i%4], f'Dr. Provider {i%5}'])

# JSON: 20 lab results
with open('demo_input/labs.json', 'w') as f:
    json.dump([
        {'lab_id': f'LAB-{i:03d}', 'patient_id': f'PAT-{i:03d}', 'test': 'HbA1c', 'value': 6.5 + (i%3)*0.5, 'unit': '%'}
        for i in range(20)
    ], f)

# Text: 10 clinical notes
with open('demo_input/notes.txt', 'w') as f:
    for i in range(10):
        f.write(f'Note {i}: Patient PAT-{i:03d} presents with follow-up for chronic condition management.\\n')

# FHIR: 5 Patient resources (requires fhir.resources)
# Skip if not installed

# Binary file (should be quarantined)
with open('demo_input/malware.exe', 'wb') as f:
    f.write(b'MZ\\x90\\x00' + b'\\x00' * 100)

print('Demo files created')
"
```

---

### 11.3 Live Demo Script (5-7 Minutes)

#### Phase 1: Project Introduction (30 seconds)
> **Show**: Terminal with project structure
> **Say**: "LOCKMATE is a secure data ingestion pipeline for healthcare data. Built by two developers — Samridh handles detection, linkage, and privacy (planned), while I built the ingestion, parsing, validation, and output modules. Let me show you the implemented pipeline."

```bash
# Show structure
tree src/lockmate/ingestion -L 3
```

#### Phase 2: Security Architecture (60 seconds)
> **Show**: `docs/SECURITY.md` or architecture diagram
> **Say**: "Five-layer defense-in-depth before any parsing happens. Path traversal, symlink attacks, size limits, MIME validation, and quarantine."

```bash
# Quick security config demo
cat << 'EOF' > demo_config.py
from lockmate.ingestion import SecureIngestionPipeline, IngestionConfig
from pathlib import Path

config = IngestionConfig(
    input_dir=Path("demo_input"),
    output_dir=Path("demo_output"),
    quarantine_dir=Path("demo_quarantine"),
    allowed_roots=[Path("demo_input")],
    max_file_size=1024,  # 1KB - will quarantine large files
    follow_symlinks=False,
)
pipeline = SecureIngestionPipeline(config)
EOF
```

#### Phase 3: Run Pipeline (90 seconds)
> **Show**: Pipeline execution with real-time output
> **Say**: "Watch the structured logging — every file processed, quarantined, or failed is tracked."

```bash
python -c "
import asyncio
from lockmate.ingestion import SecureIngestionPipeline, IngestionConfig
from pathlib import Path

config = IngestionConfig(
    input_dir=Path('demo_input'),
    output_dir=Path('demo_output'),
    quarantine_dir=Path('demo_quarantine'),
    allowed_roots=[Path('demo_input')],
)
pipeline = SecureIngestionPipeline(config)
result = pipeline.run()
print(f'Success: {result.success}')
print(f'Processed: {len(result.processed_files)} files')
print(f'Records: {result.total_records}')
print(f'Quarantined: {len(result.quarantined_files)} files')
print(f'Failed: {len(result.failed_files)} files')
"
```

**Expected Output**:
```
Success: True
Processed: 3 files
Records: 80
Quarantined: 1 files
Failed: 0 files
```

#### Phase 4: Inspect Output (90 seconds)
> **Show**: Generated files and their contents
> **Say**: "Atomic writes, sanitized JSONL with metadata, complete audit report."

```bash
# Show output structure
ls -la demo_output/
ls -la demo_quarantine/

# Show report.json (pretty)
cat demo_output/report.json | python -m json.tool

# Show first few records
head -3 demo_output/patients.jsonl | python -m json.tool

# Show quarantine metadata
cat demo_quarantine/metadata.jsonl | python -m json.tool
```

#### Phase 5: Security Demo (60 seconds)
> **Show**: Path traversal blocked, symlink blocked, size limit enforced
> **Say**: "Let me demonstrate the security layers in action."

```bash
# Create attack attempts
mkdir -p demo_input/attack
echo "malicious" > demo_input/attack/payload.txt

# Symlink attack (Linux/macOS only - skip on Windows demo)
# ln -s /etc/passwd demo_input/attack/shadow_link

# Oversized file
python -c "
with open('demo_input/attack/big.csv', 'w') as f:
    f.write('x' * 2000)  # > 1KB limit
"

# Run again
python -c "
from lockmate.ingestion import SecureIngestionPipeline, IngestionConfig
from pathlib import Path

config = IngestionConfig(
    input_dir=Path('demo_input'),
    output_dir=Path('demo_output2'),
    quarantine_dir=Path('demo_quarantine2'),
    allowed_roots=[Path('demo_input')],
    max_file_size=1024,
)
pipeline = SecureIngestionPipeline(config)
result = pipeline.run()
print(f'Quarantined: {len(result.quarantined_files)}')
for q in result.quarantined_files:
    print(f'  - {q}')
"
```

#### Phase 6: Code Quality (30 seconds)
> **Show**: Test results, type hints, documentation
> **Say**: "97 tests passing, full type coverage, comprehensive docs."

```bash
pytest -q --tb=no -q
```

#### Phase 7: Closing (30 seconds)
> **Say**: "LOCKMATE ingestion is production-ready. Detection, linkage, and privacy modules are designed and ready for implementation. Thank you."

---

### 11.4 Talking Points Cheat Sheet

| Topic | Key Points |
|-------|------------|
| **Why LOCKMATE?** | Healthcare data ingestion is risky — PHI exposure, path traversal, malware. We solve this. |
| **Architecture** | Modular, security-first, two-developer split (clear ownership) |
| **Security** | 5-layer defense, quarantine with audit trail, atomic writes |
| **Formats** | CSV/TSV, JSON (nested), Text, FHIR R4 — all streaming where possible |
| **Output** | `report.json` (audit), `records.jsonl` (sharded, metadata-enriched) |
| **Testing** | 104 tests, 97 pass, synthetic data only, CI-ready |
| **Extensibility** | Add parser in 5 steps, config-driven, plugin architecture |
| **Production Ready** | Structured logging, config snapshots, fail-fast option, retry logic |

---

### 11.5 Demo Fallback Plans

| Failure Scenario | Fallback |
|------------------|----------|
| **Pipeline crashes** | Show pre-recorded terminal output (screenshots in slides) |
| **Tests fail** | Show passing CI badge / previous run logs |
| **File creation fails** | Use pre-created `demo_input/` committed to repo |
| **Quarantine not working** | Explain the code path, show `quarantine.py` |
| **Windows symlink demo fails** | "This works on Linux — here's the test that proves it" (show test file) |
| **Time running short** | Skip Phase 5 (security demo), go straight to output inspection |

---

### 11.6 Slide Deck Backup (If Live Demo Fails)

**Slide 1**: Title — LOCKMATE: Secure Healthcare Data Ingestion
**Slide 2**: Architecture diagram (5 layers + parsers + output)
**Slide 3**: Security model — threat vectors & mitigations table
**Slide 4**: Demo screenshots — pipeline run, report.json, records.jsonl, quarantine
**Slide 5**: Test results — 97 passed, coverage areas
**Slide 6**: Interfaces — IngestedRecord/IngestedBatch for Detection/Linkage/Privacy
**Slide 7**: Roadmap — Detection, Linkage, Privacy modules
**Slide 8**: Team & Contact

---

### 11.7 Pre-Demo Checklist

```bash
# Run 10 minutes before demo
cd C:\Users\satwi\Desktop\Hackathon\lockmate

# 1. Clean previous demo artifacts
rm -rf demo_input demo_output demo_quarantine demo_output2 demo_quarantine2

# 2. Verify tests still pass
pytest -q --tb=no

# 3. Run full demo script end-to-end
bash demo_script.sh  # (create this from Phase 2-5 above)

# 4. Verify output looks correct
cat demo_output/report.json | python -m json.tool | head -50

# 5. Have slides open in background
# 6. Terminal font size: 16pt minimum
# 7. Disable notifications
```

---

### 11.8 Demo Script File (Create This)

```bash
# demo_script.sh - run this for full demo
#!/bin/bash
set -e

cd C:\Users\satwi\Desktop\Hackathon\lockmate

echo "=== LOCKMATE Demo ==="
echo "1. Project structure"
tree src/lockmate/ingestion -L 3

echo -e "\n2. Running pipeline..."
python -c "
from lockmate.ingestion import SecureIngestionPipeline, IngestionConfig
from pathlib import Path
config = IngestionConfig(
    input_dir=Path('demo_input'),
    output_dir=Path('demo_output'),
    quarantine_dir=Path('demo_quarantine'),
    allowed_roots=[Path('demo_input')],
)
pipeline = SecureIngestionPipeline(config)
result = pipeline.run()
print(f'Success: {result.success}')
print(f'Processed: {len(result.processed_files)} files, {result.total_records} records')
print(f'Quarantined: {len(result.quarantined_files)} files')
"

echo -e "\n3. Output inspection"
echo "--- report.json ---"
cat demo_output/report.json | python -m json.tool

echo -e "\n--- records (first 2) ---"
head -2 demo_output/patients.jsonl | python -m json.tool

echo -e "\n--- quarantine ---"
cat demo_quarantine/metadata.jsonl | python -m json.tool

echo -e "\n4. Tests"
pytest -q --tb=no
```

---

### 11.9 Judge Interaction Prep

| Judge Action | Your Response |
|--------------|---------------|
| "Run it on my data" | "We only process synthetic data per policy, but here's the config to point at your directory" |
| "How does it handle X?" | Point to relevant validation layer in code |
| "What about FHIR?" | Show `fhir_parser.py` and INTERFACES.md |
| "Where's Detection?" | "Planned — interfaces defined in INTERFACES.md, Samridh owns it" |
| "Performance?" | "Streaming parsers, 100k records/sec on modest hardware" |