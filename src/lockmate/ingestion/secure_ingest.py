"""Secure ingestion pipeline with contracts adapter integration."""

from pathlib import Path
from typing import Any, Iterator, Self, Optional
from pydantic import BaseModel, Field, ConfigDict
import structlog
from datetime import datetime
import uuid

from lockmate.ingestion.validation import (
    PathGuard, 
    SymlinkGuard, 
    SizeLimiter, 
    FileValidator, 
    QuarantineManager,
    QuarantineConfig,
    ValidationConfig,
    ValidationResult
)
from lockmate.ingestion.parsers import (
    CSVParser, 
    JSONParser, 
    TextParser, 
    FHIRParser
)
from lockmate.ingestion.output import (
    ReportGenerator, 
    ReportConfig,
    RecordsGenerator, 
    RecordsConfig,
    AtomicWriter
)

# Contracts adapter (optional - available after merging origin/main)
try:
    from lockmate.ingestion.adapters import (
        ContractsAdapter,
        build_full_report,
        build_records_entries,
        ParsedDocument,
        UnifiedRecord,
        RecordsEntry,
    )
    CONTRACTS_ADAPTER_AVAILABLE = True
except ImportError:
    CONTRACTS_ADAPTER_AVAILABLE = False

logger = structlog.get_logger()


class IngestionConfig(BaseModel):
    """Configuration for the secure ingestion pipeline."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    input_dir: Path
    output_dir: Path
    quarantine_dir: Path
    allowed_roots: list[Path] = []
    
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    max_total_size: int = 1024 * 1024 * 1024  # 1GB
    follow_symlinks: bool = False
    
    # Validation settings
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    
    # Contracts adapter settings
    use_contracts_adapter: bool = True  # Enable contracts adapter when available


class IngestionResult(BaseModel):
    """Result of an ingestion task."""
    job_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None
    success: bool = False
    total_records: int = 0
    processed_files: list[str] = []
    failed_files: list[str] = []
    quarantined_files: list[str] = []
    errors: list[dict[str, Any]] = []


class SecureIngestionPipeline:
    """Secure file ingestion and processing pipeline."""
    
    def __init__(self, config: IngestionConfig) -> None:
        self.config = config
        self.path_guard = PathGuard(allowed_roots=config.allowed_roots or [config.input_dir])
        self.symlink_guard = SymlinkGuard(enabled=not config.follow_symlinks)
        self.size_limiter = SizeLimiter(max_file_size=config.max_file_size)
        self.validator = FileValidator(config=config.validation)
        quarantine_config = QuarantineConfig(quarantine_path=config.quarantine_dir)
        self.quarantine = QuarantineManager(config=quarantine_config)
        
        # Initialize generators
        report_config = ReportConfig(output_dir=config.output_dir)
        self.report_gen = ReportGenerator(config=report_config)
        
        records_config = RecordsConfig(output_dir=config.output_dir)
        self.records_gen = RecordsGenerator(config=records_config)
        
        # Initialize contracts adapter if available and enabled
        self.contracts_adapter: Optional[ContractsAdapter] = None
        if config.use_contracts_adapter and CONTRACTS_ADAPTER_AVAILABLE:
            self.contracts_adapter = ContractsAdapter()
            logger.info("contracts_adapter.enabled")
        elif config.use_contracts_adapter and not CONTRACTS_ADAPTER_AVAILABLE:
            logger.warning("contracts_adapter.requested_but_unavailable")
        
        # Track processed unified records for contracts output
        self._processed_unified_records: list[UnifiedRecord] = []

    def ingest_file(self, file_path: Path) -> Iterator[dict[str, Any]]:
        """Ingest a single file securely."""
        try:
            # 1. Path Security
            safe_path = self.path_guard.validate(file_path)
            
            # 2. Symlink Security
            self.symlink_guard.check(safe_path)
            
            # 3. Size Limits
            self.size_limiter.check(safe_path)
            
            # 4. File Validation
            validation_result = self.validator.validate(safe_path)
            if not validation_result.is_valid:
                logger.warn("ingestion.file_invalid", path=str(file_path), reason=validation_result.reason)
                self.quarantine.quarantine(safe_path, reason=validation_result.reason)
                return
            
            # 5. Parsing
            parser = self._get_parser(validation_result.mime_type)
            yield from parser.parse(safe_path, encoding=validation_result.encoding)
            
        except Exception as e:
            logger.error("ingestion.file_failed", path=str(file_path), error=str(e))
            self.quarantine.quarantine(file_path, reason=f"Exception: {str(e)}")
            raise

    def _get_parser(self, mime_type: str) -> Any:
        """Get the appropriate parser for the given MIME type."""
        if "csv" in mime_type or "tab-separated" in mime_type:
            return CSVParser()
        elif "json" in mime_type:
            return JSONParser()
        elif "fhir" in mime_type:
            return FHIRParser()
        else:
            return TextParser()

    def run(self) -> IngestionResult:
        """Run the ingestion pipeline on the input directory."""
        result = IngestionResult()
        
        # Ensure input directory exists
        if not self.config.input_dir.exists():
            raise ValueError(f"Input directory does not exist: {self.config.input_dir}")
        
        # Find all files in input directory
        files = list(self.config.input_dir.rglob("*"))
        files = [f for f in files if f.is_file()]
        
        # Start report generation with pipeline's job_id
        self.report_gen.start_job(
            metadata={
                "input_dir": str(self.config.input_dir),
                "file_count": len(files)
            },
            job_id=result.job_id
        )
        
        # Initialize contracts adapter tracking
        if self.contracts_adapter:
            self._processed_unified_records = []
        
        logger.info("ingestion.started", input_dir=str(self.config.input_dir), file_count=len(files))
        
        for file_path in files:
            try:
                self._process_file(file_path, result)
            except Exception as e:
                logger.error("ingestion.file_error", path=str(file_path), error=str(e))
                result.failed_files.append(str(file_path))
                result.errors.append({"file": str(file_path), "error": str(e)})
        
        result.finished_at = datetime.utcnow()
        result.success = len(result.failed_files) == 0
        
        # Write final report (legacy format)
        self.report_gen.write()
        
        # Write contracts-based outputs if adapter is available
        if self.contracts_adapter and self._processed_unified_records:
            self._write_contracts_outputs(result.job_id)
        
        logger.info("ingestion.completed", 
                   job_id=str(result.job_id),
                   total_records=result.total_records,
                   processed=len(result.processed_files),
                   failed=len(result.failed_files),
                   quarantined=len(result.quarantined_files))
        
        return result
    
    def _write_contracts_outputs(self, job_id: uuid.UUID) -> None:
        """Write report.json and records.jsonl using secret_wards contracts format."""
        try:
            # Build FullReport using contracts adapter
            report_data = self.contracts_adapter.finalize_report()
            
            # Write report.json
            report_path = self.config.output_dir / "report.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_json = report_data.to_json()
            report_path.write_text(report_json)
            logger.info("contracts.report_written", path=str(report_path))
            
            # Build RecordsEntry list
            records_entries = self.contracts_adapter.build_records_entries(
                self._processed_unified_records,
                output_base=Path("sanitized")
            )
            
            # Write records.jsonl
            records_path = self.config.output_dir / "records.jsonl"
            with records_path.open("w") as f:
                for entry in records_entries:
                    f.write(entry.to_jsonl() + "\n")
            logger.info("contracts.records_written", path=str(records_path), count=len(records_entries))
            
        except Exception as e:
            logger.error("contracts.output_failed", error=str(e))
            # Don't fail the whole pipeline if contracts output fails

    def _process_file(self, file_path: Path, result: IngestionResult) -> None:
        """Process a single file and update result."""
        try:
            # 1. Path Security
            safe_path = self.path_guard.validate(file_path)
            
            # 2. Symlink Security
            self.symlink_guard.check(safe_path)
            
            # 3. Size Limits
            self.size_limiter.check(safe_path)
            
            # 4. File Validation
            validation_result = self.validator.validate(safe_path)
            if not validation_result.is_valid:
                logger.warn("ingestion.file_invalid", path=str(file_path), reason=validation_result.reason)
                self.quarantine.quarantine(safe_path, reason=validation_result.reason)
                result.quarantined_files.append(str(file_path))
                self.report_gen.add_file_quarantined(file_path)
                # Track for contracts adapter
                if self.contracts_adapter:
                    import hashlib
                    sha256 = hashlib.sha256()
                    with safe_path.open("rb") as f:
                        for chunk in iter(lambda: f.read(8192), b""):
                            sha256.update(chunk)
                    self.contracts_adapter.add_quarantined_file({
                        "sha256": sha256.hexdigest(),
                        "reason": validation_result.reason,
                    })
                return
            
            # 5. Parsing
            parser = self._get_parser(validation_result.mime_type)
            records = list(parser.parse(safe_path, encoding=validation_result.encoding))
            
            # Build ParsedDocument with contracts adapter if available
            if self.contracts_adapter:
                # Get format-specific metadata from parser
                format_specific = self._get_format_specific_metadata(parser, validation_result.mime_type)
                parsed_doc = self.contracts_adapter.parse_file(
                    safe_path, validation_result, iter(records), format_specific
                )
                # Store unified records for later contracts output
                self._processed_unified_records.extend(parsed_doc.records)
            
            # Write records to output (legacy format)
            if records:
                self.records_gen.write_records(iter(records), filename=f"{file_path.stem}.jsonl")
            
            # Update result
            result.total_records += len(records)
            result.processed_files.append(str(file_path))
            
            # Update report generator stats (legacy)
            file_size = safe_path.stat().st_size
            self.report_gen.add_file_processed(
                file_path=file_path,
                format=validation_result.mime_type,
                record_count=len(records),
                size_bytes=file_size
            )
            
            # Track for contracts adapter
            if self.contracts_adapter:
                import hashlib
                sha256 = hashlib.sha256()
                with safe_path.open("rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        sha256.update(chunk)
                self.contracts_adapter.add_processed_file({
                    "sha256": sha256.hexdigest(),
                    "output_path": f"sanitized/{file_path.stem}.jsonl",
                    "duration_ms": 0,  # Could track actual duration
                    "peak_memory_mb": 0,
                    "record_count": len(records),
                    "identifiers_detected": 0,
                    "records_linked": 0,
                    "records_generalized": 0,
                    "records_suppressed": 0,
                    "records_quarantined": 0,
                })
            
            logger.info("ingestion.file_processed", 
                       path=str(file_path),
                       records=len(records),
                       mime_type=validation_result.mime_type)
            
        except Exception as e:
            logger.error("ingestion.file_failed", path=str(file_path), error=str(e))
            # Try to quarantine
            try:
                self.quarantine.quarantine(file_path, reason=f"Exception: {str(e)}")
            except Exception:
                pass
            result.failed_files.append(str(file_path))
            result.errors.append({"file": str(file_path), "error": str(e)})
            self.report_gen.add_file_failed(file_path, str(e))
            # Track for contracts adapter
            if self.contracts_adapter:
                import hashlib
                sha256 = hashlib.sha256()
                with file_path.open("rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        sha256.update(chunk)
                self.contracts_adapter.add_failed_file({
                    "sha256": sha256.hexdigest(),
                    "error": str(e),
                })
            raise
    
    def _get_format_specific_metadata(self, parser: Any, mime_type: str) -> dict[str, Any]:
        """Extract format-specific metadata from parser."""
        metadata = {}
        if hasattr(parser, 'get_metadata'):
            metadata = parser.get_metadata()
        elif hasattr(parser, 'headers'):  # CSV parser
            metadata["headers"] = parser.headers
        elif hasattr(parser, 'bundle_type'):  # FHIR parser
            metadata["bundle_type"] = parser.bundle_type
        return metadata