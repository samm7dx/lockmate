"""
LOCKMATE — Phase 7: PII-Safe Exception Handling

Implements sanitized exception handling:
- Never exposes PII in error messages
- Never includes raw exception payloads containing PII
- Provides useful error categorization for debugging
- Ensures cryptographic secrets never appear in errors
"""

from __future__ import annotations

import logging
import traceback
from dataclasses import dataclass
from typing import Any, Dict, Optional, Type
from enum import Enum

from ..utils.logging import get_logger

logger = get_logger("security.safe_errors")


class ErrorCategory(Enum):
    """Categories of errors for handling and reporting."""
    VALIDATION = "validation"           # Input validation errors
    PARSE = "parse"                     # File parsing errors
    RESOURCE = "resource"               # Resource limits exceeded
    CRYPTO = "crypto"                   # Cryptographic failures
    IO = "io"                          # I/O errors
    CONFIG = "config"                   # Configuration errors
    INTERNAL = "internal"               # Internal logic errors
    QUARANTINE = "quarantine"           # Quarantine-triggered
    UNKNOWN = "unknown"                 # Unclassified


@dataclass
class SafeErrorInfo:
    """PII-safe error information for logging and reporting."""
    category: ErrorCategory
    error_type: str
    error_message: str  # Sanitized message
    context: Dict[str, Any]  # Sanitized context
    timestamp: str
    # No traceback, no raw exception, no PII


class PIISafeError(Exception):
    """
    Base exception class that ensures PII-safe error messages.
    
    All LOCKMATE exceptions should inherit from this.
    """
    
    def __init__(
        self, 
        message: str, 
        category: ErrorCategory = ErrorCategory.INTERNAL,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(message)
        # Sanitize the message immediately
        self.safe_message = self._sanitize_message(message)
        self.category = category
        self.context = context or {}
        self.original_exception = original_exception
    
    def _sanitize_message(self, message: str) -> str:
        """Sanitize error message to remove potential PII."""
        import re
        
        # Aadhaar
        message = re.sub(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[AADHAAR]', message)
        # PAN
        message = re.sub(r'\b[A-Z]{5}\d{4}[A-Z]\b', '[PAN]', message)
        # Phone
        message = re.sub(r'(?:\+91[\s-]?)?[6-9]\d{9}\b', '[PHONE]', message)
        # Email
        message = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', message)
        # File paths that might contain names
        message = re.sub(r'/home/\w+/', '/home/[USER]/', message)
        message = re.sub(r'C:\\\\Users\\\\\w+', r'C:\\Users\\[USER]', message)
        
        return message
    
    def to_safe_info(self) -> SafeErrorInfo:
        """Convert to safe error info for logging."""
        from datetime import datetime
        # Sanitize context before including in safe info
        safe_context = SafeErrorHandler._sanitize_context_static(self.context)
        return SafeErrorInfo(
            category=self.category,
            error_type=type(self).__name__,
            error_message=self.safe_message,
            context=safe_context,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )


class ValidationError(PIISafeError):
    """Input validation error."""
    def __init__(self, message: str, context: Optional[Dict] = None, **kwargs):
        super().__init__(message, ErrorCategory.VALIDATION, context, **kwargs)


class ParseError(PIISafeError):
    """File parsing error."""
    def __init__(self, message: str, context: Optional[Dict] = None, **kwargs):
        super().__init__(message, ErrorCategory.PARSE, context, **kwargs)


class ResourceLimitError(PIISafeError):
    """Resource limit exceeded."""
    def __init__(self, message: str, context: Optional[Dict] = None, **kwargs):
        super().__init__(message, ErrorCategory.RESOURCE, context, **kwargs)


class CryptoError(PIISafeError):
    """Cryptographic operation failure."""
    def __init__(self, message: str, context: Optional[Dict] = None, **kwargs):
        super().__init__(message, ErrorCategory.CRYPTO, context, **kwargs)


class QuarantineError(PIISafeError):
    """File/record quarantined."""
    def __init__(self, message: str, context: Optional[Dict] = None, **kwargs):
        super().__init__(message, ErrorCategory.QUARANTINE, context, **kwargs)


class SafeErrorHandler:
    """
    Handles exceptions in a PII-safe manner.
    
    Provides methods to catch, sanitize, and log exceptions
    without exposing sensitive data.
    """
    
    def __init__(self, logger_name: str = "security.errors"):
        self.logger = logging.getLogger(logger_name)
    
    def handle(
        self, 
        exc: Exception, 
        context: Optional[Dict[str, Any]] = None,
        reraise: bool = False,
        default_category: ErrorCategory = ErrorCategory.UNKNOWN
    ) -> SafeErrorInfo:
        """
        Handle an exception safely.
        
        Args:
            exc: The exception to handle
            context: Additional context (will be sanitized)
            reraise: Whether to re-raise the exception
            default_category: Default category if not a PIISafeError
            
        Returns:
            SafeErrorInfo for logging
        """
        # Determine category and safe message
        if isinstance(exc, PIISafeError):
            safe_info = exc.to_safe_info()
            if context:
                safe_info.context.update(self._sanitize_context(context))
        else:
            # Wrap unknown exceptions
            safe_info = SafeErrorInfo(
                category=default_category,
                error_type=type(exc).__name__,
                error_message=self._sanitize_message(str(exc)),
                context=self._sanitize_context(context or {}),
                timestamp=self._get_timestamp()
            )
        
        # Log safely (no traceback in production)
        self.logger.error(
            "exception_handled",
            extra=safe_info.__dict__
        )
        
        # In debug mode, log traceback to separate debug logger
        if logger.isEnabledFor(logging.DEBUG):
            debug_logger = logging.getLogger("security.errors.debug")
            debug_logger.debug(
                "exception_traceback",
                extra={
                    "error_type": safe_info.error_type,
                    "traceback": traceback.format_exc()
                }
            )
        
        if reraise:
            raise
        
        return safe_info
    
    def handle_with_fallback(
        self,
        exc: Exception,
        fallback_message: str,
        context: Optional[Dict[str, Any]] = None,
        reraise_as: Optional[Type[PIISafeError]] = None
    ) -> PIISafeError:
        """
        Handle exception and return a safe fallback exception.
        
        Args:
            exc: Original exception
            fallback_message: Safe message for the fallback exception
            context: Additional context
            reraise_as: Exception type to re-raise as
            
        Returns:
            PIISafeError instance
        """
        safe_info = self.handle(exc, context, reraise=False)
        
        if reraise_as:
            new_exc = reraise_as(fallback_message, context=safe_info.context, original_exception=exc)
            raise new_exc from exc
        
        return PIISafeError(fallback_message, safe_info.category, safe_info.context, exc)
    
    def _sanitize_message(self, message: str) -> str:
        """Sanitize error message to remove potential PII."""
        # Remove common PII patterns
        import re
        
        # Aadhaar
        message = re.sub(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[AADHAAR]', message)
        # PAN
        message = re.sub(r'\b[A-Z]{5}\d{4}[A-Z]\b', '[PAN]', message)
        # Phone
        message = re.sub(r'(?:\+91[\s-]?)?[6-9]\d{9}\b', '[PHONE]', message)
        # Email
        message = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', message)
        # File paths that might contain names
        message = re.sub(r'/home/\w+/', '/home/[USER]/', message)
        message = re.sub(r'C:\\\\Users\\\\\w+', r'C:\\Users\\[USER]', message)
        
        return message
    
    @staticmethod
    def _sanitize_context_static(context: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize context dictionary (static method for use by PIISafeError)."""
        forbidden = {
            "name", "patient", "phone", "aadhaar", "abha", "pan", "email",
            "address", "dob", "secret", "key", "password", "token",
            "raw_text", "original_text", "normalized_text"
        }
        
        result = {}
        for key, value in context.items():
            key_lower = key.lower()
            if any(f in key_lower for f in forbidden):
                result[key] = "[REDACTED]"
            elif isinstance(value, str):
                # Use a temporary handler instance for message sanitization
                temp_handler = SafeErrorHandler()
                result[key] = temp_handler._sanitize_message(value)
            elif isinstance(value, dict):
                result[key] = SafeErrorHandler._sanitize_context_static(value)
            elif isinstance(value, (list, tuple)):
                temp_handler = SafeErrorHandler()
                result[key] = [
                    temp_handler._sanitize_message(v) if isinstance(v, str) else v
                    for v in value
                ]
            else:
                result[key] = value
        return result

    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize context dictionary (instance method)."""
        return self._sanitize_context_static(context)
    
    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"


# Global error handler instance
_default_error_handler = SafeErrorHandler()


def sanitize_exception(exc: Exception) -> Dict[str, Any]:
    """
    Convert an exception to a safe dictionary for logging.
    
    Args:
        exc: Exception to sanitize
        
    Returns:
        Dictionary with safe error info
    """
    if isinstance(exc, PIISafeError):
        return exc.to_safe_info().__dict__
    
    return {
        "category": ErrorCategory.UNKNOWN.value,
        "error_type": type(exc).__name__,
        "message": _default_error_handler._sanitize_message(str(exc)),
        "context": {},
        "timestamp": _default_error_handler._get_timestamp()
    }


def wrap_exception(
    exc: Exception,
    message: str,
    category: ErrorCategory = ErrorCategory.INTERNAL,
    context: Optional[Dict[str, Any]] = None
) -> PIISafeError:
    """
    Wrap an exception in a PIISafeError.
    
    Args:
        exc: Original exception
        message: Safe error message
        category: Error category
        context: Additional context
        
    Returns:
        PIISafeError wrapping the original
    """
    return PIISafeError(message, category, context, exc)


# Decorator for safe function execution
def safe_execute(
    category: ErrorCategory = ErrorCategory.INTERNAL,
    fallback_message: str = "Operation failed",
    reraise: bool = False,
    handler: Optional[SafeErrorHandler] = None
):
    """
    Decorator to execute a function with safe error handling.
    
    Usage:
        @safe_execute(category=ErrorCategory.PARSE, fallback_message="Failed to parse file")
        def parse_file(path):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            h = handler or _default_error_handler
            try:
                return func(*args, **kwargs)
            except Exception as e:
                return h.handle_with_fallback(
                    e, fallback_message, 
                    context={"function": func.__name__},
                    reraise_as=PIISafeError if reraise else None
                )
        return wrapper
    return decorator