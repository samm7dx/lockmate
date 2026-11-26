"""
Adapter layer converting lockmate.ingestion parser output to secret_wards.contracts.

This module bridges the lockmate ingestion pipeline output (raw dicts from parsers)
to the shared contract types (UnifiedRecord, ParsedDocument, FullReport, RecordsEntry).
"""

from __future__ import annotations

import hashlib
import json
import base64
from pathlib import Path
from datetime import datetime
from typing import Any, Iterator, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum

# Import secret_wards contracts
try:
    from secret_wards.contracts import (
        FormatType,
        RecordStatus,
        FieldType,
        PIIType,
        MedicalType,
        QuarantineReason,
        RecordLocationType,
        InputFile,
        ParsedDocument,
        RecordLocation,
        FieldValue,
        UnifiedRecord,
        PIISpan,
        MedicalSpan,
        PrivacyTransformation,
        FileReportEntry,
        ReportTotals,
        ReportTiming,
        ReportResources,
        FullReport,
        RecordsEntry,
        compute_sha256,
    )
    CONTRACTS_AVAILABLE = True
except ImportError:
    CONTRACTS_AVAILABLE = False

from lockmate.ingestion.validation.file_validator import ValidationResult


# =============================================================================
# FALLBACK ENUMS/TYPES (when contracts not available)
# =============================================================================

if not CONTRACTS_AVAILABLE:
    # Define fallback enums matching secret_wards.contracts
    class FormatType(str, Enum):
        CSV = "csv"
        TSV = "tsv"
        JSON = "json"
        TEXT = "text"
        FHIR = "fhir"
        UNKNOWN = "unknown"
    
    class RecordStatus(str, Enum):
        PENDING = "pending"
        PROCESSED = "processed"
        QUARANTINED = "quarantined"
        FAILED = "failed"
    
    class FieldType(str, Enum):
        STRING = "string"
        NUMBER = "number"
        BOOLEAN = "boolean"
        DATE = "date"
        ARRAY = "array"
        OBJECT = "object"
    
    class PIIType(str, Enum):
        NAME = "name"
        EMAIL = "email"
        PHONE = "phone"
        ADDRESS = "address"
        SSN = "ssn"
        DOB = "dob"
        MRN = "mrn"
        ACCOUNT = "account"
        OTHER = "other"
    
    class MedicalType(str, Enum):
        DIAGNOSIS = "diagnosis"
        MEDICATION = "medication"
        PROCEDURE = "procedure"
        LAB_RESULT = "lab_result"
        VITAL_SIGN = "vital_sign"
        OTHER = "other"
    
    class QuarantineReason(str, Enum):
        INVALID_FORMAT = "invalid_format"
        ENCODING_ERROR = "encoding_error"
        SIZE_EXCEEDED = "size_exceeded"
        SYMLINK_DETECTED = "symlink_detected"
        PATH_TRAVERSAL = "path_traversal"
        PARSING_FAILED = "parsing_failed"
        PRIVACY_VIOLATION = "privacy_violation"
        OTHER = "other"
    
    class RecordLocationType(str, Enum):
        ROW = "row"
        JSON_POINTER = "json_pointer"
        DOC = "doc"
    
    # Minimal fallback dataclasses
    @dataclass
    class RecordLocation:
        type: RecordLocationType
        value: str
        
        @classmethod
        def from_row(cls, row: int) -> "RecordLocation":
            return cls(type=RecordLocationType.ROW, value=str(row))
        
        @classmethod
        def from_json_pointer(cls, pointer: str) -> "RecordLocation":
            return cls(type=RecordLocationType.JSON_POINTER, value=pointer)
        
        @classmethod
        def from_doc(cls) -> "RecordLocation":
            return cls(type=RecordLocationType.DOC, value="")
        
        def __str__(self) -> str:
            if self.type == RecordLocationType.ROW:
                return f"row:{self.value}"
            elif self.type == RecordLocationType.JSON_POINTER:
                return f"json:{self.value}"
            return "doc"
    
    @dataclass
    class FieldValue:
        value: Any
        field_type: FieldType
        path: str
        is_identifier_field: bool = False
        original_text: Optional[str] = None
    
    @dataclass
    class UnifiedRecord:
        record_id: str
        location: RecordLocation
        fields: dict[str, FieldValue]
        raw_text: str
        normalized_text: str
        offset_map: list[tuple[int, int]]
        status: RecordStatus = RecordStatus.PENDING
        pii_spans: list = field(default_factory=list)
        medical_spans: list = field(default_factory=list)
        privacy_transformations: Optional[Any] = None
        pseudonym: Optional[str] = None
        metadata: dict[str, Any] = field(default_factory=dict)
    
    @dataclass
    class InputFile:
        path: Path
        sha256: str
        size_bytes: int
        format: FormatType
        encoding: str
        discovered_at: datetime
    
    @dataclass
    class ParsedDocument:
        source_file: InputFile
        records: list[UnifiedRecord]
        format_specific: dict[str, Any] = field(default_factory=dict)
    
    @dataclass
    class FileReportEntry:
        input_sha256: str
        output_path: Optional[str] = None
        status: str = "sanitized"
        processing_duration_ms: int = 0
        peak_memory_mb: int = 0
        records_processed: int = 0
        identifiers_detected: int = 0
        records_linked: int = 0
        records_generalized: int = 0
        records_suppressed: int = 0
        records_quarantined: int = 0
        quarantine_reason: Optional[str] = None
    
    @dataclass
    class ReportTotals:
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
    
    @dataclass
    class ReportTiming:
        seconds: float
    
    @dataclass
    class ReportResources:
        peak_rss_mb: int
    
    @dataclass
    class FullReport:
        files: dict[str, FileReportEntry]
        counts: ReportTotals
        timing: ReportTiming
        resources: ReportResources
        
        def to_json(self) -> str:
            import orjson
            return orjson.dumps({
                "files": {k: v.__dict__ for k, v in self.files.items()},
                "counts": self.counts.__dict__,
                "timing": {"seconds": self.timing.seconds},
                "resources": {"peak_rss_mb": self.resources.peak_rss_mb},
            }).decode()
    
    @dataclass
    class RecordsEntry:
        file: str
        loc: str
        patient: Optional[str] = None
        
        def to_jsonl(self) -> str:
            import orjson
            return orjson.dumps({
                "file": self.file,
                "loc": self.loc,
                "patient": self.patient,
            }).decode()
    
    def compute_sha256(file_path: Path) -> str:
        sha256 = hashlib.sha256()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()


# For type hints when contracts are available
if TYPE_CHECKING and CONTRACTS_AVAILABLE:
    from secret_wards.contracts import (
        FormatType, RecordStatus, FieldType, PIIType, MedicalType,
        QuarantineReason, RecordLocationType, InputFile, ParsedDocument,
        RecordLocation, FieldValue, UnifiedRecord, PIISpan, MedicalSpan,
        PrivacyTransformation, FileReportEntry, ReportTotals, ReportTiming,
        ReportResources, FullReport, RecordsEntry
    )


# =============================================================================
# HELPER: MIME TYPE -> FORMAT TYPE MAPPING
# =============================================================================

_MIME_TO_FORMAT = {
    "text/csv": FormatType.CSV,
    "text/tab-separated-values": FormatType.TSV,
    "application/json": FormatType.JSON,
    "application/x-ndjson": FormatType.JSON,
    "text/plain": FormatType.TEXT,
    "application/fhir+json": FormatType.FHIR,
    "text/xml": FormatType.FHIR,  # Could be FHIR XML
    "application/xml": FormatType.FHIR,
}


def _mime_to_format(mime_type: str) -> FormatType:
    """Convert MIME type to FormatType enum."""
    return _MIME_TO_FORMAT.get(mime_type, FormatType.UNKNOWN)


def _infer_field_type(value: Any) -> FieldType:
    """Infer FieldType from a Python value."""
    if isinstance(value, bool):
        return FieldType.BOOLEAN
    elif isinstance(value, (int, float)):
        return FieldType.NUMBER
    elif isinstance(value, str):
        # Try to detect date-like strings
        if _looks_like_date(value):
            return FieldType.DATE
        return FieldType.STRING
    elif isinstance(value, (list, tuple)):
        return FieldType.ARRAY
    elif isinstance(value, dict):
        return FieldType.OBJECT
    else:
        return FieldType.STRING


def _looks_like_date(s: str) -> bool:
    """Heuristic to detect date-like strings."""
    import re
    date_patterns = [
        r"^\d{4}-\d{2}-\d{2}$",  # YYYY-MM-DD
        r"^\d{2}/\d{2}/\d{4}$",  # MM/DD/YYYY
        r"^\d{2}-\d{2}-\d{4}$",  # DD-MM-YYYY
        r"^\d{4}/\d{2}/\d{2}$",  # YYYY/MM/DD
    ]
    return any(re.match(p, s) for p in date_patterns)


def _build_record_id(file_sha256: str, location: RecordLocation) -> str:
    """Build stable record_id: f'{file_sha256}:{loc}'."""
    return f"{file_sha256}:{location}"


def _normalize_text(text: str) -> str:
    """Normalize text for consistent processing (NFKC)."""
    import unicodedata
    return unicodedata.normalize("NFKC", text)


def _build_offset_map(raw_text: str, normalized_text: str) -> list[tuple[int, int]]:
    """
    Build offset map from normalized to original text.
    For simplicity, we assume 1:1 mapping (common for NFKC normalization).
    A full implementation would use diff-match-patch or similar.
    """
    # Simple 1:1 mapping - each character maps to itself
    # In reality, NFKC can change character counts (e.g., full-width to half-width)
    min_len = min(len(raw_text), len(normalized_text))
    return [(i, i) for i in range(min_len)]


def _flatten_record(record: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Flatten nested dict structures (for JSON)."""
    result = {}
    for key, value in record.items():
        new_key = f"{prefix}{key}" if prefix else key
        if isinstance(value, dict):
            result.update(_flatten_record(value, f"{new_key}."))
        elif isinstance(value, list):
            # For lists, include as-is (will be serialized)
            result[new_key] = value
        else:
            result[new_key] = value
    return result


def _create_field_values(record: dict[str, Any], prefix: str = "") -> dict[str, FieldValue]:
    """Convert a flat dict to FieldValue dict."""
    field_values = {}
    for key, value in record.items():
        # Skip internal metadata fields
        if key.startswith("_"):
            continue
        
        field_path = f"{prefix}{key}" if prefix else key
        field_type = _infer_field_type(value)
        
        # Store original text representation for strings
        original_text = str(value) if isinstance(value, str) else None
        
        field_values[field_path] = FieldValue(
            value=value,
            field_type=field_type,
            path=field_path,
            is_identifier_field=False,  # Will be updated by detection layer
            original_text=original_text,
        )
    return field_values


def _build_raw_text(record: dict[str, Any]) -> str:
    """Build a raw_text representation of the record for text search."""
    parts = []
    for key, value in record.items():
        if key.startswith("_"):
            continue
        parts.append(f"{key}: {value}")
    return " | ".join(parts)


# =============================================================================
# MAIN ADAPTER FUNCTIONS
# =============================================================================

def parse_to_unified_records(
    file_path: Path,
    validation_result: ValidationResult,
    records: Iterator[dict[str, Any]],
) -> list[UnifiedRecord]:
    """
    Convert parser output records to UnifiedRecord list.
    
    Args:
        file_path: Path to the source file
        validation_result: Validation result with mime_type, encoding
        records: Iterator of dict records from parser
        
    Returns:
        List of UnifiedRecord objects
    """
    # Compute file SHA-256
    file_sha256 = compute_sha256(file_path)
    
    # Determine format type
    format_type = _mime_to_format(validation_result.mime_type)
    
    unified_records = []
    
    for record in records:
        # Determine location based on format
        location = _build_record_location(record, format_type)
        
        # Build record_id
        record_id = _build_record_id(file_sha256, location)
        
        # Flatten record if needed (for nested JSON)
        flat_record = _flatten_record(record)
        
        # Build field values
        fields = _create_field_values(flat_record)
        
        # Build raw and normalized text
        raw_text = _build_raw_text(flat_record)
        normalized_text = _normalize_text(raw_text)
        
        # Build offset map
        offset_map = _build_offset_map(raw_text, normalized_text)
        
        # Create UnifiedRecord
        ur = UnifiedRecord(
            record_id=record_id,
            location=location,
            fields=fields,
            raw_text=raw_text,
            normalized_text=normalized_text,
            offset_map=offset_map,
            status=RecordStatus.PENDING,
            pii_spans=[],
            medical_spans=[],
            privacy_transformations=None,
            pseudonym=None,
            metadata={
                "source_format": format_type.value,
                "source_encoding": validation_result.encoding,
                "source_file": str(file_path),
                "parser_metadata": {k: v for k, v in record.items() if k.startswith("_")},
            }
        )
        unified_records.append(ur)
    
    return unified_records


def _build_record_location(record: dict[str, Any], format_type: FormatType) -> RecordLocation:
    """Build RecordLocation from parser record metadata."""
    if format_type in (FormatType.CSV, FormatType.TSV):
        row_num = record.get("_row_number", 0)
        if isinstance(row_num, int):
            return RecordLocation.from_row(row_num - 1)  # 0-indexed
        return RecordLocation.from_row(0)
    
    elif format_type == FormatType.JSON:
        # For JSON, use row_number if available, otherwise JSON pointer
        row_num = record.get("_row_number")
        if row_num is not None:
            return RecordLocation.from_json_pointer(f"/{row_num - 1}")
        return RecordLocation.from_json_pointer("/")
    
    elif format_type == FormatType.FHIR:
        # FHIR resources use bundle entry or resource ID
        entry_num = record.get("_bundle_entry")
        if entry_num is not None:
            return RecordLocation.from_json_pointer(f"/entry/{entry_num - 1}/resource")
        fhir_id = record.get("_fhir_id")
        if fhir_id:
            return RecordLocation.from_json_pointer(f"/{fhir_id}")
        return RecordLocation.from_json_pointer("/")
    
    else:  # TEXT or UNKNOWN
        # Text files use "doc" for whole file, or line/paragraph number
        line_num = record.get("line_number")
        para_num = record.get("paragraph_number")
        if line_num is not None:
            return RecordLocation.from_row(line_num - 1)
        if para_num is not None:
            return RecordLocation.from_row(para_num - 1)
        return RecordLocation.from_doc()


def build_parsed_document(
    file_path: Path,
    validation_result: ValidationResult,
    records: Iterator[dict[str, Any]],
    format_specific: Optional[dict[str, Any]] = None,
) -> ParsedDocument:
    """
    Build a ParsedDocument from parser output.
    
    Args:
        file_path: Path to source file
        validation_result: Validation result
        records: Parser output records
        format_specific: Format-specific metadata (e.g., CSV headers, FHIR bundle type)
        
    Returns:
        ParsedDocument containing UnifiedRecords
    """
    # Create InputFile
    input_file = InputFile(
        path=file_path.relative_to(file_path.anchor) if file_path.anchor else file_path,
        sha256=compute_sha256(file_path),
        size_bytes=file_path.stat().st_size,
        format=_mime_to_format(validation_result.mime_type),
        encoding=validation_result.encoding,
        discovered_at=datetime.utcnow(),
    )
    
    # Convert records
    unified_records = parse_to_unified_records(file_path, validation_result, records)
    
    return ParsedDocument(
        source_file=input_file,
        records=unified_records,
        format_specific=format_specific or {},
    )


# =============================================================================
# REPORT ADAPTER
# =============================================================================

@dataclass
class ReportData:
    """Collected data for building FullReport."""
    processed_files: list[dict[str, Any]] = field(default_factory=list)
    quarantined_files: list[dict[str, Any]] = field(default_factory=list)
    failed_files: list[dict[str, Any]] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    peak_memory_mb: int = 0


def build_full_report(report_data: ReportData) -> FullReport:
    """
    Build FullReport from collected pipeline data.
    
    Args:
        report_data: Collected processing data
        
    Returns:
        FullReport ready for to_json()
    """
    files: dict[str, FileReportEntry] = {}
    
    totals = ReportTotals()
    totals.total_processing_duration_ms = 0
    
    for f in report_data.processed_files:
        sha256 = f.get("sha256", "")
        entry = FileReportEntry(
            input_sha256=sha256,
            output_path=f.get("output_path"),
            status="sanitized",
            processing_duration_ms=f.get("duration_ms", 0),
            peak_memory_mb=f.get("peak_memory_mb", 0),
            records_processed=f.get("record_count", 0),
            identifiers_detected=f.get("identifiers_detected", 0),
            records_linked=f.get("records_linked", 0),
            records_generalized=f.get("records_generalized", 0),
            records_suppressed=f.get("records_suppressed", 0),
            records_quarantined=f.get("records_quarantined", 0),
        )
        files[sha256] = entry
        
        totals.files_total += 1
        totals.files_sanitized += 1
        totals.records_processed += entry.records_processed
        totals.identifiers_detected += entry.identifiers_detected
        totals.records_linked += entry.records_linked
        totals.records_generalized += entry.records_generalized
        totals.records_suppressed += entry.records_suppressed
        totals.records_quarantined += entry.records_quarantined
        totals.total_processing_duration_ms += entry.processing_duration_ms
        totals.peak_memory_mb = max(totals.peak_memory_mb, entry.peak_memory_mb)
    
    for f in report_data.quarantined_files:
        sha256 = f.get("sha256", "")
        entry = FileReportEntry(
            input_sha256=sha256,
            output_path=f.get("output_path"),
            status="quarantined",
            quarantine_reason=f.get("reason"),
            records_processed=0,
        )
        files[sha256] = entry
        
        totals.files_total += 1
        totals.files_quarantined += 1
    
    for f in report_data.failed_files:
        sha256 = f.get("sha256", "")
        entry = FileReportEntry(
            input_sha256=sha256,
            output_path=None,
            status="quarantined",
            quarantine_reason=f.get("error", "Processing failed"),
        )
        files[sha256] = entry
        
        totals.files_total += 1
        totals.files_quarantined += 1
    
    # Calculate timing
    if report_data.start_time and report_data.end_time:
        duration = (report_data.end_time - report_data.start_time).total_seconds()
    else:
        duration = 0.0
    
    return FullReport(
        files=files,
        counts=totals,
        timing=ReportTiming(seconds=duration),
        resources=ReportResources(peak_rss_mb=report_data.peak_memory_mb),
    )


# =============================================================================
# RECORDS.JSONL ADAPTER
# =============================================================================

def build_records_entries(
    unified_records: list[UnifiedRecord],
    output_base: Path = Path("sanitized"),
) -> list[RecordsEntry]:
    """
    Build RecordsEntry list from UnifiedRecords.
    
    Args:
        unified_records: List of processed UnifiedRecords
        output_base: Base path for output (default: sanitized/)
        
    Returns:
        List of RecordsEntry ready for to_jsonl()
    """
    entries = []
    
    for ur in unified_records:
        # Determine output file path relative to sanitized/
        # This would come from the serializer output
        file_path = ur.metadata.get("output_file", "unknown.jsonl")
        
        # Build location string
        loc_str = str(ur.location)
        
        # Get pseudonym (may be None if not linked confidently)
        pseudonym = ur.pseudonym
        
        entry = RecordsEntry(
            file=file_path,
            loc=loc_str,
            patient=pseudonym,
        )
        entries.append(entry)
    
    return entries


# =============================================================================
# CONTRACTS ADAPTER CLASS (for pipeline integration)
# =============================================================================

class ContractsAdapter:
    """
    High-level adapter for integrating lockmate.ingestion with secret_wards contracts.
    
    Usage:
        adapter = ContractsAdapter()
        
        # During ingestion
        parsed_doc = adapter.parse_file(file_path, validation_result, parser_records)
        
        # After processing (detection, linkage, privacy)
        full_report = adapter.build_report(report_data)
        records_entries = adapter.build_records_entries(processed_records)
        
        # Write outputs
        full_report.to_json() -> report.json
        [e.to_jsonl() for e in records_entries] -> records.jsonl
    """
    
    def __init__(self) -> None:
        self._report_data = ReportData(start_time=datetime.utcnow())
    
    def parse_file(
        self,
        file_path: Path,
        validation_result: ValidationResult,
        records: Iterator[dict[str, Any]],
        format_specific: Optional[dict[str, Any]] = None,
    ) -> ParsedDocument:
        """Parse a file and return ParsedDocument with UnifiedRecords."""
        return build_parsed_document(file_path, validation_result, records, format_specific)
    
    def add_processed_file(self, file_info: dict[str, Any]) -> None:
        """Record a successfully processed file for report."""
        self._report_data.processed_files.append(file_info)
    
    def add_quarantined_file(self, file_info: dict[str, Any]) -> None:
        """Record a quarantined file for report."""
        self._report_data.quarantined_files.append(file_info)
    
    def add_failed_file(self, file_info: dict[str, Any]) -> None:
        """Record a failed file for report."""
        self._report_data.failed_files.append(file_info)
    
    def set_peak_memory(self, mb: int) -> None:
        """Update peak memory usage."""
        self._report_data.peak_memory_mb = max(self._report_data.peak_memory_mb, mb)
    
    def finalize_report(self) -> FullReport:
        """Build and return the final FullReport."""
        self._report_data.end_time = datetime.utcnow()
        return build_full_report(self._report_data)
    
    def build_records_entries(
        self,
        unified_records: list[UnifiedRecord],
        output_base: Path = Path("sanitized"),
    ) -> list[RecordsEntry]:
        """Build RecordsEntry list from processed UnifiedRecords."""
        return build_records_entries(unified_records, output_base)


__all__ = [
    "ContractsAdapter",
    "parse_to_unified_records",
    "build_parsed_document",
    "build_full_report",
    "build_records_entries",
    "FormatType",
    "RecordStatus",
    "FieldType",
    "PIIType",
    "MedicalType",
    "QuarantineReason",
    "RecordLocationType",
    "RecordLocation",
    "FieldValue",
    "UnifiedRecord",
    "InputFile",
    "ParsedDocument",
    "FileReportEntry",
    "ReportTotals",
    "ReportTiming",
    "ReportResources",
    "FullReport",
    "RecordsEntry",
    "compute_sha256",
]