from pathlib import Path
from typing import Any, Iterator, Self
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
    ValidationConfig
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
        
        # Write final report
        self.report_gen.write()
        
        logger.info("ingestion.completed", 
                   job_id=str(result.job_id),
                   total_records=result.total_records,
                   processed=len(result.processed_files),
                   failed=len(result.failed_files),
                   quarantined=len(result.quarantined_files))
        
        return result
    
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
                return
            
            # 5. Parsing
            parser = self._get_parser(validation_result.mime_type)
            records = list(parser.parse(safe_path, encoding=validation_result.encoding))
            
            # Write records to output
            if records:
                self.records_gen.write_records(iter(records), filename=f"{file_path.stem}.jsonl")
            
            # Update result
            result.total_records += len(records)
            result.processed_files.append(str(file_path))
            
            # Update report generator stats
            file_size = safe_path.stat().st_size
            self.report_gen.add_file_processed(
                file_path=file_path,
                format=validation_result.mime_type,
                record_count=len(records),
                size_bytes=file_size
            )
            
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
            raise