"""JSON and nested JSON parsing."""

from pathlib import Path
from typing import Union, Iterator, Any, Optional
import json
import orjson
import structlog
from pydantic import BaseModel, ConfigDict

logger = structlog.get_logger()


class JSONParserConfig(BaseModel):
    """Configuration for JSON parser."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    use_orjson: bool = True  # Use orjson for speed
    max_depth: int = 100
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    array_mode: str = "items"  # "items" or "whole" - parse array items individually
    encoding: str = "utf-8"


class JSONParser:
    """Parses JSON files, including nested structures."""
    
    def __init__(self, config: Optional[JSONParserConfig] = None) -> None:
        self.config = config or JSONParserConfig()
    
    def parse(
        self, 
        file_path: Union[str, Path], 
        encoding: Optional[str] = None
    ) -> Iterator[dict[str, Any]]:
        """
        Parse a JSON file.
        
        Args:
            file_path: Path to JSON file
            encoding: File encoding
            
        Yields:
            Dict representing each record (if array) or the whole object
        """
        file_path = Path(file_path)
        enc = encoding or self.config.encoding
        
        logger.info("json.parse_started", path=str(file_path), encoding=enc)
        
        try:
            if self.config.use_orjson:
                yield from self._parse_with_orjson(file_path, enc)
            else:
                yield from self._parse_with_stdlib(file_path, enc)
                
        except json.JSONDecodeError as e:
            logger.error("json.parse_error", path=str(file_path), error=str(e))
            raise
        except orjson.JSONDecodeError as e:
            logger.error("json.parse_error", path=str(file_path), error=str(e))
            raise
        
        logger.info("json.parse_completed", path=str(file_path))
    
    def _parse_with_orjson(
        self, 
        file_path: Path, 
        encoding: str
    ) -> Iterator[dict[str, Any]]:
        """Parse using orjson."""
        with open(file_path, "rb") as f:
            data = f.read()
        
        # Check size
        if len(data) > self.config.max_file_size:
            raise ValueError(f"File exceeds max size: {len(data)} > {self.config.max_file_size}")
        
        parsed = orjson.loads(data)
        
        if isinstance(parsed, list) and self.config.array_mode == "items":
            for i, item in enumerate(parsed):
                if isinstance(item, dict):
                    yield {"_row_number": i + 1, **item}
                else:
                    yield {"_row_number": i + 1, "value": item}
        else:
            # Single object or array as whole
            if isinstance(parsed, dict):
                yield parsed
            elif isinstance(parsed, list):
                yield {"_array": parsed}
            else:
                yield {"value": parsed}
    
    def _parse_with_stdlib(
        self, 
        file_path: Path, 
        encoding: str
    ) -> Iterator[dict[str, Any]]:
        """Parse using standard library json."""
        with open(file_path, "r", encoding=encoding) as f:
            parsed = json.load(f)
        
        if isinstance(parsed, list) and self.config.array_mode == "items":
            for i, item in enumerate(parsed):
                if isinstance(item, dict):
                    yield {"_row_number": i + 1, **item}
                else:
                    yield {"_row_number": i + 1, "value": item}
        else:
            if isinstance(parsed, dict):
                yield parsed
            elif isinstance(parsed, list):
                yield {"_array": parsed}
            else:
                yield {"value": parsed}


class NestedJSONParser(JSONParser):
    """
    Parses deeply nested JSON by flattening nested structures.
    """
    
    def __init__(self, config: Optional[JSONParserConfig] = None) -> None:
        super().__init__(config)
        self.flatten_config = config or JSONParserConfig()
    
    def parse(
        self, 
        file_path: Union[str, Path], 
        encoding: Optional[str] = None
    ) -> Iterator[dict[str, Any]]:
        """Parse and flatten nested JSON structures."""
        for record in super().parse(file_path, encoding):
            if isinstance(record, dict) and "_array" in record:
                # Array was yielded as whole, flatten each item
                for i, item in enumerate(record["_array"]):
                    if isinstance(item, dict):
                        yield self._flatten_dict(item, prefix="", row_number=i+1)
                    else:
                        yield {"_row_number": i+1, "value": item}
            elif isinstance(record, dict):
                yield self._flatten_dict(record, prefix="")
            else:
                yield record
    
    def _flatten_dict(
        self, 
        d: dict[str, Any], 
        prefix: str = "", 
        row_number: Optional[int] = None,
        depth: int = 0
    ) -> dict[str, Any]:
        """
        Recursively flatten a nested dictionary.
        
        Args:
            d: Dictionary to flatten
            prefix: Key prefix for nested keys
            row_number: Optional row number
            depth: Current recursion depth
            
        Returns:
            Flattened dictionary
        """
        if depth > self.config.max_depth:
            return {**d, "_truncated": True}
        
        result = {}
        if row_number is not None:
            result["_row_number"] = row_number
        
        for key, value in d.items():
            new_key = f"{prefix}{key}" if prefix else key
            
            if isinstance(value, dict):
                # Recursively flatten nested dict
                flattened = self._flatten_dict(value, f"{new_key}.", depth=depth+1)
                result.update(flattened)
            elif isinstance(value, list):
                # Handle arrays - index them
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        flattened = self._flatten_dict(item, f"{new_key}[{i}].", depth=depth+1)
                        result.update(flattened)
                    else:
                        result[f"{new_key}[{i}]"] = item
            else:
                result[new_key] = value
        
        return result