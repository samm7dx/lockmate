"""FHIR R4 ingestion support."""

from pathlib import Path
from typing import Union, Iterator, Any, Optional, Literal
import json
import orjson
import structlog
from pydantic import BaseModel, ConfigDict

# Optional FHIR resources support
try:
    from fhir.resources import get_fhir_model_class
    FHIR_AVAILABLE = True
except ImportError:
    FHIR_AVAILABLE = False

logger = structlog.get_logger()


class FHIRParserConfig(BaseModel):
    """Configuration for FHIR parser."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    use_orjson: bool = True
    validate_resources: bool = True
    bundle_mode: Literal["entries", "whole"] = "entries"
    encoding: str = "utf-8"
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    resource_types: Optional[list[str]] = None  # Filter specific types


class FHIRParser:
    """Parses FHIR R4 JSON resources and Bundles."""
    
    def __init__(self, config: Optional[FHIRParserConfig] = None) -> None:
        if not FHIR_AVAILABLE:
            raise ImportError(
                "fhir.resources package not installed. "
                "Install with: pip install fhir.resources"
            )
        self.config = config or FHIRParserConfig()
    
    def parse(
        self, 
        file_path: Union[str, Path], 
        encoding: Optional[str] = None
    ) -> Iterator[dict[str, Any]]:
        """
        Parse a FHIR JSON file (Bundle or single resource).
        
        Args:
            file_path: Path to FHIR JSON file
            encoding: File encoding
            
        Yields:
            Dict representing each FHIR resource
        """
        file_path = Path(file_path)
        enc = encoding or self.config.encoding
        
        logger.info("fhir.parse_started", path=str(file_path), encoding=enc)
        
        try:
            if self.config.use_orjson:
                data = self._load_with_orjson(file_path)
            else:
                data = self._load_with_stdlib(file_path, enc)
            
            yield from self._process_fhir_data(data)
            
        except (json.JSONDecodeError, orjson.JSONDecodeError) as e:
            logger.error("fhir.parse_error", path=str(file_path), error=str(e))
            raise
        except Exception as e:
            logger.error("fhir.process_error", path=str(file_path), error=str(e))
            raise
        
        logger.info("fhir.parse_completed", path=str(file_path))
    
    def _load_with_orjson(self, file_path: Path) -> dict[str, Any]:
        """Load JSON using orjson."""
        with open(file_path, "rb") as f:
            data = f.read()
        
        if len(data) > self.config.max_file_size:
            raise ValueError(f"File exceeds max size: {len(data)} > {self.config.max_file_size}")
        
        return orjson.loads(data)
    
    def _load_with_stdlib(self, file_path: Path, encoding: str) -> dict[str, Any]:
        """Load JSON using standard library."""
        with open(file_path, "r", encoding=encoding) as f:
            return json.load(f)
    
    def _process_fhir_data(self, data: dict[str, Any]) -> Iterator[dict[str, Any]]:
        """Process FHIR data (Bundle or single resource)."""
        resource_type = data.get("resourceType")
        
        if resource_type == "Bundle":
            yield from self._process_bundle(data)
        elif resource_type:
            # Single resource
            yield from self._process_resource(data)
        else:
            logger.warning("fhir.unknown_structure", keys=list(data.keys()))
            yield {"_raw": data}
    
    def _process_bundle(self, bundle: dict[str, Any]) -> Iterator[dict[str, Any]]:
        """Process a FHIR Bundle."""
        entry_number = 0
        
        if self.config.bundle_mode == "entries":
            entries = bundle.get("entry", [])
            for entry in entries:
                entry_number += 1
                resource = entry.get("resource")
                if resource:
                    processed = self._process_resource(resource, bundle_context=bundle)
                    for p in processed:
                        p["_bundle_entry"] = entry_number
                        p["_bundle_id"] = bundle.get("id")
                        yield p
        else:
            # Yield whole bundle with bundle context
            processed = self._process_resource(bundle, bundle_context=bundle)
            for p in processed:
                yield p
    
    def _process_resource(
        self, 
        resource: dict[str, Any], 
        bundle_context: Optional[dict[str, Any]] = None
    ) -> Iterator[dict[str, Any]]:
        """Process a single FHIR resource."""
        resource_type = resource.get("resourceType", "Unknown")
        
        # Filter by resource type if configured
        if self.config.resource_types and resource_type not in self.config.resource_types:
            return
        
        if self.config.validate_resources:
            try:
                validated = self._validate_resource(resource)
                resource = validated
            except Exception as e:
                logger.warning("fhir.validation_failed", resource_type=resource_type, error=str(e))
                resource["_validation_error"] = str(e)
        
        # Add metadata
        result = {
            **resource,
            "_resource_type": resource_type,
            "_fhir_id": resource.get("id"),
        }
        
        if bundle_context:
            result["_bundle_id"] = bundle_context.get("id")
            result["_bundle_type"] = bundle_context.get("type")
        
        yield result
    
    def _validate_resource(self, resource: dict[str, Any]) -> dict[str, Any]:
        """
        Validate FHIR resource using fhir.resources.
        
        Returns validated resource dict.
        """
        resource_type = resource.get("resourceType")
        if not resource_type:
            raise ValueError("Resource missing resourceType")
        
        # Get FHIR model class and validate
        model_class = get_fhir_model_class(resource_type)
        fhir_obj = model_class.model_validate(resource)
        
        # Convert back to dict (serializes with validation)
        return json.loads(fhir_obj.model_dump_json(exclude_none=True))


def parse_fhir_ndjson(
    file_path: Union[str, Path],
    encoding: str = "utf-8"
) -> Iterator[dict[str, Any]]:
    """
    Parse FHIR NDJSON (Newline Delimited JSON) files.
    
    Each line is a separate FHIR resource.
    """
    file_path = Path(file_path)
    
    logger.info("fhir.ndjson_started", path=str(file_path))
    
    with open(file_path, "r", encoding=encoding) as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            
            try:
                resource = json.loads(line)
                resource["_line_number"] = i + 1
                yield resource
            except json.JSONDecodeError as e:
                logger.error("fhir.ndjson_line_error", path=str(file_path), line=i+1, error=str(e))
                yield {"_error": str(e), "_line_number": i + 1, "_raw": line}
    
    logger.info("fhir.ndjson_completed", path=str(file_path))