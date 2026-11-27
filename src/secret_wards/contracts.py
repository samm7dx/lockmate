"""
LOCKMATE — Shared Data Contracts

This module defines the 12 frozen dataclasses that serve as the single
integration contract between all LOCKMATE pipeline components.

All agents MUST implement these interfaces exactly. No breaking changes
after Phase 1 without Orchestrator approval.

Version: 1.0
Source: context.md §21
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4


# =============================================================================
# ENUMS
# =============================================================================

class FormatType(Enum):
    """Supported input file formats."""
    CSV = "csv"
    TSV = "tsv"
    JSON = "json"
    TEXT = "text"
    FHIR = "fhir"
    UNKNOWN = "unknown"


class RecordStatus(Enum):
    """Processing status of a record."""
    PENDING = "pending"
    PROCESSED = "processed"
    QUARANTINED = "quarantined"


class FieldType(Enum):
    """Field value types."""
    STRING = "string"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"


class PIIType(Enum):
    """Types of personally identifiable information."""
    NAME = "name"
    PHONE = "phone"
    AADHAAR = "aadhaar"
    ABHA = "abha"
    PAN = "pan"
    EMAIL = "email"
    ADDRESS = "address"
    DATE = "date"
    UHID = "uhid"
    RELATIVE = "relative"
    DOCTOR = "doctor"
    URL = "url"
    PIN = "pin"
    INSURANCE = "insurance"
    OTHER = "other"


class MedicalType(Enum):
    """Types of clinical/medical information that must be preserved."""
    DRUG = "drug"
    DOSAGE = "dosage"
    FREQUENCY = "frequency"
    DURATION = "duration"
    DIAGNOSIS = "diagnosis"
    PROCEDURE = "procedure"
    LAB = "lab"
    VITAL = "vital"
    UNIT = "unit"
    DOCTOR = "doctor"
    ICD_CODE = "icd_code"
    ROUTE = "route"


class QuarantineReason(Enum):
    """Reasons for quarantining a file or record."""
    UNSUPPORTED_FORMAT = "unsupported_format"
    ENCODING_DETECTION_FAILED = "encoding_detection_failed"
    PARSE_ERROR = "parse_error"
    RESOURCE_LIMIT_EXCEEDED = "resource_limit_exceeded"
    RESIDUAL_PII = "residual_pii"
    OUTPUT_GATE_FAILED = "output_gate_failed"
    UNCERTAIN_IDENTITY = "uncertain_identity"
    PATH_TRAVERSAL = "path_traversal"
    DECOMPRESSION_BOMB = "decompression_bomb"
    MALFORMED_FHIR = "malformed_fhir"
    BINARY_ATTACHMENT = "binary_attachment"


class RecordLocationType(Enum):
    """Type of record location reference."""
    ROW = "row"
    JSON_POINTER = "json_pointer"
    DOC = "doc"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass(frozen=True)
class InputFile:
    """
    Represents a discovered input file with its metadata.
    
    Immutable — file identity is established at discovery time.
    """
    path: Path
    sha256: str
    size_bytes: int
    format: FormatType
    encoding: str
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "path": str(self.path),
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "format": self.format.value,
            "encoding": self.encoding,
            "discovered_at": self.discovered_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InputFile":
        """Deserialize from dictionary."""
        return cls(
            path=Path(data["path"]),
            sha256=data["sha256"],
            size_bytes=data["size_bytes"],
            format=FormatType(data["format"]),
            encoding=data["encoding"],
            discovered_at=datetime.fromisoformat(data["discovered_at"])
        )


@dataclass
class ParsedDocument:
    """
    A parsed document containing multiple logical records.
    
    Preserves format-specific information for lossless serialization.
    """
    source_file: InputFile
    records: List["UnifiedRecord"]
    format_specific: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_file": self.source_file.to_dict(),
            "records": [r.to_dict() for r in self.records],
            "format_specific": self.format_specific
        }


@dataclass
class RecordLocation:
    """
    Location of a record within its source document.
    
    Format-specific location reference for traceability.
    """
    location_type: RecordLocationType
    value: str  # e.g., "row:0", "/visits/3", "doc"
    
    def __str__(self) -> str:
        return f"{self.location_type.value}:{self.value}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "location_type": self.location_type.value,
            "value": self.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecordLocation":
        return cls(
            location_type=RecordLocationType(data["location_type"]),
            value=data["value"]
        )
    
    @classmethod
    def from_row(cls, row: int) -> "RecordLocation":
        return cls(RecordLocationType.ROW, f"row:{row}")
    
    @classmethod
    def from_json_pointer(cls, pointer: str) -> "RecordLocation":
        return cls(RecordLocationType.JSON_POINTER, pointer)
    
    @classmethod
    def from_doc(cls) -> "RecordLocation":
        return cls(RecordLocationType.DOC, "doc")


@dataclass
class FieldValue:
    """
    A field value with its metadata.
    
    Preserves both the raw value and structural context.
    """
    value: Any
    field_type: FieldType
    path: str
    is_identifier_field: bool = False
    original_text: Optional[str] = None  # For text fields
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "field_type": self.field_type.value,
            "path": self.path,
            "is_identifier_field": self.is_identifier_field,
            "original_text": self.original_text
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FieldValue":
        return cls(
            value=data["value"],
            field_type=FieldType(data["field_type"]),
            path=data["path"],
            is_identifier_field=data.get("is_identifier_field", False),
            original_text=data.get("original_text")
        )


@dataclass
class UnifiedRecord:
    """
    Unified Record Model (URM) — the core internal representation.
    
    All parsers emit this model. Preserves enough structural information
    to serialize back to the original format.
    """
    record_id: str  # Stable: f"{file_sha256}:{loc}"
    location: RecordLocation
    fields: Dict[str, FieldValue]
    raw_text: str  # Full text for unstructured/content search
    normalized_text: str  # Post-normalization text
    offset_map: List[Tuple[int, int]]  # (norm_start, norm_end) -> (orig_start, orig_end)
    status: RecordStatus = RecordStatus.PENDING
    pii_spans: List["PIISpan"] = field(default_factory=list)
    medical_spans: List["MedicalSpan"] = field(default_factory=list)
    privacy_transformations: Optional["PrivacyTransformation"] = None
    pseudonym: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "location": self.location.to_dict(),
            "fields": {k: v.to_dict() for k, v in self.fields.items()},
            "raw_text": self.raw_text,
            "normalized_text": self.normalized_text,
            "offset_map": self.offset_map,
            "status": self.status.value,
            "pii_spans": [s.to_dict() for s in self.pii_spans],
            "medical_spans": [s.to_dict() for s in self.medical_spans],
            "privacy_transformations": self.privacy_transformations.to_dict() if self.privacy_transformations else None,
            "pseudonym": self.pseudonym,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UnifiedRecord":
        return cls(
            record_id=data["record_id"],
            location=RecordLocation.from_dict(data["location"]),
            fields={k: FieldValue.from_dict(v) for k, v in data["fields"].items()},
            raw_text=data["raw_text"],
            normalized_text=data["normalized_text"],
            offset_map=data["offset_map"],
            status=RecordStatus(data["status"]),
            pii_spans=[PIISpan.from_dict(s) for s in data.get("pii_spans", [])],
            medical_spans=[MedicalSpan.from_dict(s) for s in data.get("medical_spans", [])],
            privacy_transformations=PrivacyTransformation.from_dict(data["privacy_transformations"]) if data.get("privacy_transformations") else None,
            pseudonym=data.get("pseudonym"),
            metadata=data.get("metadata", {})
        )


@dataclass
class PIISpan:
    """
    A detected PII span in normalized text.
    
    All offsets are in the normalized_text coordinate space.
    Use offset_map to map back to original text.
    """
    start: int  # Offset in normalized_text
    end: int    # Offset in normalized_text
    pii_type: PIIType
    confidence: float  # 0.0 - 1.0
    original_text: str  # The actual text span from original
    context: str  # Surrounding 50 chars for context
    detector: str  # Which detector fired
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "pii_type": self.pii_type.value,
            "confidence": self.confidence,
            "original_text": self.original_text,
            "context": self.context,
            "detector": self.detector
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PIISpan":
        return cls(
            start=data["start"],
            end=data["end"],
            pii_type=PIIType(data["pii_type"]),
            confidence=data["confidence"],
            original_text=data["original_text"],
            context=data["context"],
            detector=data["detector"]
        )
    
    def overlaps(self, other: "PIISpan") -> bool:
        """Check if this span overlaps with another."""
        return not (self.end <= other.start or other.end <= self.start)
    
    def contains(self, other: "PIISpan") -> bool:
        """Check if this span fully contains another."""
        return self.start <= other.start and other.end <= self.end


@dataclass
class MedicalSpan:
    """
    A detected medical/clinical span that must be preserved.
    
    All offsets in normalized_text coordinate space.
    """
    start: int
    end: int
    medical_type: MedicalType
    confidence: float
    original_text: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "medical_type": self.medical_type.value,
            "confidence": self.confidence,
            "original_text": self.original_text
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MedicalSpan":
        return cls(
            start=data["start"],
            end=data["end"],
            medical_type=MedicalType(data["medical_type"]),
            confidence=data["confidence"],
            original_text=data["original_text"]
        )
    
    def overlaps(self, other: "MedicalSpan") -> bool:
        return not (self.end <= other.start or other.end <= self.start)


@dataclass
class IdentityCandidate:
    """
    A candidate pair of records that may represent the same patient.
    """
    record_a: UnifiedRecord
    record_b: UnifiedRecord
    blocking_keys: List[str]
    scores: Dict[str, float] = field(default_factory=dict)
    total_score: float = 0.0
    cannot_link: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_a_id": self.record_a.record_id,
            "record_b_id": self.record_b.record_id,
            "blocking_keys": self.blocking_keys,
            "scores": self.scores,
            "total_score": self.total_score,
            "cannot_link": self.cannot_link
        }


@dataclass
class PatientCluster:
    """
    A cluster of records representing the same patient.
    
    Formed by conservative clustering of identity candidates.
    """
    cluster_id: str
    records: List[UnifiedRecord]
    canonical_identity: str = ""  # For pseudonym derivation
    pseudonym: Optional[str] = None  # PSN-XXXX or None
    is_confident: bool = True  # False -> pseudonym = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "record_ids": [r.record_id for r in self.records],
            "canonical_identity": self.canonical_identity,
            "pseudonym": self.pseudonym,
            "is_confident": self.is_confident
        }
    
    def add_record(self, record: UnifiedRecord) -> None:
        """Add a record to this cluster."""
        self.records.append(record)


@dataclass
class PrivacyTransformation:
    """
    Privacy transformations applied to a record.
    
    Tracks all quasi-identifier modifications for audit.
    """
    record: UnifiedRecord
    date_shifts: Dict[str, int] = field(default_factory=dict)  # field_path -> days_offset
    age_band: Optional[str] = None
    location_generalization: Dict[str, str] = field(default_factory=dict)  # field_path -> generalized_value
    suppressions: List[str] = field(default_factory=list)  # field_paths suppressed
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record.record_id,
            "date_shifts": self.date_shifts,
            "age_band": self.age_band,
            "location_generalization": self.location_generalization,
            "suppressions": self.suppressions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], record: UnifiedRecord) -> "PrivacyTransformation":
        return cls(
            record=record,
            date_shifts=data.get("date_shifts", {}),
            age_band=data.get("age_band"),
            location_generalization=data.get("location_generalization", {}),
            suppressions=data.get("suppressions", [])
        )


@dataclass
class SanitizedRecord:
    """
    A record after all sanitization transformations.
    
    Ready for serialization to output format.
    """
    record: UnifiedRecord
    transformed_text: str  # After all replacements
    transformed_fields: Dict[str, Any] = field(default_factory=dict)  # For structured serialization
    pseudonym: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record.record_id,
            "transformed_text": self.transformed_text,
            "transformed_fields": self.transformed_fields,
            "pseudonym": self.pseudonym
        }


@dataclass
class QuarantineResult:
    """
    Result of quarantining a file or record.
    """
    input_file: InputFile
    reason: QuarantineReason
    output_path: Path  # In sanitized/quarantined/
    records_affected: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_file_sha256": self.input_file.sha256,
            "reason": self.reason.value,
            "output_path": str(self.output_path),
            "records_affected": self.records_affected,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details
        }


@dataclass
class ProcessingMetrics:
    """
    Processing metrics for a single file.
    
    Aggregated into report.json totals.
    """
    file_sha256: str
    duration_ms: int
    peak_memory_mb: int
    records_processed: int = 0
    identifiers_detected: int = 0
    records_linked: int = 0
    records_generalized: int = 0
    records_suppressed: int = 0
    records_quarantined: int = 0
    status: str = "processed"  # processed, quarantined, error
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_sha256": self.file_sha256,
            "duration_ms": self.duration_ms,
            "peak_memory_mb": self.peak_memory_mb,
            "records_processed": self.records_processed,
            "identifiers_detected": self.identifiers_detected,
            "records_linked": self.records_linked,
            "records_generalized": self.records_generalized,
            "records_suppressed": self.records_suppressed,
            "records_quarantined": self.records_quarantined,
            "status": self.status
        }


# =============================================================================
# REPORT STRUCTURES (for output/report.py)
# =============================================================================

@dataclass
class FileReportEntry:
    """Single file entry in report.json."""
    input_sha256: str
    output: Optional[str]
    status: str  # "sanitized" or "quarantined" or "suppressed"
    quarantine_reason: Optional[str] = None
    processing_duration_ms: int = 0
    peak_memory_mb: int = 0
    records_processed: int = 0
    identifiers_detected: int = 0
    records_linked: int = 0
    records_generalized: int = 0
    records_suppressed: int = 0
    records_quarantined: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        d = {
            "input_sha256": self.input_sha256,
            "output": self.output,
            "status": self.status,
            "processing_duration_ms": self.processing_duration_ms,
            "peak_memory_mb": self.peak_memory_mb,
            "records_processed": self.records_processed,
            "identifiers_detected": self.identifiers_detected,
            "records_linked": self.records_linked,
            "records_generalized": self.records_generalized,
            "records_suppressed": self.records_suppressed,
            "records_quarantined": self.records_quarantined
        }
        if self.quarantine_reason is not None:
            d["reason"] = self.quarantine_reason
        return d


@dataclass
class ReportTotals:
    """Aggregate totals for report.json."""
    files_total: int = 0
    files_sanitized: int = 0
    files_quarantined: int = 0
    records_processed: int = 0
    identifiers_detected: int = 0
    records_linked: int = 0
    records_generalized: int = 0
    records_suppressed: int = 0
    records_quarantined: int = 0
    total_processing_duration_ms: int = 0
    peak_memory_mb: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "files_total": self.files_total,
            "files_sanitized": self.files_sanitized,
            "files_quarantined": self.files_quarantined,
            "records_processed": self.records_processed,
            "identifiers_detected": self.identifiers_detected,
            "records_linked": self.records_linked,
            "records_generalized": self.records_generalized,
            "records_suppressed": self.records_suppressed,
            "records_quarantined": self.records_quarantined,
            "total_processing_duration_ms": self.total_processing_duration_ms,
            "peak_memory_mb": self.peak_memory_mb
        }


@dataclass
class ReportTiming:
    """Timing information for report.json."""
    seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {"seconds": self.seconds}


@dataclass
class ReportResources:
    """Resource usage for report.json."""
    peak_rss_mb: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {"peak_rss_mb": self.peak_rss_mb}


@dataclass
class FullReport:
    """Complete report.json structure."""
    schema: str = "raksha-report/1"
    files: List[FileReportEntry] = field(default_factory=list)
    counts: ReportTotals = field(default_factory=ReportTotals)
    timing: ReportTiming = field(default_factory=ReportTiming)
    resources: ReportResources = field(default_factory=ReportResources)
    entities: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": self.schema,
            "files": [f.to_dict() for f in self.files],
            "counts": self.counts.to_dict(),
            "timing": self.timing.to_dict(),
            "resources": self.resources.to_dict(),
            "entities": self.entities
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# =============================================================================
# RECORDS.JSONL ENTRY
# =============================================================================

@dataclass
class RecordsEntry:
    """Single line in records.jsonl."""
    file: str  # Relative path from output/sanitized/
    loc: str   # Location: row:N, JSON pointer, or doc
    patient: Optional[str]  # PSN-XXXX or null
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file,
            "loc": self.loc,
            "patient": self.patient
        }
    
    def to_jsonl(self) -> str:
        return json.dumps(self.to_dict(), separators=(',', ':'))


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file (streaming for large files)."""
    sha256 = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def generate_pseudonym_format(canonical_identity: str, secret: bytes) -> str:
    """
    Generate pseudonym in PSN-XXXXXXXX format.
    
    Uses HMAC-SHA256 with domain separation.
    """
    from cryptography.hazmat.primitives import hmac, hashes
    
    h = hmac.HMAC(secret, hashes.SHA256())
    h.update(b"pseudonym")
    h.update(canonical_identity.encode("utf-8"))
    digest = h.finalize()
    
    # Truncate to 16 bytes (128 bits), base32 encode
    truncated = digest[:16]
    b32 = base64.b32encode(truncated).decode("ascii").rstrip("=").lower()
    return f"PSN-{b32[:8]}"  # PSN-XXXXXXXX format


def derive_date_shift(patient_pseudonym: str, secret: bytes) -> int:
    """
    Derive per-patient date shift offset in days [-365, +365].
    
    Uses HMAC with domain separation.
    """
    from cryptography.hazmat.primitives import hmac, hashes
    
    h = hmac.HMAC(secret, hashes.SHA256())
    h.update(b"date_shift")
    h.update(patient_pseudonym.encode("utf-8"))
    digest = h.finalize()
    
    # Map to [-365, 365]
    offset = int.from_bytes(digest[:4], "big") % 731 - 365
    return offset


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Enums
    "FormatType",
    "RecordStatus",
    "FieldType",
    "PIIType",
    "MedicalType",
    "QuarantineReason",
    "RecordLocationType",
    # Data Classes
    "InputFile",
    "ParsedDocument",
    "RecordLocation",
    "FieldValue",
    "UnifiedRecord",
    "PIISpan",
    "MedicalSpan",
    "IdentityCandidate",
    "PatientCluster",
    "PrivacyTransformation",
    "SanitizedRecord",
    "QuarantineResult",
    "ProcessingMetrics",
    # Report Structures
    "FileReportEntry",
    "ReportTotals",
    "ReportTiming",
    "ReportResources",
    "FullReport",
    "RecordsEntry",
    # Utility Functions
    "compute_sha256",
    "generate_pseudonym_format",
    "derive_date_shift",
]