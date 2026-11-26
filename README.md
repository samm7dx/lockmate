# LOCKMATE

Secure data ingestion and processing pipeline for healthcare data.

## Architecture Overview

```
lockmate/
├── src/
│   ├── ingestion/           # Developer 2 (Satwilk) - File ingestion & parsing
│   │   ├── secure_ingest.py     # Secure file ingestion with validation
│   │   ├── parsers/
│   │   │   ├── __init__.py
│   │   │   ├── csv_parser.py    # CSV/TSV parsing
│   │   │   ├── json_parser.py   # JSON/nested JSON parsing
│   │   │   ├── text_parser.py   # Plain-text parsing
│   │   │   └── fhir_parser.py   # FHIR R4 ingestion support
│   │   ├── validation/
│   │   │   ├── __init__.py
│   │   │   ├── file_validator.py    # File validation & encoding checks
│   │   │   ├── path_guard.py        # Path traversal protection
│   │   │   ├── symlink_guard.py     # Symlink security
│   │   │   ├── size_limits.py       # File-size & resource limits
│   │   │   └── quarantine.py        # Malformed-file quarantine
│   │   ├── output/
│   │   │   ├── __init__.py
│   │   │   ├── serializer.py        # Sanitized output serialization
│   │   │   ├── atomic_write.py      # Safe output filenames & atomic writes
│   │   │   ├── report_generator.py  # report.json generation
│   │   │   └── records_generator.py # records.jsonl generation
│   │   └── tests/
│   │       ├── test_csv_parser.py
│   │       ├── test_json_parser.py
│   │       ├── test_text_parser.py
│   │       ├── test_fhir_parser.py
│   │       ├── test_file_validator.py
│   │       ├── test_path_guard.py
#   │       ├── test_symlink_guard.py
#   │       ├── test_size_limits.py
#   │       ├── test_quarantine.py
#   │       ├── test_serializer.py
#   │       ├── test_atomic_write.py
#   │       ├── test_report_generator.py
#   │       └── test_records_generator.py
│   ├── detection/           # Developer 1 (Samridh) - Data detection
│   ├── linkage/             # Developer 1 (Samridh) - Record linkage
│   └── privacy/             # Developer 1 (Samridh) - Privacy/De-identification
├── tests/
│   ├── integration/
│   └── fixtures/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── INTERFACES.md
│   └── SECURITY.md
├── pyproject.toml
├── pytest.ini
└── .gitignore
```

## Developer Responsibilities

### Developer 1 (Samridh) - Main Developer
- Data detection module
- Record linkage module
- Privacy/de-identification module

### Developer 2 (Satwilk) - Ingestion & Parsing
- Secure file ingestion
- CSV/TSV parsing
- JSON/nested JSON parsing
- Plain-text parsing
- FHIR R4 ingestion support
- File validation & encoding checks
- Path traversal protection
- Symlink security
- File-size & resource limits
- Malformed-file quarantine
- Sanitized output serialization
- Safe output filenames & atomic writes
- `report.json` generation
- `records.jsonl` generation
- Unit tests for all ingestion modules

## Shared Interfaces

Defined in `docs/INTERFACES.md` - coordinate before implementing.

## Security

See `docs/SECURITY.md` for security requirements including:
- Path traversal protection
- Symlink resolution safety
- Resource limits (file size, memory, processing time)
- Input validation and sanitization
- Quarantine for malformed/suspicious files
- Atomic writes to prevent partial outputs

## Development Rules

1. Work on `agent/satwilk` branch
2. Do not push to main
3. Do not modify Samridh's modules (detection, linkage, privacy)
4. Use synthetic test data only
5. Run tests and report actual results
6. Coordinate shared interfaces before implementation

## Getting Started

```bash
pip install -e ".[dev]"
pytest
```