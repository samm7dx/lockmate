# LOCKMATE Architecture

## Overview

LOCKMATE is a secure data ingestion and processing pipeline designed for healthcare data. It follows a modular architecture with clear separation of concerns between ingestion, detection, linkage, and privacy modules.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      LOCKMATE Pipeline                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  Ingestion   │───▶│  Detection   │───▶│  Linkage     │      │
│  │  (Satwilk)   │    │  (Samridh)   │    │  (Samridh)   │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                                       │                │
│         ▼                                       ▼                │
│  ┌──────────────┐                       ┌──────────────┐        │
│  │   Output     │                       │   Privacy    │        │
│  │  (Satwilk)   │                       │  (Samridh)   │        │
│  └──────────────┘                       └──────────────┘        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Ingestion Module (Developer 2 - Satwilk)

### Responsibilities

1. **Secure File Ingestion**
   - File validation and encoding detection
   - Path traversal protection
   - Symlink security
   - File-size and resource limits
   - Malformed-file quarantine

2. **Format Parsers**
   - CSV/TSV parsing with configurable delimiters
   - JSON and nested JSON parsing
   - Plain-text parsing with encoding handling
   - FHIR R4 resource parsing

3. **Output Generation**
   - Sanitized output serialization
   - Safe output filenames and atomic writes
   - `report.json` generation (metadata, stats, errors)
   - `records.jsonl` generation (processed records)

### Security Model

```
┌────────────────────────────────────────────────────────────┐
│                    Security Layers                          │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Layer 1: Path Guard                                       │
│  ├─ Resolve absolute paths                                 │
│  ├─ Validate against allowed roots                         │
│  ├─ Detect path traversal (../, ..\, etc.)                │
│  └─ Reject absolute paths outside sandbox                  │
│                                                             │
│  Layer 2: Symlink Guard                                    │
│  ├─ Detect symlinks                                        │
│  ├─ Resolve and validate targets                           │
│  ├─ Reject symlinks pointing outside sandbox               │
│  └─ Configurable: follow/block/warn                        │
│                                                             │
│  Layer 3: Size Limits                                      │
│  ├─ Max file size (default: 100MB)                         │
│  ├─ Max total ingestion size                               │
│  ├─ Max memory per parser                                  │
│  └─ Max processing time per file                           │
│                                                             │
│  Layer 4: File Validator                                   │
│  ├─ MIME type validation (python-magic)                    │
│  ├─ Encoding detection (charset-normalizer)                │
│  ├─ Structure validation per format                        │
│  └─ Malformed file quarantine                              │
│                                                             │
│  Layer 5: Quarantine                                       │
│  ├─ Isolate suspicious files                               │
│  ├─ Metadata logging                                       │
│  ├─ Configurable retention                                 │
│  └─ Audit trail                                            │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

## Data Flow

```
Input File
    │
    ▼
┌─────────────────┐
│  Path Guard     │──▶ Reject if path traversal detected
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Symlink Guard  │──▶ Reject/Quarantine if unsafe symlink
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Size Limits    │──▶ Reject if exceeds limits
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  File Validator │──▶ Quarantine if malformed
│  (MIME/Encoding)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Format Parser  │──▶ Parse based on detected format
│  (CSV/JSON/     │
│   Text/FHIR)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Output Serial- │──▶ Sanitize and serialize
│  izer           │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Atomic Writer  │──▶ Write atomically to final location
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Report Gen.    │──▶ Generate report.json
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Records Gen.   │──▶ Generate records.jsonl
└─────────────────┘
```

## Shared Interfaces

See `INTERFACES.md` for detailed interface specifications between modules.

### Ingestion → Detection

```python
# Ingestion produces standardized records for detection
{
    "record_id": "uuid",
    "source_file": "path",
    "row_number": 123,
    "data": {...},           # Parsed record data
    "metadata": {...}        # Parser-specific metadata
}
```

### Ingestion → Output

```python
# Output modules consume parsed records
records: Iterator[ParsedRecord]
config: OutputConfig
```

## Configuration

All modules use Pydantic v2 for configuration with environment variable support.

```python
class IngestionConfig(BaseModel):
    allowed_roots: list[Path] = [Path.cwd() / "data"]
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    max_total_size: int = 1024 * 1024 * 1024  # 1GB
    max_memory_per_parser: int = 512 * 1024 * 1024  # 512MB
    max_processing_time: int = 300  # seconds
    follow_symlinks: bool = False
    quarantine_enabled: bool = True
    quarantine_path: Path = Path.cwd() / "quarantine"
```

## Testing Strategy

- Unit tests for each parser and validator
- Property-based testing with Hypothesis for parsers
- Security-focused tests for path/symlink guards
- Integration tests for full pipeline
- Synthetic test data only (no real PHI)

## Error Handling

All modules use structured error types with error codes for programmatic handling:

```python
class IngestionError(Exception):
    code: str
    message: str
    details: dict
    recoverable: bool
```

## Logging

Structured logging with `structlog` for observability:

```python
logger = structlog.get_logger()
logger.info("ingestion.started", file=path, size=size)
logger.error("ingestion.failed", file=path, error=error.code)
```