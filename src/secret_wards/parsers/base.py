"""
LOCKMATE — Base Parser Classes

Common utilities and base classes for all format parsers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Union

from ..contracts import (
    InputFile, ParsedDocument, UnifiedRecord, RecordLocation,
    FieldValue, FieldType, RecordLocationType, RecordStatus
)
from ..utils.logging import get_logger
from ..utils.metrics import FileMetrics

logger = get_logger("parsers.base")


class BaseParser(ABC):
    """Abstract base class for format parsers."""
    
    def __init__(self, input_file, encoding: str = "utf-8"):
        self.input_file = input_file
        self.encoding = encoding
        self.metrics = FileMetrics(input_file.sha256)
    
    @abstractmethod
    def parse(self) -> "ParsedDocument":
        """Parse file and return ParsedDocument with URM records."""
        pass
    
    def _create_record_id(self, location: RecordLocation) -> str:
        """Create stable record ID from file hash and location."""
        return f"{self.input_file.sha256}:{location}"
    
    def _infer_field_type(self, value: Any) -> FieldType:
        """Infer field type from Python value."""
        if isinstance(value, bool):
            return FieldType.BOOLEAN
        elif isinstance(value, int):
            return FieldType.NUMBER
        elif isinstance(value, float):
            return FieldType.NUMBER
        elif isinstance(value, str):
            # Could be date, but we'll treat as string initially
            return FieldType.STRING
        elif isinstance(value, (list, tuple)):
            return FieldType.ARRAY
        elif isinstance(value, dict):
            return FieldType.OBJECT
        else:
            return FieldType.STRING
    
    def _create_field_value(
        self,
        value: Any,
        path: str,
        is_identifier_field: bool = False,
        original_text: Optional[str] = None
    ) -> FieldValue:
        """Create FieldValue with inferred type."""
        return FieldValue(
            value=value,
            field_type=self._infer_field_type(value),
            path=path,
            is_identifier_field=is_identifier_field,
            original_text=original_text or str(value) if isinstance(value, str) else None
        )


class StreamingParserMixin:
    """Mixin for parsers that support streaming large files."""
    
    def stream_records(self) -> Generator[UnifiedRecord, None, None]:
        """Yield records one at a time for memory efficiency."""
        raise NotImplementedError("Streaming not implemented for this parser")


def build_record_location(
    location_type: RecordLocationType,
    value: Union[int, str]
) -> RecordLocation:
    """Build RecordLocation from type and value."""
    if location_type == RecordLocationType.ROW:
        return RecordLocation.from_row(int(value))
    elif location_type == RecordLocationType.JSON_POINTER:
        return RecordLocation.from_json_pointer(str(value))
    else:
        return RecordLocation.from_doc()


def create_parsed_document(
    input_file,
    records: List["UnifiedRecord"],
    format_specific: Optional[Dict[str, Any]] = None
) -> "ParsedDocument":
    """Factory function to create ParsedDocument."""
    return ParsedDocument(
        source_file=input_file,
        records=records,
        format_specific=format_specific or {}
    )