"""
LOCKMATE — JSON Parser

Schema-agnostic JSON parser with streaming support for large files,
nested object/array traversal, and JSON Pointer path tracking.
"""

from __future__ import annotations

import json
import ijson
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Union

from ..contracts import (
    InputFile, ParsedDocument, UnifiedRecord, RecordLocation,
    FieldValue, FieldType, RecordLocationType, RecordStatus
)
from .base import BaseParser, build_record_location, create_parsed_document
from ..utils.logging import get_logger_adapter
from ..utils.metrics import FileMetrics

logger = get_logger_adapter("parsers.json")


def parse_json(input_file: InputFile, encoding: str = "utf-8") -> ParsedDocument:
    """
    Parse JSON file to Unified Record Model.
    
    Features:
    - Schema-agnostic: handles any JSON structure
    - Streaming for large files (ijson)
    - Nested object/array traversal
    - JSON Pointer (RFC 6901) path tracking
    - Array element indexing
    
    Args:
        input_file: InputFile with path and metadata
        encoding: File encoding
        
    Returns:
        ParsedDocument with URM records
    """
    parser = JSONParser(input_file, encoding)
    return parser.parse()


class JSONParser(BaseParser):
    """JSON parser with streaming and nested traversal support."""
    
    MAX_NESTING_DEPTH = 50
    
    def __init__(self, input_file: InputFile, encoding: str = "utf-8"):
        super().__init__(input_file, encoding)
    
    def parse(self) -> ParsedDocument:
        """Parse JSON file to URM records."""
        records = []
        
        try:
            # First, try to load as single JSON to determine structure
            with self.input_file.path.open("r", encoding=self.encoding) as f:
                first_char = f.read(1)
                f.seek(0)
                
                if first_char == "[":
                    # JSON array - stream elements as records
                    records = list(self._parse_json_array())
                elif first_char == "{":
                    # JSON object - parse as single record or traverse
                    records = list(self._parse_json_object())
                else:
                    # Not valid JSON start
                    raise ValueError("JSON must start with [ or {")
                    
        except json.JSONDecodeError as e:
            logger.error("json_decode_error", file=self.input_file.path, error=str(e))
            raise
        except Exception as e:
            logger.error("parse_error", file=self.input_file.path, error=str(e))
            raise
        
        self.metrics.finalize()
        logger.info("json_parse_complete", 
                   file=self.input_file.sha256[:16],
                   records=len(records))
        
        return create_parsed_document(self.input_file, records, {
            "format": "json",
            "encoding": self.encoding
        })
    
    def _parse_json_array(self) -> Generator[UnifiedRecord, None, None]:
        """Parse JSON array with streaming (each element = record)."""
        with self.input_file.path.open("rb") as f:
            # Use ijson for streaming
            parser = ijson.items(f, "item")
            for idx, item in enumerate(parser):
                self.metrics.records_processed += 1
                record = self._convert_to_record(item, idx)
                if record:
                    yield record
    
    def _parse_json_object(self) -> Generator[UnifiedRecord, None, None]:
        """Parse JSON object - could be single record or container."""
        with self.input_file.path.open("r", encoding=self.encoding) as f:
            data = json.load(f)
        
        # If it's a FHIR Bundle or similar container, extract entries
        if isinstance(data, dict):
            if data.get("resourceType") == "Bundle" and "entry" in data:
                # FHIR Bundle - parse each entry
                for idx, entry in enumerate(data.get("entry", [])):
                    self.metrics.records_processed += 1
                    record = self._convert_to_record(entry, idx, prefix="/entry")
                    if record:
                        yield record
            elif data.get("resourceType"):
                # Single FHIR resource
                self.metrics.records_processed += 1
                record = self._convert_to_record(data, 0)
                if record:
                    yield record
            else:
                # Generic object - treat as single record
                self.metrics.records_processed += 1
                record = self._convert_to_record(data, 0)
                if record:
                    yield record
    
    def _convert_to_record(
        self,
        data: Any,
        index: int,
        prefix: str = ""
    ) -> Optional[UnifiedRecord]:
        """Convert JSON data to UnifiedRecord with full path tracking."""
        if data is None:
            return None
        
        # Flatten nested structure with path tracking
        fields = {}
        raw_text_parts = []
        
        def flatten(obj: Any, path: str = "") -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}/{key}" if path else key
                    flatten(value, new_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    new_path = f"{path}/{i}"
                    flatten(item, new_path)
            else:
                # Leaf value
                full_path = prefix + path if prefix else path
                is_id = self._is_identifier_key(path.split("/")[-1])
                
                field_value = self._create_field_value(
                    value=obj,
                    path=full_path,
                    is_identifier_field=is_id,
                    original_text=str(obj) if isinstance(obj, str) else None
                )
                fields[full_path] = field_value
                raw_text_parts.append(f"{full_path}: {obj}")
        
        flatten(data)
        
        if not fields:
            return None
        
        location = RecordLocation.from_json_pointer(prefix or "/")
        record_id = self._create_record_id(location)
        raw_text = " | ".join(raw_text_parts) if raw_text_parts else ""
        
        return UnifiedRecord(
            record_id=record_id,
            location=location,
            fields=fields,
            raw_text=raw_text,
            normalized_text=raw_text,
            offset_map=[],
            status=RecordStatus.PENDING
        )
    
    def _is_identifier_key(self, key: str) -> bool:
        """Check if JSON key suggests identifier field."""
        key_lower = key.lower()
        id_keywords = [
            "name", "patient", "id", "identifier", "aadhaar", "abha", "pan",
            "phone", "mobile", "email", "address", "dob", "date", "birth",
            "uhid", "mrn", "pin", "postal", "zip", "telecom", "contact"
        ]
        return any(keyword in key_lower for keyword in id_keywords)
    
    def stream_records(self) -> Generator[UnifiedRecord, None, None]:
        """Stream records for memory efficiency."""
        with self.input_file.path.open("r", encoding=self.encoding) as f:
            first_char = f.read(1)
            f.seek(0)
            
            if first_char == "[":
                yield from self._parse_json_array()
            elif first_char == "{":
                yield from self._parse_json_object()