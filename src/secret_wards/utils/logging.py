"""
LOCKMATE — PII-Scrubbed Structured Logging
"""

from __future__ import annotations

import json
import logging
import sys
import re
from typing import Any, Dict, Optional
from pathlib import Path

from ..contracts import PIIType


class PIIScrubbingFormatter(logging.Formatter):
    """
    JSON formatter that scrubs PII from log messages.
    
    Uses detection patterns to identify and redact potential PII
    in log messages before output.
    """
    
    # Patterns that might indicate PII in logs
    PII_PATTERNS = [
        # Phone numbers (Indian)
        (re.compile(r'\b(?:\+91|0)?[6-9]\d{9}\b'), "[PHONE]"),
        # Aadhaar (12 digits)
        (re.compile(r'\b\d{12}\b'), "[AADHAAR]"),
        # PAN
        (re.compile(r'\b[A-Z]{5}\d{4}[A-Z]\b'), "[PAN]"),
        # Email
        (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), "[EMAIL]"),
        # 6-digit PIN codes
        (re.compile(r'\b\d{6}\b'), "[PIN]"),
        # Common name patterns (conservative)
        (re.compile(r'\b(?:Mr|Mrs|Ms|Dr|Prof|S/o|D/o|W/o|C/O)\s+[A-Z][a-z]+\b'), "[NAME]"),
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def format(self, record: logging.LogRecord) -> str:
        # Build base log dict
        log_dict = self._log_dict(record)
        
        # Add extra fields if present
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "msg", "name", "pathname", "process",
                "processName", "relativeCreated", "thread", "threadName",
                "exc_info", "exc_text", "stack_info", "getMessage"
            }:
                log_dict[key] = self._scrub_value(value)
        
        # Add exception info if present
        if record.exc_info:
            log_dict["exception"] = self._scrub_message(
                self.formatException(record.exc_info)
            )
        
        return json.dumps(log_dict, separators=(',', ':'), ensure_ascii=False)
    
    def _scrub_message(self, message: str) -> str:
        """Scrub PII from a log message."""
        scrubbed = message
        for pattern, replacement in self.PII_PATTERNS:
            scrubbed = pattern.sub(replacement, scrubbed)
        return scrubbed
    
    def _scrub_value(self, value: Any) -> Any:
        """Recursively scrub PII from any value."""
        if isinstance(value, str):
            return self._scrub_message(value)
        elif isinstance(value, dict):
            return {k: self._scrub_value(v) for k, v in value.items()}
        elif isinstance(value, (list, tuple)):
            return [self._scrub_value(v) for v in value]
        else:
            return value
    
    def _log_dict(self, record: logging.LogRecord) -> dict:
        """Convert log record to dict for JSON output."""
        return {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": self._scrub_message(record.getMessage()),
        }
    
    
def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    enable_console: bool = True
) -> logging.Logger:
    """
    Setup structured logging with PII scrubbing.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        enable_console: Whether to log to console
        
    Returns:
        Configured root logger
    """
    logger = logging.getLogger("lockmate")
    logger.setLevel(getattr(logging, level.upper()))
    logger.handlers.clear()
    
    formatter = PIIScrubbingFormatter()
    
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger for a specific module."""
    return logging.getLogger(f"lockmate.{name}")


class LoggerAdapter:
    """
    Logger adapter that supports keyword arguments for structured logging.
    
    Usage:
        logger = LoggerAdapter(get_logger("module"))
        logger.info("message", key=value)  # Automatically uses extra=...
    """
    
    def __init__(self, logger: logging.Logger):
        self._logger = logger
    
    def _log(self, level: int, msg: str, **kwargs) -> None:
        if kwargs:
            self._logger.log(level, msg, extra=kwargs)
        else:
            self._logger.log(level, msg)
    
    def debug(self, msg: str, **kwargs) -> None:
        self._log(logging.DEBUG, msg, **kwargs)
    
    def info(self, msg: str, **kwargs) -> None:
        self._log(logging.INFO, msg, **kwargs)
    
    def warning(self, msg: str, **kwargs) -> None:
        self._log(logging.WARNING, msg, **kwargs)
    
    def error(self, msg: str, **kwargs) -> None:
        self._log(logging.ERROR, msg, **kwargs)
    
    def critical(self, msg: str, **kwargs) -> None:
        self._log(logging.CRITICAL, msg, **kwargs)
    
    def warning(self, msg: str, **kwargs) -> None:
        self._log(logging.WARNING, msg, **kwargs)
    
    def exception(self, msg: str, **kwargs) -> None:
        self._logger.exception(msg, **kwargs)
    
    def log(self, level: int, msg: str, **kwargs) -> None:
        self._log(level, msg, **kwargs)
    
    # Delegate other attributes to the underlying logger
    def __getattr__(self, name: str):
        return getattr(self._logger, name)


def get_logger_adapter(name: str) -> LoggerAdapter:
    """Get a logger adapter that supports keyword arguments."""
    return LoggerAdapter(get_logger(name))


def log_with_extra(logger: logging.Logger, level: int, msg: str, **kwargs) -> None:
    """
    Log a message with extra fields using the 'extra' parameter.
    
    Usage:
        log_with_extra(logger, logging.INFO, "pipeline_started", input_dir="/path", output_dir="/out")
    """
    if kwargs:
        logger.log(level, msg, extra=kwargs)
    else:
        logger.log(level, msg)