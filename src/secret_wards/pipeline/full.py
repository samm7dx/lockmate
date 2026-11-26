"""
LOCKMATE — Full Pipeline Orchestration
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..contracts import (
    InputFile, ParsedDocument, UnifiedRecord, ProcessingMetrics,
    QuarantineResult, QuarantineReason, FullReport, FileReportEntry,
    ReportTotals, ReportTiming, ReportResources, RecordsEntry
)
from ..utils.logging import get_logger
from ..utils.metrics import ProcessingMetricsCollector, FileMetrics
from ..utils.temp import TempFileManager
from ..exceptions import LockmateError, QuarantineAllError, PathTraversalError, ResourceLimitError


logger = get_logger("pipeline")


def run_pipeline(
    input_dir: Path,
    output_dir: Path,
    secret: bytes,
    config_path: Path,
    metrics_collector: ProcessingMetricsCollector
) -> FullReport:
    """
    Run the full LOCKMATE sanitization pipeline.
    
    This is the main entry point called from main.py.
    Currently a stub — full implementation in Phase 2-13.
    
    Args:
        input_dir: Input directory to process
        output_dir: Output directory for sanitized files
        secret: RAKSHA_SECRET bytes
        config_path: Path to policy.yaml
        metrics_collector: Metrics collector for aggregation
        
    Returns:
        FullReport with all processing results
    """
    logger.info("pipeline_started", input_dir=str(input_dir), output_dir=str(output_dir))
    
    # Initialize components
    temp_manager = TempFileManager(secret)
    report = FullReport()
    start_time = metrics_collector._stages.get("pipeline_start", None)
    
    try:
        # Phase 1: Secure Intake & File Discovery
        with metrics_collector.stage("intake_discovery") as stage:
            input_files = _discover_files(input_dir, stage)
            logger.info("discovered_files", count=len(input_files))
        
        if not input_files:
            logger.warning("no_files_found", input_dir=str(input_dir))
            return _finalize_report(report, metrics_collector, start_time)
        
        # Phase 2: Process each file
        for input_file in input_files:
            file_metrics = FileMetrics(input_file.sha256)
            
            try:
                # Check resource limits
                _check_resource_limits(input_file)
                
                # Parse file to URM
                with metrics_collector.stage(f"parse_{input_file.format.value}") as stage:
                    parsed_doc = _parse_file(input_file, stage)
                
                if not parsed_doc:
                    # Quarantine unsupported/unparseable
                    _quarantine_file(
                        input_file, output_dir, temp_manager,
                        QuarantineReason.PARSE_ERROR,
                        "Failed to parse file", report, file_metrics
                    )
                    continue
                
                # Process document through pipeline
                with metrics_collector.stage("sanitize") as stage:
                    sanitized_records = _sanitize_document(
                        parsed_doc, input_file, secret, output_dir, temp_manager, stage
                    )
                
                # Write sanitized output
                with metrics_collector.stage("serialize") as stage:
                    output_paths = _serialize_output(
                        sanitized_records, input_file, output_dir, temp_manager, stage
                    )
                
                # Security gate validation
                with metrics_collector.stage("security_gate") as stage:
                    gate_passed = _run_security_gate(
                        sanitized_records, output_paths, secret, stage
                    )
                
                if not gate_passed:
                    _quarantine_file(
                        input_file, output_dir, temp_manager,
                        QuarantineReason.OUTPUT_GATE_FAILED,
                        "Security gate validation failed", report, file_metrics
                    )
                    continue
                
                # Generate records entries
                _generate_records_entries(sanitized_records, report, output_dir)
                
                # Record file success
                file_entry = FileReportEntry(
                    input_sha256=input_file.sha256,
                    output_path=str(output_paths[0].relative_to(output_dir)) if output_paths else None,
                    status="sanitized",
                    processing_duration_ms=file_metrics.finalize()["duration_ms"],
                    peak_memory_mb=file_metrics.finalize()["peak_memory_mb"],
                    records_processed=file_metrics.records_processed,
                    identifiers_detected=file_metrics.identifiers_detected,
                    records_linked=file_metrics.records_linked,
                    records_generalized=file_metrics.records_generalized,
                    records_suppressed=file_metrics.records_suppressed,
                    records_quarantined=file_metrics.records_quarantined
                )
                report.files[input_file.sha256] = file_entry
                
            except Exception as e:
                logger.error("file_processing_failed", file_sha256=input_file.sha256, error=str(e))
                _quarantine_file(
                    input_file, output_dir, temp_manager,
                    QuarantineReason.PARSE_ERROR,
                    f"Processing error: {type(e).__name__}", report, file_metrics
                )
        
        return _finalize_report(report, metrics_collector, start_time)
        
    except Exception as e:
        logger.critical("pipeline_fatal_error", error=str(e))
        raise QuarantineAllError(f"Pipeline fatal error: {e}") from e
    finally:
        temp_manager.cleanup_all()


def _discover_files(input_dir: Path, stage: "StageMetrics") -> list:
    """Discover all files in input directory."""
    from ..contracts import FormatType
    import hashlib
    
    input_files = []
    total_size = 0
    MAX_TOTAL_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB
    
    for file_path in input_dir.rglob("*"):
        if not file_path.is_file():
            continue
        
        # Check path traversal
        try:
            file_path.resolve().relative_to(input_dir.resolve())
        except ValueError:
            raise PathTraversalError(f"Path traversal attempt: {file_path}")
        
        # Check file size
        file_size = file_path.stat().st_size
        MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
        if file_size > MAX_FILE_SIZE:
            logger.warning("file_too_large", file=str(file_path), size=file_size)
            continue
        
        total_size += file_size
        if total_size > MAX_TOTAL_SIZE:
            raise ResourceLimitError(f"Total input size exceeds 2 GB limit")
        
        # Compute SHA-256
        sha256 = hashlib.sha256()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        
        # Classify format
        format_type = _classify_format(file_path)
        
        # Detect encoding (for text-based formats)
        encoding = "utf-8" if format_type != FormatType.UNKNOWN else "binary"
        
        input_file = InputFile(
            path=file_path.resolve(),
            sha256=sha256.hexdigest(),
            size_bytes=file_size,
            format=format_type,
            encoding=encoding
        )
        input_files.append(input_file)
    
    # Sort by SHA-256 for deterministic processing
    input_files.sort(key=lambda f: f.sha256)
    
    stage.records_processed = len(input_files)
    return input_files


def _classify_format(file_path: Path) -> "FormatType":
    """Classify file format by extension and content sniffing."""
    from ..contracts import FormatType
    
    suffix = file_path.suffix.lower()
    
    if suffix in [".csv"]:
        return FormatType.CSV
    elif suffix in [".tsv"]:
        return FormatType.TSV
    elif suffix in [".json"]:
        return FormatType.JSON
    elif suffix in [".txt", ".text"]:
        return FormatType.TEXT
    elif suffix in [".xml", ".fhir"]:
        return FormatType.FHIR
    else:
        # Content sniffing for extensionless files
        try:
            with file_path.open("rb") as f:
                header = f.read(512)
            
            # Check for JSON
            if header.lstrip().startswith((b"{", b"[")):
                return FormatType.JSON
            # Check for XML/FHIR
            if header.lstrip().startswith(b"<?xml") or b"<Bundle" in header or b"<Patient" in header:
                return FormatType.FHIR
            # Default to text
            return FormatType.TEXT
        except Exception:
            return FormatType.UNKNOWN


def _check_resource_limits(input_file: InputFile) -> None:
    """Check file-level resource limits."""
    MAX_NESTING_DEPTH = 50
    # Additional checks would go here for JSON/FHIR nesting
    pass


def _parse_file(input_file: InputFile, stage: "StageMetrics") -> Optional["ParsedDocument"]:
    """Parse a file based on its format."""
    # This is a stub - full implementation in Phase 2
    # For now, return None to trigger quarantine
    logger.warning("parser_not_implemented", format=input_file.format.value, file=input_file.sha256[:16])
    return None


def _sanitize_document(
    parsed_doc: "ParsedDocument",
    input_file: InputFile,
    secret: bytes,
    output_dir: Path,
    temp_manager: TempFileManager,
    stage: "StageMetrics"
) -> list:
    """Sanitize a parsed document through the full pipeline."""
    # This is a stub - full implementation in Phases 3-6
    logger.warning("sanitize_not_implemented")
    return []


def _serialize_output(
    sanitized_records: list,
    input_file: InputFile,
    output_dir: Path,
    temp_manager: TempFileManager,
    stage: "StageMetrics"
) -> list:
    """Serialize sanitized records to output files."""
    # This is a stub - full implementation in Phase 3
    logger.warning("serialize_not_implemented")
    return []


def _run_security_gate(
    sanitized_records: list,
    output_paths: list,
    secret: bytes,
    stage: "StageMetrics"
) -> bool:
    """Run security gate validation on output."""
    # This is a stub - full implementation in Phase 6
    logger.warning("security_gate_not_implemented")
    return True


def _generate_records_entries(
    sanitized_records: list,
    report: "FullReport",
    output_dir: Path
) -> None:
    """Generate records.jsonl entries."""
    # This is a stub - full implementation in Phase 6
    pass


def _quarantine_file(
    input_file: InputFile,
    output_dir: Path,
    temp_manager: TempFileManager,
    reason: "QuarantineReason",
    details: str,
    report: "FullReport",
    file_metrics: "FileMetrics"
) -> None:
    """Quarantine a file and add to report."""
    from ..contracts import QuarantineReason
    
    # Copy to quarantine directory
    quarantine_dir = output_dir / "sanitized" / "quarantined"
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    
    quarantine_path = quarantine_dir / f"{input_file.sha256}{input_file.path.suffix}"
    
    # Copy original file
    import shutil
    shutil.copy2(input_file.path, quarantine_path)
    
    # Add to report
    file_entry = FileReportEntry(
        input_sha256=input_file.sha256,
        output_path=str(quarantine_path.relative_to(output_dir)),
        status="quarantined",
        quarantine_reason=reason.value,
        processing_duration_ms=file_metrics.finalize()["duration_ms"],
        peak_memory_mb=file_metrics.finalize()["peak_memory_mb"]
    )
    report.files[input_file.sha256] = file_entry


def _finalize_report(
    report: "FullReport",
    metrics_collector: "ProcessingMetricsCollector",
    start_time: float
) -> "FullReport":
    """Finalize report with aggregate totals."""
    totals = metrics_collector.get_totals()
    
    report.counts = ReportTotals(
        files_total=len(report.files),
        files_sanitized=sum(1 for f in report.files.values() if f.status == "sanitized"),
        files_quarantined=sum(1 for f in report.files.values() if f.status == "quarantined"),
        records_processed=totals.get("records_processed", 0),
        identifiers_detected=totals.get("identifiers_detected", 0),
        records_linked=totals.get("records_linked", 0),
        records_generalized=totals.get("records_generalized", 0),
        records_suppressed=totals.get("records_suppressed", 0),
        records_quarantined=totals.get("records_quarantined", 0),
        total_processing_duration_ms=totals.get("total_duration_ms", 0),
        peak_memory_mb=int(totals.get("peak_memory_mb", 0))
    )
    
    report.timing = ReportTiming(seconds=totals.get("total_duration_ms", 0) / 1000.0)
    report.resources = ReportResources(peak_rss_mb=int(totals.get("peak_memory_mb", 0)))
    
    return report