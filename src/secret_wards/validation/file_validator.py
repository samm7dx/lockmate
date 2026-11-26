"""
LOCKMATE — File Validation and Encoding Checks

Validates file MIME type, encoding, and basic structure.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union, Optional, Set
from dataclasses import dataclass

from charset_normalizer import from_path

from ..utils.logging import get_logger

# Try to import libmagic (python-magic). May not be available on all platforms
# (especially Windows without libmagic installed). We fall back to extension-based
# MIME detection in that case.
try:
    import magic as _magic
    _MAGIC_AVAILABLE = True
except ImportError:
    _magic = None
    _MAGIC_AVAILABLE = False

logger = get_logger("validation.file_validator")

# Fallback MIME types based on file extension (best-effort)
_EXTENSION_MIME_TYPES: dict[str, str] = {
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".json": "application/json",
    ".ndjson": "application/x-ndjson",
    ".jsonl": "application/x-ndjson",
    ".xml": "application/xml",
    ".html": "text/html",
    ".htm": "text/html",
    ".yaml": "application/x-yaml",
    ".yml": "application/x-yaml",
    ".md": "text/markdown",
    ".log": "text/plain",
    ".fhir": "application/fhir+json",
    ".fhira": "application/fhir+json",
}


@dataclass
class ValidationConfig:
    """Configuration for file validation."""
    allowed_mime_types: Set[str] = frozenset({
        "text/plain",
        "text/csv",
        "text/tab-separated-values",
        "application/json",
        "application/x-ndjson",
        "application/fhir+json",
        "application/xml",
        "text/xml",
        "text/markdown",
        "application/x-yaml",
    })
    require_utf8: bool = False
    max_encoding_confidence: float = 0.9
    use_magic: bool = True


@dataclass
class ValidationResult:
    """Result of file validation."""
    is_valid: bool
    reason: str
    mime_type: str
    encoding: str
    encoding_confidence: float
    details: dict


class FileValidator:
    """Validates file MIME type, encoding, and basic structure."""
    
    def __init__(self, config: Optional[ValidationConfig] = None) -> None:
        self.config = config or ValidationConfig()
        self._magic = None
        if self.config.use_magic and _MAGIC_AVAILABLE:
            try:
                import magic as _magic
                self._magic = _magic.Magic(mime=True)
            except Exception as e:
                logger.warning("file_validator.magic_init_failed", error=str(e))
                self._magic = None
    
    def detect_mime_type(self, path: Path) -> str:
        """
        Detect MIME type of a file.
        
        Uses libmagic if available, otherwise falls back to extension-based detection.
        
        Args:
            path: Path to file
            
        Returns:
            Detected MIME type string
        """
        # Try libmagic first
        try:
            import magic as _magic
            self._magic = _magic.Magic(mime=True)
            mime = self._magic.from_file(str(path))
            if mime and mime != "inode/x-empty":
                return mime
        except Exception as e:
            logger.debug("file_validator.magic_failed", path=str(path), error=str(e))
        
        # Fallback to extension-based detection
        mime = _EXTENSION_MIME_TYPES.get(path.suffix.lower(), "application/octet-stream")
        logger.debug("file_validator.mime_extension_fallback", path=str(path), mime=mime)
        return mime
    
    def validate(self, path: Union[str, Path]) -> ValidationResult:
        """
        Validate a file's MIME type and encoding.
        
        Args:
            path: Path to file
            
        Returns:
            ValidationResult with validation outcome and details
        """
        path = Path(path)
        
        # 1. Check file exists and is readable
        if not path.exists():
            return ValidationResult(
                is_valid=False,
                reason="File does not exist",
                mime_type="",
                encoding="",
                encoding_confidence=0.0,
                details={"error": "not_found"}
            )
        
        if not path.is_file():
            return ValidationResult(
                is_valid=False,
                reason="Path is not a regular file",
                mime_type="",
                encoding="",
                encoding_confidence=0.0,
                details={"error": "not_a_file"}
            )
        
        # 2. Detect MIME type
        mime_type = self.detect_mime_type(path)
        
        # 3. Check if MIME type is allowed
        if mime_type not in self.config.allowed_mime_types:
            logger.warning(
                "validation.mime_rejected",
                extra={
                    "path": str(path),
                    "mime_type": mime_type,
                    "allowed": list(self.config.allowed_mime_types)
                }
            )
            return ValidationResult(
                is_valid=False,
                reason=f"MIME type not allowed: {mime_type}",
                mime_type=mime_type,
                encoding="",
                encoding_confidence=0.0,
                details={"error": "mime_not_allowed"}
            )
        
        # 4. Detect encoding
        try:
            result = from_path(str(path))
            best = result.best()
            
            if best is None:
                encoding = "unknown"
                confidence = 0.0
            else:
                encoding = best.encoding or "unknown"
                # Use coherence as confidence proxy (charset-normalizer 3.x API)
                confidence = getattr(best, 'coherence', 0.0) or 0.0
                
        except Exception as e:
            logger.error("validation.encoding_failed", extra={"path": str(path), "error": str(e)})
            encoding = "unknown"
            confidence = 0.0
        
        # 5. Check encoding if required
        if self.config.require_utf8 and encoding.lower() not in ("utf-8", "ascii", "utf-8-sig"):
            logger.warning(
                "validation.encoding_not_utf8",
                extra={"path": str(path), "encoding": encoding, "confidence": confidence}
            )
            if confidence > self.config.max_encoding_confidence:
                return ValidationResult(
                    is_valid=False,
                    reason=f"Encoding not UTF-8: {encoding} (confidence: {confidence:.2f})",
                    mime_type=mime_type,
                    encoding=encoding,
                    encoding_confidence=confidence,
                    details={"error": "encoding_not_utf8"}
                )
        
        return ValidationResult(
            is_valid=True,
            reason="Valid",
            mime_type=mime_type,
            encoding=encoding,
            encoding_confidence=confidence,
            details={}
        )