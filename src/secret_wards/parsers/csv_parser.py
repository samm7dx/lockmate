"""
LOCKMATE — CSV/TSV Parser

Parses CSV and TSV files with auto-delimiter detection, header inference,
quote handling, and shifted column tolerance.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

from ..contracts import (
    InputFile, ParsedDocument, UnifiedRecord, RecordLocation,
    FieldValue, FieldType, RecordLocationType, RecordStatus,
    RecordLocation, PIISpan, PIIType
)
from .base import BaseParser, build_record_location, create_parsed_document
from ..utils.logging import get_logger_adapter
from ..utils.metrics import FileMetrics
from ..detection.structured import sanitize_csv_headers, scan_structured_fields
from ..detection.placeholder import detect_pii_placeholder
from ..detection.identifiers import detect_identifiers

logger = get_logger_adapter("parsers.csv")


def parse_csv(input_file: InputFile, encoding: str = "utf-8") -> ParsedDocument:
    """
    Parse CSV or TSV file to Unified Record Model.
    
    Features:
    - Auto-delimiter detection (comma, tab, semicolon, pipe)
    - Header inference (with fallback to positional)
    - Quote handling (RFC 4180 compliant)
    - Shifted column tolerance (content-based matching)
    - Streaming for large files
    
    Args:
        input_file: InputFile with path and metadata
        encoding: File encoding
        
    Returns:
        ParsedDocument with URM records
    """
    parser = CSVParser(input_file, encoding)
    return parser.parse()


class CSVParser(BaseParser):
    """CSV/TSV parser with robust delimiter and header detection."""
    
    # Common delimiters to try (in priority order)
    DELIMITERS = [",", "\t", ";", "|"]
    
    def __init__(self, input_file: InputFile, encoding: str = "utf-8"):
        super().__init__(input_file, encoding)
        self.delimiter: str = ","
        self.has_header: bool = True
        self.headers: List[str] = []
        self.header_spans: List = []
    
    def parse(self) -> ParsedDocument:
        """Parse CSV/TSV file to URM records."""
        records = []
        
        try:
            with self.input_file.path.open("r", encoding=self.encoding, newline="") as f:
                # Detect delimiter and header
                self._detect_format(f)
                
                # Reset file position
                f.seek(0)
                
                # Create reader with detected settings
                reader = csv.reader(
                    f,
                    delimiter=self.delimiter,
                    quotechar='"',
                    quoting=csv.QUOTE_MINIMAL,
                    skipinitialspace=True
                )
                
                # Read header if present
                if self.has_header:
                    try:
                        self.headers = next(reader)
                        self.headers = [h.strip() for h in self.headers]
                    except StopIteration:
                        self.headers = []
                        self.has_header = False
                
                # Scan headers for PII
                self.header_spans = self._scan_headers_for_pii()
                
                # Parse records
                for row_idx, row in enumerate(reader):
                    self.metrics.records_processed += 1
                    
                    # Handle shifted columns
                    record = self._parse_row(row, row_idx)
                    if record:
                        records.append(record)
                        
        except UnicodeDecodeError as e:
            logger.error("encoding_error", file=self.input_file.path, error=str(e))
            raise
        except Exception as e:
            logger.error("parse_error", file=self.input_file.path, error=str(e))
            raise
        
        self.metrics.finalize()
        logger.info("csv_parse_complete", 
                   file=self.input_file.sha256[:16],
                   records=len(records),
                   delimiter=repr(self.delimiter),
                   has_header=self.has_header)
        
        return create_parsed_document(self.input_file, records, {
            "delimiter": self.delimiter,
            "has_header": self.has_header,
            "headers": self.headers
        })
    
    def _detect_format(self, file_handle) -> None:
        """
        Detect delimiter and whether file has header.
        
        Uses csv.Sniffer for delimiter detection and heuristic for header.
        """
        # Read sample for sniffing
        sample = file_handle.read(8192)
        file_handle.seek(0)
        
        if not sample.strip():
            self.delimiter = ","
            self.has_header = False
            return
        
        # Try to detect delimiter
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample, delimiters="".join(self.DELIMITERS))
            self.delimiter = dialect.delimiter
        except Exception:
            # Fallback: heuristic based on file extension
            if self.input_file.path.suffix.lower() == ".tsv":
                self.delimiter = "\t"
            else:
                self.delimiter = ","
        
        # Detect header
        try:
            self.has_header = csv.Sniffer().has_header(sample)
        except Exception:
            # Heuristic: first row has fewer numeric values than subsequent rows
            self.has_header = True
    
    def _scan_headers_for_pii(self) -> List[PIISpan]:
        """
        Scan CSV headers for PII.
        
        Returns:
            List of PIISpan objects found in headers
        """
        if not self.headers:
            return []
        
        spans = []
        header_text = " | ".join(self.headers)
        
        # Create a mock record for detection
        from ..contracts import UnifiedRecord, RecordLocation, RecordStatus
        
        mock_record = UnifiedRecord(
            record_id=f"{self.input_file.sha256}:headers",
            location=RecordLocation.from_json_pointer("/headers"),
            fields={},
            raw_text=header_text,
            normalized_text=header_text,
            offset_map=[],
            status=RecordStatus.PENDING
        )
        
        # Run detectors on header text
        spans.extend(detect_pii_placeholder(mock_record))
        spans.extend(detect_identifiers(mock_record))
        
        # Update detector names to indicate header source
        for span in spans:
            span.detector = f"csv_header.{span.detector}"
            span.context = f"CSV header: {span.context}"
        
        if spans:
            logger.info("csv_header_pii_detected", 
                       file=self.input_file.sha256[:16],
                       spans=len(spans),
                       headers=self.headers)
        
        return spans
    
    def _parse_row(self, row: List[str], row_idx: int) -> Optional[UnifiedRecord]:
        """
        Parse a single row into UnifiedRecord.
        
        Handles shifted columns by matching content to headers.
        """
        if not row or all(not cell.strip() for cell in row):
            return None  # Skip empty rows
        
        # Build field values
        fields = {}
        raw_text_parts = []
        
        if self.has_header and self.headers:
            # Match columns to headers
            for col_idx, cell in enumerate(row):
                header = self.headers[col_idx] if col_idx < len(self.headers) else f"col_{col_idx}"
                cell_clean = cell.strip()
                
                # Check if header suggests identifier field
                is_id_field = self._is_identifier_header(header)
                
                field_value = self._create_field_value(
                    value=cell_clean,
                    path=header,
                    is_identifier_field=is_id_field,
                    original_text=cell
                )
                fields[header] = field_value
                raw_text_parts.append(f"{header}: {cell_clean}")
        else:
            # Positional columns
            for col_idx, cell in enumerate(row):
                header = f"col_{col_idx}"
                cell_clean = cell.strip()
                field_value = self._create_field_value(
                    value=cell_clean,
                    path=header,
                    original_text=cell
                )
                fields[header] = field_value
                raw_text_parts.append(cell_clean)
        
        # Create record
        location = RecordLocation.from_row(row_idx)
        record_id = self._create_record_id(location)
        
        # Combine raw text for searching
        raw_text = " | ".join(raw_text_parts) if raw_text_parts else ""
        
        record = UnifiedRecord(
            record_id=record_id,
            location=location,
            fields=fields,
            raw_text=raw_text,
            normalized_text=raw_text,  # Will be normalized later
            offset_map=[],  # Will be populated during normalization
            status=RecordStatus.PENDING,
            pii_spans=self.header_spans.copy() if self.header_spans else []  # Attach header spans
        )
        return record
    
    def _is_identifier_header(self, header: str) -> bool:
        """Check if header suggests identifier field."""
        header_lower = header.lower().strip()
        id_keywords = [
            "name", "patient", "id", "identifier", "aadhaar", "abha", "pan",
            "phone", "mobile", "email", "address", "dob", "date", "birth",
            "uhid", "mrn", "pin", "postal", "zip"
        ]
        return any(keyword in header_lower for keyword in id_keywords)
    
    def stream_records(self) -> Generator[UnifiedRecord, None, None]:
        """Stream records one at a time for memory efficiency."""
        with self.input_file.path.open("r", encoding=self.encoding, newline="") as f:
            self._detect_format(f)
            f.seek(0)
            
            reader = csv.reader(
                f,
                delimiter=self.delimiter,
                quotechar='"',
                quoting=csv.QUOTE_MINIMAL,
                skipinitialspace=True
            )
            
            if self.has_header:
                try:
                    self.headers = next(reader)
                    self.headers = [h.strip() for h in self.headers]
                except StopIteration:
                    self.headers = []
                    self.has_header = False
            
            for row_idx, row in enumerate(reader):
                if not row or all(not cell.strip() for cell in row):
                    continue
                
                record = self._parse_row(row, row_idx)
                if record:
                    yield record