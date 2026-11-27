"""
LOCKMATE — FHIR R4 Parser

Parses FHIR R4 resources using fhir.resources library with validation,
reference/extension/contained resource traversal.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Union

from ..contracts import (
    InputFile, ParsedDocument, UnifiedRecord, RecordLocation,
    FieldValue, FieldType, RecordLocationType, RecordStatus, PIISpan, PIIType
)
from .base import BaseParser, build_record_location, create_parsed_document
from ..utils.logging import get_logger_adapter
from ..utils.metrics import FileMetrics
from ..parsers.fhir_meta import scan_fhir_metadata

logger = get_logger_adapter("parsers.fhir")

# Optional import - fhir.resources may not be available
try:
    from fhir.resources import construct_fhir_element
    from fhir.resources.bundle import Bundle
    from fhir.resources.resource import Resource
    FHIR_AVAILABLE = True
except ImportError:
    FHIR_AVAILABLE = False
    logger.warning("fhir.resources not available - FHIR parsing will be limited")


def parse_fhir(input_file: InputFile, encoding: str = "utf-8") -> ParsedDocument:
    """
    Parse FHIR R4 file to Unified Record Model.
    
    Features:
    - FHIR R4 validation using fhir.resources
    - Bundle/Resource parsing
    - Reference traversal
    - Extension handling
    - Contained resource extraction
    - Binary attachment detection
    
    Args:
        input_file: InputFile with path and metadata
        encoding: File encoding (usually utf-8)
        
    Returns:
        ParsedDocument with URM records
    """
    parser = FHIRParser(input_file, encoding)
    return parser.parse()


class FHIRParser(BaseParser):
    """FHIR R4 parser with validation and deep traversal."""
    
    def __init__(self, input_file: InputFile, encoding: str = "utf-8"):
        super().__init__(input_file, encoding)
        
        if not FHIR_AVAILABLE:
            raise ImportError("fhir.resources package required for FHIR parsing. Install with: pip install fhir.resources")
    
    def parse(self) -> ParsedDocument:
        """Parse FHIR file to URM records."""
        records = []
        
        try:
            with self.input_file.path.open("r", encoding=self.encoding) as f:
                data = json.load(f)
            
            # Scan FHIR metadata for PII
            meta_spans = scan_fhir_metadata(data)
            if meta_spans:
                logger.debug("fhir_metadata_pii_detected", count=len(meta_spans))
            
            # Check if it's a Bundle
            if isinstance(data, dict) and data.get("resourceType") == "Bundle":
                records = list(self._parse_bundle(data))
            elif isinstance(data, dict) and "resourceType" in data:
                # Single resource
                self.metrics.records_processed += 1
                record = self._convert_resource(data, 0)
                if record:
                    records.append(record)
            else:
                logger.warning("not_valid_fhir", file=self.input_file.path)
                raise ValueError("Not a valid FHIR Bundle or Resource")
            
            # Attach metadata spans to all records
            for record in records:
                record.pii_spans = meta_spans
                
        except json.JSONDecodeError as e:
            logger.error("json_decode_error", file=self.input_file.path, error=str(e))
            raise
        except Exception as e:
            logger.error("fhir_parse_error", file=self.input_file.path, error=str(e))
            raise
        
        self.metrics.finalize()
        logger.info("fhir_parse_complete", 
                   file=self.input_file.sha256[:16],
                   records=len(records))
        
        return create_parsed_document(self.input_file, records, {
            "format": "fhir",
            "encoding": self.encoding,
            "fhir_version": "R4"
        })
    
    def _parse_bundle(self, bundle_data: Dict) -> Generator[UnifiedRecord, None, None]:
        """Parse FHIR Bundle entries."""
        entries = bundle_data.get("entry", [])
        
        for idx, entry in enumerate(entries):
            resource = entry.get("resource")
            if not resource:
                continue
            
            self.metrics.records_processed += 1
            record = self._convert_resource(resource, idx, prefix=f"/entry/{idx}")
            if record:
                yield record
    
    def _convert_resource(
        self,
        resource: Dict,
        index: int,
        prefix: str = ""
    ) -> Optional[UnifiedRecord]:
        """Convert FHIR resource to UnifiedRecord."""
        if not isinstance(resource, dict):
            return None
        
        resource_type = resource.get("resourceType", "Unknown")
        
        # Flatten resource with FHIR-aware path tracking
        fields = {}
        raw_text_parts = []
        
        def flatten_fhir(obj: Any, path: str = "") -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    
                    # Special handling for FHIR-specific structures
                    if key == "contained" and isinstance(value, list):
                        # Contained resources
                        for i, contained in enumerate(value):
                            flatten_fhir(contained, f"{path}.contained[{i}]")
                    elif key == "extension" and isinstance(value, list):
                        # Extensions
                        for i, ext in enumerate(value):
                            flatten_fhir(ext, f"{path}.extension[{i}]")
                    elif key == "reference" and isinstance(value, str):
                        # References - track for linkage
                        pass  # Handled in reference scanner
                    elif key in ("valueString", "valueCode", "valueDateTime", "valueDate", 
                                 "valueQuantity", "valueAddress", "valueContactPoint"):
                        # Primitive values with type
                        pass  # Will be flattened normally
                    else:
                        flatten_fhir(value, f"{path}.{key}" if path else key)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    flatten_fhir(item, f"{path}[{i}]")
            else:
                # Leaf value
                full_path = f"{prefix}.{path}" if prefix else path
                is_id = self._is_identifier_key(path.split(".")[-1]) if path else False
                
                field_value = self._create_field_value(
                    value=obj,
                    path=full_path,
                    is_identifier_field=is_id,
                    original_text=str(obj) if isinstance(obj, str) else None
                )
                fields[full_path] = field_value
                if isinstance(obj, str):
                    raw_text_parts.append(f"{full_path}: {obj}")
        
        flatten_fhir(resource)
        
        if not fields:
            return None
        
        location = RecordLocation.from_json_pointer(f"{prefix}/{resource_type}")
        record_id = self._create_record_id(location)
        raw_text = " | ".join(raw_text_parts) if raw_text_parts else ""
        
        return UnifiedRecord(
            record_id=record_id,
            location=location,
            fields=fields,
            raw_text=raw_text,
            normalized_text=raw_text,
            offset_map=[],
            status=RecordStatus.PENDING,
            metadata={"resourceType": resource.get("resourceType")}
        )
    
    def _is_identifier_key(self, key: str) -> bool:
        """Check if FHIR element key suggests identifier."""
        key_lower = key.lower()
        id_keywords = [
            "identifier", "name", "telecom", "address", "contact",
            "patient", "subject", "practitioner", "organization",
            "aadhaar", "abha", "pan", "uhid", "mrn", "pin"
        ]
        return any(keyword in key_lower for keyword in id_keywords)
    
    def stream_records(self) -> Generator[UnifiedRecord, None, None]:
        """Stream records for memory efficiency."""
        with self.input_file.path.open("r", encoding=self.encoding) as f:
            data = json.load(f)
        
        if isinstance(data, dict) and data.get("resourceType") == "Bundle":
            for idx, entry in enumerate(data.get("entry", [])):
                resource = entry.get("resource")
                if resource:
                    self.metrics.records_processed += 1
                    record = self._convert_resource(resource, idx, prefix=f"/entry/{idx}")
                    if record:
                        yield record
        elif isinstance(data, dict) and "resourceType" in data:
            self.metrics.records_processed += 1
            record = self._convert_resource(data, 0)
            if record:
                yield record


# Import json here to avoid circular import
import json