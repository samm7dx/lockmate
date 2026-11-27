"""
LOCKMATE — Phase 7: PII-Safe Structured Logging

Implements logging that never exposes PII:
- Never logs patient names, phone numbers, Aadhaar numbers
- Never logs original record text
- Never logs raw exception payloads containing PII
- Never logs cryptographic secrets
- Includes useful operational information (stage, counts, status, timing)
"""

from __future__ import annotations

import json
import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union
from pathlib import Path

from ..utils.logging import get_logger

logger = get_logger("security.safe_logging")


# PII patterns that should never appear in logs
PII_PATTERNS = [
    # Aadhaar: 12 digits with optional spaces/hyphens
    (re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'), "[AADHAAR]"),
    # PAN: 5 letters, 4 digits, 1 letter
    (re.compile(r'\b[A-Z]{5}\d{4}[A-Z]\b'), "[PAN]"),
    # ABHA: 14 digits
    (re.compile(r'\b\d{14}\b'), "[ABHA]"),
    # Phone numbers (Indian): 10 digits, optionally with +91
    (re.compile(r'(?:\+91[\s-]?)?[6-9]\d{9}\b'), "[PHONE]"),
    # Email addresses
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), "[EMAIL]"),
    # Credit card-like patterns
    (re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'), "[CARD]"),
    # Potential names (capitalized words, but be careful)
    # We'll handle names through explicit sanitization rather than regex
]

# Fields that should never be logged
FORBIDDEN_FIELDS = {
    "name", "patient_name", "doctor_name", "relative_name",
    "phone", "mobile", "telephone",
    "aadhaar", "aadhar", "uid",
    "abha", "abha_id",
    "pan", "pan_number",
    "email", "email_id",
    "address", "full_address",
    "date_of_birth", "dob", "birth_date",
    "mrn", "uhid", "patient_id",
    "insurance", "policy_number",
    "password", "secret", "key", "token",
    "raw_text", "original_text", "normalized_text",
}


@dataclass
class LogSanitizer:
    """Sanitizes log data to remove PII."""
    
    # Custom patterns to add
    custom_patterns: List[tuple] = field(default_factory=list)
    # Fields to always redact
    forbidden_fields: Set[str] = field(default_factory=lambda: FORBIDDEN_FIELDS.copy())
    # Maximum string length in logs
    max_string_length: int = 500
    # Whether to hash identifiers instead of redacting
    hash_identifiers: bool = False
    
    def __post_init__(self):
        self._all_patterns = PII_PATTERNS + self.custom_patterns
    
    def sanitize(self, data: Any) -> Any:
        """
        Recursively sanitize data structure.
        
        Args:
            data: Any JSON-serializable data
            
        Returns:
            Sanitized copy
        """
        if data is None:
            return None
        elif isinstance(data, str):
            return self._sanitize_string(data)
        elif isinstance(data, dict):
            return self._sanitize_dict(data)
        elif isinstance(data, (list, tuple)):
            return [self.sanitize(item) for item in data]
        elif isinstance(data, (int, float, bool)):
            return data
        else:
            # Convert to string and sanitize
            return self._sanitize_string(str(data))
    
    def _sanitize_string(self, text: str) -> str:
        """Sanitize a single string."""
        if not text:
            return text
        
        # Apply regex patterns
        for pattern, replacement in self._all_patterns:
            text = pattern.sub(replacement, text)
        
        # Truncate long strings
        if len(text) > self.max_string_length:
            text = text[:self.max_string_length] + "...[TRUNCATED]"
        
        return text
    
    def _sanitize_dict(self, d: Dict) -> Dict:
        """Sanitize a dictionary, redacting forbidden fields."""
        result = {}
        for key, value in d.items():
            key_lower = key.lower()
            
            # Check if field is forbidden
            if any(forbidden in key_lower for forbidden in self.forbidden_fields):
                result[key] = "[REDACTED]"
            elif key_lower in ("secret", "password", "key", "token"):
                result[key] = "[REDACTED]"
            else:
                result[key] = self.sanitize(value)
        return result
    
    def sanitize_exception(self, exc: Exception) -> Dict[str, Any]:
        """
        Sanitize an exception for logging.
        
        Args:
            exc: Exception to sanitize
            
        Returns:
            Dictionary with safe exception info
        """
        return {
            "type": type(exc).__name__,
            "message": self._sanitize_string(str(exc)),
            # Never include traceback in production logs (PII risk)
        }


# Global sanitizer instance
_default_sanitizer = LogSanitizer()


def sanitize_log_data(data: Any) -> Any:
    """Convenience function to sanitize log data."""
    return _default_sanitizer.sanitize(data)


def sanitize_exception(exc: Exception) -> Dict[str, Any]:
    """Convenience function to sanitize an exception."""
    return _default_sanitizer.sanitize_exception(exc)


class SafeLogger:
    """
    PII-safe structured logger.
    
    Wraps standard logger to automatically sanitize all log data.
    """
    
    def __init__(self, name: str, sanitizer: Optional[LogSanitizer] = None):
        self.logger = logging.getLogger(name)
        self.sanitizer = sanitizer or _default_sanitizer
    
    def _log(self, level: int, event: str, **kwargs):
        """Internal log method with sanitization."""
        # Sanitize all keyword arguments
        safe_kwargs = {k: self.sanitizer.sanitize(v) for k, v in kwargs.items()}
        
        # Add standard fields
        safe_kwargs["event"] = event
        safe_kwargs["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        # Log as structured JSON
        self.logger.log(level, json.dumps(safe_kwargs, separators=(',', ':')))
    
    def debug(self, event: str, **kwargs):
        self._log(logging.DEBUG, event, **kwargs)
    
    def info(self, event: str, **kwargs):
        self._log(logging.INFO, event, **kwargs)
    
    def warning(self, event: str, **kwargs):
        self._log(logging.WARNING, event, **kwargs)
    
    def error(self, event: str, **kwargs):
        self._log(logging.ERROR, event, **kwargs)
    
    def critical(self, event: str, **kwargs):
        self._log(logging.CRITICAL, event, **kwargs)
    
    def exception(self, event: str, exc: Exception, **kwargs):
        """Log an exception with sanitized details."""
        safe_kwargs = {k: self.sanitizer.sanitize(v) for k, v in kwargs.items()}
        safe_kwargs["event"] = event
        safe_kwargs["timestamp"] = datetime.utcnow().isoformat() + "Z"
        safe_kwargs["exception"] = self.sanitizer.sanitize_exception(exc)
        self.logger.log(logging.ERROR, json.dumps(safe_kwargs, separators=(',', ':')))


def setup_safe_logging(
    level: str = "INFO",
    format: str = "json",
    output: Optional[Path] = None,
    sanitizer: Optional[LogSanitizer] = None
) -> SafeLogger:
    """
    Set up PII-safe logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format: Log format ("json" or "text")
        output: Optional file path for log output
        sanitizer: Custom LogSanitizer instance
        
    Returns:
        Configured SafeLogger for the root
    """
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create handler
    if output:
        handler = logging.FileHandler(output)
    else:
        handler = logging.StreamHandler(sys.stdout)
    
    # Set formatter
    if format == "json":
        formatter = logging.Formatter('%(message)s')
    else:
        formatter = logging.Formatter(
            '%(asctime)s %(levelname)s %(name)s: %(message)s'
        )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # Return safe logger for root
    return SafeLogger("", sanitizer or _default_sanitizer)


def create_module_logger(module_name: str) -> SafeLogger:
    """Create a safe logger for a specific module."""
    return SafeLogger(module_name)


# Context manager for temporary log level changes
class LogLevelContext:
    """Temporarily change log level."""
    
    def __init__(self, logger: logging.Logger, level: int):
        self.logger = logger
        self.new_level = level
        self.old_level = logger.level
    
    def __enter__(self):
        self.logger.setLevel(self.new_level)
        return self
    
    def __exit__(self, *args):
        self.logger.setLevel(self.old_level)