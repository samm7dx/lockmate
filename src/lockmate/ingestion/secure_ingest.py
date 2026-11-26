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
    RecordsGenerator, 
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
        self.quarantine = QuarantineManager(path=config.quarantine_dir)
        
        # Initialize generators
        self.report_gen = ReportGenerator(output_dir=config.output_dir)
        self.records_gen = RecordsGenerator(output_dir=config.output_dir)

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
        # Implementation will follow after interface agreement
        raise NotImplementedError()