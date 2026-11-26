"""
LOCKMATE — Intake Pipeline Integration

Orchestrates file discovery, classification, parsing, and quarantine.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple, Optional

from ..contracts import (
    InputFile, ParsedDocument, QuarantineResult, FormatType, QuarantineReason
)
from ..utils.logging import get_logger
from ..utils.metrics import FileMetrics
from ..exceptions import LockmateError, ParseError, UnsupportedFormatError
from .discovery import discover_files
from .classifier import classify_format
from .encoding import detect_encoding
from .quarantine import quarantine_file, create_quarantine_entry, get_reason_details
from ..parsers.csv_parser import parse_csv
from ..parsers.json_parser import parse_json
from ..parsers.text_parser import parse_text
from ..parsers.fhir_parser import parse_fhir

logger = get_logger("intake.pipeline")


class IntakePipeline:
    """
    Intake pipeline orchestrator.
    
    Coordinates file discovery, format classification, encoding detection,
    parsing to URM, and quarantine handling.
    """
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
    
    def process_directory(
        self,
        input_dir: Path,
        max_file_size: int = 100 * 1024 * 1024,
        max_total_size: int = 2 * 1024 * 1024 * 1024
    ) -> Tuple[List[ParsedDocument], List[QuarantineResult]]:
        """
        Process all files in input directory.
        
        Args:
            input_dir: Input directory path
            max_file_size: Maximum file size in bytes
            max_total_size: Maximum total input size in bytes
            
        Returns:
            Tuple of (successfully parsed documents, quarantine results)
        """
        logger.info("intake_started", input_dir=str(input_dir))
        
        # Phase 1: Discover files
        input_files = discover_files(input_dir, max_file_size, max_total_size)
        logger.info("files_discovered", count=len(input_files))
        
        if not input_files:
            logger.warning("no_files_found", input_dir=str(input_dir))
            return [], []
        
        # Phase 2: Process each file
        parsed_documents: List[ParsedDocument] = []
        quarantine_results: List[QuarantineResult] = []
        
        for input_file in input_files:
            file_metrics = FileMetrics(input_file.sha256)
            
            # Create updated InputFile early for error handling
            updated_input_file = input_file
            
            try:
                # Classify format
                format_type = classify_format(input_file.path)
                if format_type == FormatType.UNKNOWN:
                    raise UnsupportedFormatError(
                        f"Unable to classify format: {input_file.path}",
                        str(input_file.path), "unknown"
                    )
                
                # Detect encoding
                encoding = detect_encoding(input_file.path, format_type)
                
                # Create updated InputFile with detected info (InputFile is frozen)
                updated_input_file = InputFile(
                    path=input_file.path,
                    sha256=input_file.sha256,
                    size_bytes=input_file.size_bytes,
                    format=format_type,
                    encoding=encoding,
                    discovered_at=input_file.discovered_at
                )
                
                # Parse based on format
                parsed_doc = self._parse_file(updated_input_file, format_type, encoding)
                
                if parsed_doc:
                    parsed_documents.append(parsed_doc)
                    logger.debug("file_parsed", extra={
                        "file_sha256": updated_input_file.sha256[:16],
                        "format": format_type.value,
                        "records": len(parsed_doc.records)
                    })
                else:
                    raise ParseError(
                        "Parser returned no document",
                        str(updated_input_file.path), format_type.value
                    )
                    
            except UnsupportedFormatError as e:
                logger.warning("unsupported_format", extra={
                    "file_sha256": updated_input_file.sha256[:16],
                    "reason": str(e)
                })
                quarantine_results.append(quarantine_file(
                    updated_input_file, self.output_dir,
                    QuarantineReason.UNSUPPORTED_FORMAT,
                    f"Unsupported format: {e}"
                ))
                
            except ParseError as e:
                logger.warning("parse_error", extra={
                    "file_sha256": updated_input_file.sha256[:16],
                    "error": str(e)
                })
                quarantine_results.append(quarantine_file(
                    updated_input_file, self.output_dir,
                    QuarantineReason.PARSE_ERROR,
                    f"Parse error: {e}"
                ))
                
            except Exception as e:
                logger.error("unexpected_error", extra={
                    "file_sha256": updated_input_file.sha256[:16],
                    "error_type": type(e).__name__,
                    "error": str(e)[:200]
                })
                quarantine_results.append(quarantine_file(
                    updated_input_file, self.output_dir,
                    QuarantineReason.PARSE_ERROR,
                    f"Unexpected error: {type(e).__name__}: {e}"
                ))
            
            # Record file metrics (even for quarantined files)
            final_metrics = file_metrics.finalize()
            logger.debug("file_metrics", **final_metrics)
        
        # Summary
        sanitized_count = len(parsed_documents)
        quarantined_count = len(quarantine_results)
        logger.info("intake_complete",
                   total=len(input_files),
                   sanitized=sanitized_count,
                   quarantined=quarantined_count)
        
        return parsed_documents, quarantine_results
    
    def _parse_file(
        self,
        input_file,
        format_type,
        encoding: str
    ):
        """Parse file based on format type."""
        from ..parsers import (
            parse_csv, parse_json, parse_text, parse_fhir
        )
        
        if format_type in (FormatType.CSV, FormatType.TSV):
            return parse_csv(input_file, encoding)
        elif format_type == FormatType.JSON:
            return parse_json(input_file, encoding)
        elif format_type == FormatType.TEXT:
            return parse_text(input_file, encoding)
        elif format_type == FormatType.FHIR:
            return parse_fhir(input_file, encoding)
        else:
            raise ValueError(f"Unknown format type: {format_type}")
    
    def get_quarantine_summary(self, quarantine_results: List) -> dict:
        """Generate summary of quarantined files by reason."""
        from collections import Counter
        reasons = [q.reason.value for q in quarantine_results]
        return dict(Counter(reasons))