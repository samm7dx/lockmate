"""
LOCKMATE — Plain Text Parser

Parses plain text files with encoding detection, line/paragraph segmentation,
and offset mapping for normalization.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from ..contracts import (
    InputFile, ParsedDocument, UnifiedRecord, RecordLocation,
    FieldValue, FieldType, RecordLocationType, RecordStatus
)
from .base import BaseParser, build_record_location, create_parsed_document
from ..utils.logging import get_logger
from ..utils.metrics import FileMetrics

logger = get_logger("parsers.text")


def parse_text(input_file: InputFile, encoding: str = "utf-8") -> ParsedDocument:
    """
    Parse plain text file to Unified Record Model.
    
    Features:
    - Encoding detection (already done at intake)
    - Line and paragraph segmentation
    - Offset mapping for normalization round-trip
    - Treats entire file as single record (loc="doc")
    
    Args:
        input_file: InputFile with path and metadata
        encoding: File encoding
        
    Returns:
        ParsedDocument with single URM record
    """
    parser = TextParser(input_file, encoding)
    return parser.parse()


class TextParser(BaseParser):
    """Plain text parser with segmentation and offset tracking."""
    
    def __init__(self, input_file: InputFile, encoding: str = "utf-8"):
        super().__init__(input_file, encoding)
    
    def parse(self) -> ParsedDocument:
        """Parse text file to single URM record."""
        try:
            with self.input_file.path.open("r", encoding=self.encoding) as f:
                content = f.read()
            
            if not content:
                logger.warning("empty_text_file", file=self.input_file.path)
                content = ""
            
            self.metrics.records_processed = 1
            
            # Build fields (single text field)
            fields = {
                "content": self._create_field_value(
                    value=content,
                    path="content",
                    original_text=content
                )
            }
            
            # Create single record
            location = RecordLocation.from_doc()
            record_id = self._create_record_id(location)
            
            record = UnifiedRecord(
                record_id=record_id,
                location=location,
                fields=fields,
                raw_text=content,
                normalized_text=content,  # Will be normalized later
                offset_map=[],  # Will be populated during normalization
                status=RecordStatus.PENDING
            )
            
            self.metrics.finalize()
            logger.info("text_parse_complete", 
                       file=self.input_file.sha256[:16],
                       chars=len(content))
            
            return create_parsed_document(self.input_file, [record], {
                "format": "text",
                "encoding": self.encoding,
                "char_count": len(content),
                "line_count": content.count("\n") + 1 if content else 0
            })
            
        except UnicodeDecodeError as e:
            logger.error("encoding_error", file=self.input_file.path, error=str(e))
            raise
        except Exception as e:
            logger.error("parse_error", file=self.input_file.path, error=str(e))
            raise
    
    def stream_records(self) -> Generator[UnifiedRecord, None, None]:
        """Stream single record (for API consistency)."""
        doc = self.parse()
        if doc.records:
            yield doc.records[0]