# Shared Interfaces

This document defines the interfaces between the Ingestion module (Developer 2 - Satwilk) and the Detection, Linkage, and Privacy modules (Developer 1 - Samridh).

## 1. Ingestion → Detection/Linkage/Privacy

The Ingestion module provides standardized records for downstream processing.

### Data Model: `IngestedRecord`

```python
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID, uuid4

class IngestedRecord(BaseModel):
    """Standardized record produced by the ingestion module."""
    record_id: UUID = Field(default_factory=uuid4)
    source_file: str  # Original filename or path
    format: str       # csv, json, fhir, text
    row_number: int | None = None  # Row/Line number in source file
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Raw parsed data
    data: dict[str, Any]
    
    # Metadata about the ingestion
    metadata: dict[str, Any] = Field(default_factory=dict)
```

### Data Model: `IngestedBatch`

```python
class IngestedBatch(BaseModel):
    """Batch of records produced by a single ingestion task."""
    batch_id: UUID = Field(default_factory=uuid4)
    records: list[IngestedRecord]
    stats: dict[str, Any]
```

## 2. Detection → Ingestion (for Report/Records Generation)

The Detection module adds labels/findings to the records.

### Data Model: `DetectionFinding`

```python
class DetectionFinding(BaseModel):
    """PII/PHI finding from the detection module."""
    field: str
    label: str           # PII_NAME, PII_SSN, PHI_DIAGNOSIS, etc.
    score: float         # 0.0 to 1.0 confidence score
    offset: int | None = None
    length: int | None = None
```

### Data Model: `DetectedRecord`

```python
class DetectedRecord(IngestedRecord):
    """Record with detection findings."""
    findings: list[DetectionFinding] = []
    is_sensitive: bool = False
```

## 3. Linkage → Ingestion (for Report/Records Generation)

The Linkage module identifies duplicates or linked records.

### Data Model: `LinkageResult`

```python
class LinkageResult(BaseModel):
    """Linkage result for a record."""
    canonical_id: UUID
    confidence: float
    is_duplicate: bool
```

### Data Model: `LinkedRecord`

```class LinkedRecord(DetectedRecord):
    """Record with linkage results."""
    linkage: LinkageResult | None = None
```

## 4. Privacy → Ingestion (for Sanitized Serialization)

The Privacy module provides the sanitized version of the data.

### Data Model: `PrivacyAction`

```python
class PrivacyAction(str, Enum):
    REDACT = "redact"
    MASK = "mask"
    HASH = "hash"
    PSEUDONYMIZE = "pseudonymize"
    NONE = "none"

class PrivacyResult(BaseModel):
    """Sanitization results for a record."""
    action_taken: dict[str, PrivacyAction]
    original_data_hash: str
```

### Data Model: `SanitizedRecord`

```python
class SanitizedRecord(LinkedRecord):
    """Final sanitized record ready for serialization."""
    sanitized_data: dict[str, Any]
    privacy: PrivacyResult
```

## 5. Summary Statistics

Both modules contribute to the final report.

### Ingestion Stats

```python
{
    "total_files": 10,
    "total_records": 1000,
    "total_size_bytes": 1048576,
    "formats": {"csv": 5, "json": 5},
    "errors": [],
    "quarantined_files": 0
}
```

### Detection Stats

```python
{
    "sensitive_records": 100,
    "total_findings": 250,
    "label_counts": {"PII_NAME": 100, "PHI_DIAGNOSIS": 50}
}
```

## 6. Output Generation (`report.json` and `records.jsonl`)

The Ingestion module is responsible for the final output generation using data collected from all modules.

### `report.json` Structure

```json
{
    "job_id": "uuid",
    "timestamp": "iso8601",
    "ingestion_stats": {...},
    "detection_stats": {...},
    "linkage_stats": {...},
    "privacy_stats": {...},
    "errors": [...]
}
```

### `records.jsonl` Structure

Each line is a JSON object containing the `SanitizedRecord` data.

```json
{"record_id": "...", "source_file": "...", "data": {...}, "findings": [...], "linkage": {...}, "privacy": {...}}
```