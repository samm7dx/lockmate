"""
LOCKMATE — Full Pipeline Orchestration

Integrates intake, sanitization, output, and reporting.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, List, Tuple
import logging

from ..contracts import (
    InputFile, ParsedDocument, UnifiedRecord, ProcessingMetrics,
    QuarantineResult, QuarantineReason, FullReport, FileReportEntry,
    ReportTotals, ReportTiming, ReportResources, RecordsEntry,
    FormatType, SanitizedRecord, PIIType
)
from ..utils.logging import get_logger_adapter
from ..utils.metrics import ProcessingMetricsCollector, FileMetrics, StageMetrics
from ..utils.temp import TempFileManager
from ..exceptions import LockmateError, QuarantineAllError, PathTraversalError, ResourceLimitError
from ..intake.pipeline import IntakePipeline
from ..output.pipeline import OutputPipeline
from ..linkage.clustering import ClusteringConfig
from ..linkage.pseudonym import PseudonymManager

import logging

logger = get_logger_adapter("pipeline")


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
    import sys
    sys.setrecursionlimit(10000)
    
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
        
        logger.info("starting_sanitization_phase", parsed_docs=len(parsed_documents))
        
        if not parsed_documents and not quarantine_results:
            logger.warning("no_files_processed", input_dir=str(input_dir))
            return _finalize_report(report, metrics_collector)
        
        # Phase 2: Sanitize documents (placeholder detection + medical veto)
        sanitized_records_by_doc: Dict[str, List] = {}
        pseudonym_map: Dict[str, str] = {}
        
        for parsed_doc in parsed_documents:
            file_sha256 = parsed_doc.source_file.sha256
            
            logger.info("sanitizing_document", file_sha256=file_sha256[:16], records=len(parsed_doc.records))
            
            with metrics_collector.stage(f"sanitize_{file_sha256[:8]}") as stage:
                sanitized_records = _sanitize_document(
                    parsed_doc, secret, stage
                )
                sanitized_records_by_doc[file_sha256] = sanitized_records
                logger.info("document_sanitized", file_sha256=file_sha256[:16], sanitized_records=len(sanitized_records))
                
                # Generate pseudonyms for linked records (placeholder for Phase 8)
                for sr in sanitized_records:
                    if sr.pseudonym:
                        pseudonym_map[sr.record.record_id] = sr.pseudonym
        
        logger.info("sanitization_phase_complete", total_sanitized=sum(len(v) for v in sanitized_records_by_doc.values()))
        
        # Phase 5: Cross-hospital Patient Linkage (Phase 5)
        logger.info("starting_linkage_phase")
        with metrics_collector.stage("patient_linkage") as stage:
            pseudonym_map = _run_patient_linkage(
                sanitized_records_by_doc=sanitized_records_by_doc,
                secret=secret,
                stage=stage,
                metrics_collector=metrics_collector
            )
            logger.info("linkage_phase_complete", pseudonyms_generated=len(pseudonym_map))
        
        logger.info("starting_output_phase")
        # Phase 3: Write sanitized output + generate reports
        with metrics_collector.stage("output_and_reports") as stage:
            _write_output(
                parsed_documents=parsed_documents,
                sanitized_records_by_doc=sanitized_records_by_doc,
                quarantine_results=quarantine_results,
                output_dir=output_dir,
                stage=stage,
                metrics_collector=metrics_collector,
                pseudonym_map=pseudonym_map
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
    Sanitize a parsed document through the Phase 4 pipeline:
    1. Unicode normalization
    2. Multilingual PII detection (names, identifiers, structured fields)
    3. Clinical detection (drugs, labs, diagnoses, doctors)
    4. Medical veto (contextual disambiguation)
    5. Span merger with veto
    5. Text replacement + structured field sanitization
    6. Serialization preparation
    
    Args:
        parsed_doc: ParsedDocument with URM records
        secret: RAKSHA_SECRET bytes (for future pseudonymization)
        stage: Metrics stage tracker
        
    Returns:
        List of SanitizedRecord objects
    """
    from ..detection.normalize import apply_normalization
    from ..detection.names import detect_names
    from ..detection.identifiers import detect_identifiers
    from ..detection.structured import scan_structured_fields
    from ..detection.placeholder import detect_pii_placeholder
    from ..clinical.drugs import detect_drugs
    from ..clinical.labs import detect_labs
    from ..clinical.diagnoses import detect_diagnoses
    from ..clinical.doctors import detect_doctors
    from ..clinical.veto import merge_spans_with_veto, detect_all_medical_spans
    from ..transform.structured import sanitize_record
    from ..contracts import SanitizedRecord
    
    sanitized_records = []
    all_pii_spans = []
    all_medical_spans = []
    
    for record in parsed_doc.records:
        logger.info("sanitizing_record", record_id=record.record_id)
        
        # Step 1: Unicode normalization
        logger.info("normalizing_text", record_id=record.record_id)
        normalized_text, offset_map = apply_normalization(record)
        logger.info("normalization_returned", record_id=record.record_id, norm_len=len(normalized_text), offset_map_len=len(offset_map))
        record.normalized_text = normalized_text
        record.offset_map = offset_map
        logger.info("text_normalized", record_id=record.record_id)
        
        # Step 2: Detect PII - multilingual names
        logger.info("detecting_names", record_id=record.record_id)
        name_spans = detect_names(record)
        logger.info("names_detected", record_id=record.record_id, count=len(name_spans))
        
        # Step 3: Detect identifiers (Aadhaar, ABHA, PAN, phone, email, etc.)
        logger.debug("detecting_identifiers", record_id=record.record_id)
        id_spans = detect_identifiers(record)
        logger.debug("identifiers_detected", record_id=record.record_id, count=len(id_spans))
        
        # Step 4: Detect structured fields PII (JSON keys, CSV headers, FHIR meta)
        logger.debug("detecting_structured", record_id=record.record_id)
        struct_spans = scan_structured_fields(record)
        logger.debug("structured_detected", record_id=record.record_id, count=len(struct_spans))
        
        # Extract doctor spans from structured fields for medical veto
        doctor_struct_spans = [s for s in struct_spans if s.pii_type == PIIType.DOCTOR]
        
        # Step 5: Detect clinical expressions
        logger.debug("detecting_clinical", record_id=record.record_id)
        drug_spans = detect_drugs(record)
        lab_spans = detect_labs(record)
        diag_spans = detect_diagnoses(record)
        doctor_spans = detect_doctors(record)
        logger.debug("clinical_detected", record_id=record.record_id, 
                    drugs=len(drug_spans), labs=len(lab_spans), diagnoses=len(diag_spans), doctors=len(doctor_spans))
        
        # Combine all PII spans (excluding doctor spans from structured fields - they're medical)
        pii_spans = []
        pii_spans.extend(name_spans)
        pii_spans.extend(id_spans)
        # Filter out doctor spans from struct_spans for PII (they're medical, not PII)
        pii_spans.extend([s for s in struct_spans if s.pii_type != PIIType.DOCTOR])
        pii_spans.extend(detect_pii_placeholder(record))  # Fallback placeholder
        
        # Combine all medical spans (including doctor spans from structured fields)
        medical_spans = []
        medical_spans.extend(drug_spans)
        medical_spans.extend(lab_spans)
        medical_spans.extend(diag_spans)
        medical_spans.extend(doctor_spans)
        medical_spans.extend(doctor_struct_spans)  # Add doctor spans from structured fields
        medical_spans.extend(detect_all_medical_spans(record))
        
        # Store spans on record for later use
        record.pii_spans = pii_spans
        record.medical_spans = medical_spans
        
        all_pii_spans.extend(pii_spans)
        all_medical_spans.extend(medical_spans)
        
        # Step 6: Apply medical veto (contextual disambiguation)
        logger.debug("applying_veto", record_id=record.record_id)
        filtered_spans = merge_spans_with_veto(pii_spans, medical_spans)
        logger.debug("veto_applied", record_id=record.record_id, original=len(pii_spans), filtered=len(filtered_spans))
        
        # Step 7: Apply replacements to text AND structured fields
        logger.debug("sanitizing_record", record_id=record.record_id)
        sanitized_record = sanitize_record(record, filtered_spans)
        logger.debug("record_sanitized", record_id=record.record_id)
        
        # Assign placeholder pseudonym (will be replaced in Phase 8)
        sanitized_record.pseudonym = f"PSN-PLACEHOLDER-{record.record_id[:8]}"
        
        sanitized_records.append(sanitized_record)
    
    stage.records_processed = len(sanitized_records)
    stage.identifiers_detected = len(all_pii_spans)
    return sanitized_records


def _write_output(
    parsed_documents: List,
    sanitized_records_by_doc: Dict[str, List],
    quarantine_results: List,
    output_dir: Path,
    stage,
    metrics_collector,
    pseudonym_map: Dict[str, str]
) -> None:
    """
    Write all output: sanitized files, report.json, records.jsonl
    """
    from ..output.pipeline import OutputPipeline
    from ..contracts import FullReport
    
    output_pipeline = OutputPipeline(output_dir)
    
    # Write sanitized files
    output_paths = output_pipeline.write_sanitized_output(
        parsed_docs=parsed_documents,
        sanitized_records_by_doc=sanitized_records_by_doc,
        pseudonym_map=pseudonym_map
    )
    
    # Generate report.json and records.jsonl using the output pipeline's finalize method
    output_pipeline.finalize_output(
        parsed_docs=parsed_documents,
        sanitized_records_by_doc=sanitized_records_by_doc,
        quarantine_results=quarantine_results,
        output_paths=output_paths,
        pseudonym_map=pseudonym_map,
        metrics_collector=metrics_collector,
        total_duration_ms=0,
        peak_memory_mb=0
    )


def _finalize_report(report: "FullReport", metrics_collector) -> "FullReport":
    """Finalize the report with metrics."""
    from ..contracts import ReportTotals, ReportTiming, ReportResources
    metrics = metrics_collector.get_totals()
    report.counts = ReportTotals(
        files_total=0,
        files_sanitized=0,
        files_quarantined=0,
        records_processed=0,
        identifiers_detected=0,
        records_linked=0,
        records_generalized=0,
        records_suppressed=0,
        records_quarantined=0,
        total_processing_duration_ms=0,
        peak_memory_mb=0
    )
    report.timing = ReportTiming(seconds=0)
    report.resources = ReportResources(peak_rss_mb=0)
    return report


def _run_patient_linkage(
    sanitized_records_by_doc: Dict[str, List],
    secret: bytes,
    stage,
    metrics_collector
) -> Dict[str, str]:
    """
    Run Phase 5 cross-hospital patient linkage.
    
    Collects all sanitized records, runs clustering, generates pseudonyms,
    and returns a pseudonym map for output.
    
    Args:
        sanitized_records_by_doc: Dict of file_sha256 -> List[SanitizedRecord]
        secret: RAKSHA_SECRET bytes
        stage: Metrics stage tracker
        metrics_collector: Metrics collector
        
    Returns:
        Dict mapping record_id -> pseudonym
    """
    from ..linkage.clustering import cluster_records, ClusteringConfig, ClusterResult
    from ..linkage.pseudonym import PseudonymManager, insert_pseudonyms_into_sanitized
    from ..contracts import SanitizedRecord
    
    logger.info("collecting_all_sanitized_records")
    
    # Collect all sanitized records
    all_sanitized = []
    for records in sanitized_records_by_doc.values():
        all_sanitized.extend(records)
    
    logger.info("linkage_input_records", count=len(all_sanitized))
    
    if not all_sanitized:
        logger.warning("no_records_for_linkage")
        return {}
    
    # Run clustering
    config = ClusteringConfig(
        min_link_score=0.85,
        min_candidate_score=0.7,
        ambiguity_threshold=0.1,
        require_strong_id_for_high_confidence=True,
    )
    
    # Run clustering
    result: ClusterResult = cluster_records(all_sanitized, config=config)
    
    logger.info("clustering_result", 
               clusters=len(result.clusters),
               singletons=len(result.singleton_records),
               unresolved=len(result.unresolved_pairs))
    
    # Generate pseudonyms
    pseudonym_manager = PseudonymManager(secret)
    assigned = pseudonym_manager.assign_pseudonyms(result.clusters)
    
    # Insert pseudonyms into sanitized records
    # Group sanitized records by file_sha256
    sanitized_by_file = {}
    for file_sha256, records in sanitized_records_by_doc.items():
        sanitized_by_file[file_sha256] = records
    
    # Insert pseudonyms
    insert_pseudonyms_into_sanitized(result.clusters, sanitized_by_file, secret)
    
    # Build pseudonym map for output
    pseudonym_map = {}
    for cluster in result.clusters:
        if cluster.pseudonym:
            for record in cluster.records:
                # record is SanitizedRecord, access record.record.record_id
                if hasattr(record, 'record') and hasattr(record.record, 'record_id'):
                    rid = record.record.record_id
                elif hasattr(record, 'record_id'):
                    rid = record.record_id
                else:
                    continue
                pseudonym_map[rid] = cluster.pseudonym
    
    logger.info("pseudonyms_assigned", count=len(pseudonym_map))
    
    return pseudonym_map


# Re-export the main function for main.py
__all__ = ["run_pipeline"]