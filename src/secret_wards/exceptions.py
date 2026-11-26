"""
LOCKMATE — Custom Exception Hierarchy
"""

from __future__ import annotations
from typing import Optional


class LockmateError(Exception):
    """Base exception for all LOCKMATE errors."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(LockmateError):
    """Configuration-related errors."""
    pass


class ValidationError(LockmateError):
    """Input validation errors."""
    pass


class IntakeError(LockmateError):
    """File intake and parsing errors."""
    pass


class ParseError(IntakeError):
    """Parsing errors for specific formats."""
    def __init__(self, message: str, file_path: str, format_type: str, details: Optional[dict] = None):
        super().__init__(message, details)
        self.file_path = file_path
        self.format_type = format_type


class EncodingError(IntakeError):
    """Encoding detection/decoding errors."""
    pass


class ResourceLimitError(IntakeError):
    """Resource limit exceeded (file size, nesting, etc.)."""
    pass


class QuarantineError(LockmateError):
    """Quarantine-related errors."""
    pass


class QuarantineAllError(LockmateError):
    """Top-level error triggering quarantine of all remaining files."""
    pass


class DetectionError(LockmateError):
    """PII detection errors."""
    pass


class LinkageError(LockmateError):
    """Identity resolution/linkage errors."""
    pass


class PseudonymError(LockmateError):
    """Pseudonymization errors."""
    pass


class CryptoError(LockmateError):
    """Cryptographic operations errors."""
    pass


class PrivacyTransformError(LockmateError):
    """Privacy transformation errors."""
    pass


class SerializationError(LockmateError):
    """Output serialization errors."""
    pass


class SecurityGateError(LockmateError):
    """Output security gate failures."""
    pass


class ReportGenerationError(LockmateError):
    """Report generation errors."""
    pass


class PipelineError(LockmateError):
    """General pipeline orchestration errors."""
    pass


class UnsupportedFormatError(ParseError):
    """Unsupported file format."""
    pass


class PathTraversalError(IntakeError):
    """Path traversal attempt detected."""
    pass


class DecompressionBombError(IntakeError):
    """Decompression bomb detected."""
    pass


class DeterminismError(LockmateError):
    """Determinism verification failure."""
    pass


class SecretRotationError(LockmateError):
    """Secret rotation verification failure."""
    pass


class CanaryLeakageError(LockmateError):
    """Canary string detected in output."""
    pass


class MedicalCorruptionError(LockmateError):
    """Clinical value corrupted during sanitization."""
    pass


class FalseMergeError(LockmateError):
    """False patient merge detected."""
    pass