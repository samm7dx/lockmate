# LOCKMATE - Secret Wards Track 3 Submission

**Team: CreativeMinds**

## Overview

LOCKMATE is an offline, CPU-only privacy firewall for Indian healthcare data (Secret Wards Track 3). It removes all personally identifiable information (PII) from heterogeneous hospital records while preserving medical utility and enabling cross-hospital patient linkage via stable pseudonyms.

## Features

- **Multilingual PII Detection**: English, Devanagari Hindi, and Hinglish with transliteration
- **Contextual Clinical Disambiguation**: Preserves medical terms (drugs, doses, diagnoses) while removing patient/relative names
- **Structured Field Sanitization**: JSON keys, CSV headers, FHIR metadata, filenames
- **Residual PII Security Gate**: Pre-write and post-write validation
- **Format Preservation**: CSV→CSV, JSON→JSON, FHIR R4→FHIR R4, Text→Text
- **Quarantine System**: Unsupported/malformed files safely isolated

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set secret (32+ bytes, base64 or hex)
export RAKSHA_SECRET="your-32-byte-secret-here"

# Run pipeline
python main.py --input /path/to/input --output /path/to/output
```

## Architecture

```
src/secret_wards/
├── intake/          # File discovery, validation, parsing (CSV/TSV/JSON/FHIR/Text)
├── detection/       # Multilingual PII detection (names, IDs, structured fields)
├── clinical/        # Clinical preservation (drugs, labs, diagnoses, doctors)
├── transform/       # Text replacement, structured field sanitization
├── output/          # Serialization, security gate, report generation
├── pipeline/        # Full pipeline orchestration
├── contracts.py     # Shared data contracts
└── utils/           # Logging, metrics, temp files
```

## Requirements

- Python 3.10+
- Dependencies in `requirements.txt`
- RAKSHA_SECRET environment variable (32+ bytes, base64/hex)

## Output Format

```
output/
├── sanitized/       # Sanitized files (same structure/formats)
├── quarantined/     # Unprocessable files
├── report.json      # Processing report
└── records.jsonl    # Patient linkage records
```

## Phase 4 Status

✅ Multilingual PII Detection (English/Devanagari/Hinglish)
✅ Contextual Clinical Disambiguation
✅ Structured Field Sanitization (JSON keys, CSV headers, FHIR meta)
✅ Residual PII Security Gate
✅ Format Preservation (CSV/JSON/FHIR/Text)
✅ Validator: CONTRACT OK
```

