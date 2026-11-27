"""
LOCKMATE — Phase 7: Security Hardening, Reliability & Performance

This module implements security and operational foundations:
- Cryptographic key management
- Intermediate data protection (encryption at rest)
- PII-safe logging and error handling
- Export security controls
- Offline execution verification
- Performance and reliability measurement
- Reproducibility verification
"""

from .key_manager import KeyManager, KeyPurpose, derive_key
from .encryption import encrypt_data, decrypt_data, EncryptedData, TempFileEncryption
from .safe_logging import SafeLogger, setup_safe_logging, sanitize_log_data
from .safe_errors import SafeErrorHandler, sanitize_exception, PIISafeError
from .export_hardening import ExportHardener, OutputGate, CanaryChecker

__all__ = [
    "KeyManager",
    "KeyPurpose",
    "derive_key",
    "encrypt_data",
    "decrypt_data",
    "EncryptedData",
    "TempFileEncryption",
    "SafeLogger",
    "setup_safe_logging",
    "sanitize_log_data",
    "SafeErrorHandler",
    "sanitize_exception",
    "PIISafeError",
    "ExportHardener",
    "OutputGate",
    "CanaryChecker",
]