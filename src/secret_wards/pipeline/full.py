"""
LOCKMATE — Full Pipeline Orchestration

Integrates intake, sanitization, output, and reporting.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, List, Tuple

from ..contracts import (
    InputFile, ParsedDocument, UnifiedRecord, ProcessingMetrics,
    QuarantineResult, QuarantineReason, FullReport, FileReportEntry,
    ReportTotals, ReportTiming, ReportResources, RecordsEntry,
    FormatType, SanitizedRecord
)
from ..utils.logging import get_logger
from ..utils.metrics import ProcessingMetricsCollector, FileMetrics, StageMetrics
from ..utils.temp import TempFileManager
from ..exceptions import LockmateError, QuarantineAllError, PathTraversalError, ResourceLimitError
from ..intake.pipeline import IntakePipeline
from ..output.pipeline import OutputPipeline

logger = get_logger("pipeline")


def run_pipeline(
    input_dir: Path,
    output_dir: Path,
    secret: bytes,
    config_path: Path,
    metrics_collector: ProcessingMetricsCollector
):
    """
    Run the full LOCKMATE sanitization pipeline.
    
    This is the main entry point called from main.py.
    
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
    output_pipeline = OutputPipeline(output_dir)
    intake_pipeline = IntakePipeline(output_dir)
    report = FullReport()
    
    start_time = metrics_collector._stages.get("pipeline_start", None)
    
    try:
        # Phase 1: Secure Intake & File Discovery + Parsing
        with metrics_collector.stage("intake_and_parse") as stage:
            parsed_documents, quarantine_results = intake_pipeline.process_directory(input_dir)
            stage.records_processed = sum(len(doc.records) for doc in parsed_documents)
            logger.info("intake_complete", 
                       parsed=len(parsed_documents), 
                       quarantined=len(quarantine_results))
        
        if not parsed_documents and not quarantine_results:
            logger.warning("no_files_processed", input_dir=str(input_dir))
            return _finalize_report(report, metrics_collector)
        
        # Phase 2: Sanitize documents (placeholder detection + medical veto)
        sanitized_records_by_doc: Dict[str, List] = {}
        pseudonym_map: Dict[str, str] = {}
        
        for parsed_doc in parsed_documents:
            file_sha256 = parsed_doc.source_file.sha256
            
            with metrics_collector.stage(f"sanitize_{file_sha256[:8]}") as stage:
                sanitized_records = _sanitize_document(
                    parsed_doc, secret, stage
                )
                sanitized_records_by_doc[file_sha256] = sanitized_records
                
                # Generate pseudonyms for linked records (placeholder for Phase 8)
                for sr in sanitized_records:
                    if sr.pseudonym:
                        pseudonym_map[sr.record.record_id] = sr.pseudonym
        
        # Phase 3: Write sanitized output + generate reports
        with metrics_collector.stage("output_and_reports") as stage:
            _write_output(
                parsed_documents=parsed_documents,
                sanitized_records_by_doc=sanitized_records_by_doc,
                quarantine_results=[],
                output_dir=output_dir,
                stage=stage
            )
        
        return _finalize_report(report, metrics_collector)
        
    except Exception as e:
        logger.critical("pipeline_fatal_error", error=str(e))
        raise QuarantineAllError(f"Pipeline fatal error: {e}") from e
    finally:
        temp_manager.cleanup_all()


def _sanitize_document(
    parsed_doc: "ParsedDocument",
    secret: bytes,
    stage: "StageMetrics"
) -> List:
    """
    Sanitize a parsed document through the Phase 3 pipeline:
    1. Placeholder PII detection
    2. Placeholder medical veto
    3. Span merger with veto
    4. Text replacement
    5. Structured field sanitization
    6. Serialization preparation
    
    Args:
        parsed_doc: ParsedDocument with URM records
        secret: RAKSHA_SECRET bytes (for future pseudonymization)
        stage: Metrics stage tracker
        
    Returns:
        List of SanitizedRecord objects
    """
    from ..detection.placeholder import detect_pii_placeholder, detect_medical_placeholder
    from ..detection.merger import merge_spans_with_veto
    from ..transform.replacer import sanitize_record_text
    from ..contracts import SanitizedRecord
    
    sanitized_records = []
    
    for record in parsed_doc.records:
        # Step 1: Detect PII (placeholder)
        pii_spans = detect_pii_placeholder(record)
        
        # Step 2: Detect medical expressions (placeholder)
        medical_spans = detect_medical_placeholder(record)
        
        # Step 3: Apply medical veto
        filtered_spans = merge_spans_with_veto(pii_spans, medical_spans)
        
        # Step 4: Apply replacements to text
        sanitized_record = sanitize_record_text(record, filtered_spans)
        
        # Assign placeholder pseudonym (will be replaced in Phase 8)
        sanitized_record.pseudonym = f"PSN-PLACEHOLDER-{record.record_id[:8]}"
        
        sanitized_records.append(sanitized_record)
    
    stage.records_processed = len(sanitized_records)
    return sanitized_records


def _write_output(
    parsed_documents: List,
    sanitized_records_by_doc: Dict[str, List],
    quarantine_results: List,
    output_dir: Path,
    stage
) -> None:
    """
    Write all output: sanitized files, report.json, records.jsonl
    """
    from ..output.pipeline import OutputPipeline
    from ..contracts import FullReport
    import time
    
    output_pipeline = OutputPipeline(Path("."))
    
    # Create a mock report for now
    report = FullReport()
    
    # Write sanitized files
    output_pipeline.write_sanitized_output(
        parsed_documents=parsed_documents,
        sanitized_records_by_doc=sanitized_records_by_doc,
        pseudonym_map={}
    )
    
    # Generate report.json
    from ..contracts import FullReport, FileReportEntry, ReportTotals
    report = FullReport()
    
    # TODO: Generate proper report with actual metrics
    # For now, write minimal report
    from ..contracts import ReportTotals, ReportTiming, ReportResources
    report.counts = ReportTotals(
        files_total=len(parsed_documents),
        files_sanitized=len(parsed_documents),
        files_quarantined=0,
        records_processed=sum(len(doc.records) for doc in parsed_documents),
        identifiers_detected=0,
        records_linked=0,
        records_generalized=0,
        records_suppressed=0,
        records_quarantined=0
    )
    report.timing = ReportTiming(seconds=0)
    report.resources = ReportResources(peak_rss_mb=0)
    
    # Write report.json
    from ..output.writer import write_atomic
    write_atomic(Path(".") / "report.json", report.to_json(), mode="w")
    
    # Write records.jsonl (minimal for now)
    write_atomic(Path(".") / "records.jsonl", "", mode="w")


# Re-export the main function for main.py
__all__ = ["run_pipeline"]