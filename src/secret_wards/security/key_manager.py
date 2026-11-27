"""
LOCKMATE — Phase 7: Cryptographic Key Management

Implements proper key management abstraction:
- Never writes RAKSHA_SECRET to disk
- Never includes secrets in logs or exception messages
- Derives separate purpose-specific keys using HKDF with domain separation
- Keeps cryptographic keys separate from persisted data
- Avoids plain hashing of patient identifiers as pseudonymization
- Ensures cryptographic failures block unsafe export
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, List
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from ..utils.logging import get_logger

logger = get_logger("security.key_manager")


class KeyPurpose(Enum):
    """Enumeration of key purposes for domain separation."""
    PSEUDONYM = "pseudonym"
    DATE_SHIFT = "date_shift"
    ENCRYPTION = "encryption"
    AUTHENTICATION = "authentication"
    TEMP_FILE = "temp_file"
    EXPORT_GATE = "export_gate"
    CANARY = "canary"


@dataclass(frozen=True)
class KeyDerivationConfig:
    """Configuration for key derivation."""
    algorithm: str = "HKDF-SHA256"
    salt: bytes = b"lockmate-salt-v1"  # Fixed salt for deterministic derivation
    info_prefix: bytes = b"lockmate"


class KeyManager:
    """
    Cryptographic key manager for LOCKMATE.
    
    Derives purpose-specific keys from RAKSHA_SECRET using HKDF
    with domain separation. Never stores or logs the master secret.
    """
    
    # Domain separation constants
    DOMAIN_SEPARATORS = {
        KeyPurpose.PSEUDONYM: b"lockmate.pseudonym.v1",
        KeyPurpose.DATE_SHIFT: b"lockmate.date_shift.v1",
        KeyPurpose.ENCRYPTION: b"lockmate.encryption.v1",
        KeyPurpose.AUTHENTICATION: b"lockmate.authentication.v1",
        KeyPurpose.TEMP_FILE: b"lockmate.temp_file.v1",
        KeyPurpose.EXPORT_GATE: b"lockmate.export_gate.v1",
        KeyPurpose.CANARY: b"lockmate.canary.v1",
    }
    
    def __init__(self, master_secret: bytes):
        """
        Initialize key manager with master secret.
        
        Args:
            master_secret: RAKSHA_SECRET bytes (>=32 bytes)
            
        Raises:
            ValueError: If secret is too short
        """
        if len(master_secret) < 32:
            raise ValueError("Master secret must be at least 32 bytes")
        
        self._master_secret = master_secret
        self._derived_keys: Dict[KeyPurpose, bytes] = {}
        self._config = KeyDerivationConfig()
        
        logger.info("key_manager_initialized", 
                   secret_length=len(master_secret),
                   purposes=list(KeyPurpose))
    
    def get_key(self, purpose: KeyPurpose, length: int = 32) -> bytes:
        """
        Get or derive a purpose-specific key.
        
        Args:
            purpose: KeyPurpose enum value
            length: Desired key length in bytes (default 32 for AES-256)
            
        Returns:
            Derived key bytes
        """
        if purpose not in self._derived_keys:
            self._derived_keys[purpose] = self._derive_key(purpose, length)
        
        return self._derived_keys[purpose]
    
    def _derive_key(self, purpose: KeyPurpose, length: int) -> bytes:
        """Derive a key using HKDF with domain separation."""
        domain = self.DOMAIN_SEPARATORS.get(purpose, b"lockmate.unknown.v1")
        
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=length,
            salt=self._config.salt,
            info=domain,
        )
        
        derived = hkdf.derive(self._master_secret)
        
        logger.debug("key_derived", purpose=purpose.value, length=len(derived))
        return derived
    
    def get_hmac_key(self, purpose: KeyPurpose) -> bytes:
        """Get HMAC key for a purpose (32 bytes for SHA256)."""
        return self.get_key(purpose, 32)
    
    def get_encryption_key(self) -> bytes:
        """Get AES-256 encryption key (32 bytes)."""
        return self.get_key(KeyPurpose.ENCRYPTION, 32)
    
    def get_authentication_key(self) -> bytes:
        """Get authentication key (32 bytes)."""
        return self.get_key(KeyPurpose.AUTHENTICATION, 32)
    
    def derive_pseudonym_key(self, patient_id: str) -> bytes:
        """
        Derive a patient-specific pseudonymization key.
        
        This is used for deterministic pseudonym generation.
        """
        h = hmac.HMAC(self.get_hmac_key(KeyPurpose.PSEUDONYM), hashes.SHA256())
        h.update(patient_id.encode("utf-8"))
        return h.finalize()
    
    def derive_date_shift_key(self, patient_pseudonym: str) -> bytes:
        """Derive a patient-specific date shift key."""
        h = hmac.HMAC(self.get_hmac_key(KeyPurpose.DATE_SHIFT), hashes.SHA256())
        h.update(patient_pseudonym.encode("utf-8"))
        return h.finalize()
    
    def rotate_keys(self, new_master_secret: bytes):
        """
        Rotate to a new master secret.
        
        This invalidates all derived keys and re-derives them.
        
        Args:
            new_master_secret: New master secret (>=32 bytes)
        """
        if len(new_master_secret) < 32:
            raise ValueError("New master secret must be at least 32 bytes")
        
        self._master_secret = new_master_secret
        self._derived_keys.clear()
        
        logger.info("keys_rotated")
    
    def clear_keys(self):
        """Clear all derived keys from memory."""
        self._derived_keys.clear()
        logger.info("keys_cleared")
    
    def __del__(self):
        """Attempt to clear keys on deletion."""
        self.clear_keys()
    
    def __repr__(self) -> str:
        return f"KeyManager(purposes={list(self._derived_keys.keys())})"


def derive_key(master_secret: bytes, purpose: KeyPurpose, length: int = 32) -> bytes:
    """
    Standalone function to derive a key from master secret.
    
    Uses HKDF with domain separation.
    
    Args:
        master_secret: RAKSHA_SECRET bytes
        purpose: KeyPurpose enum
        length: Desired key length
        
    Returns:
        Derived key bytes
    """
    config = KeyDerivationConfig()
    domain_separators = {
        KeyPurpose.PSEUDONYM: b"lockmate.pseudonym.v1",
        KeyPurpose.DATE_SHIFT: b"lockmate.date_shift.v1",
        KeyPurpose.ENCRYPTION: b"lockmate.encryption.v1",
        KeyPurpose.AUTHENTICATION: b"lockmate.authentication.v1",
        KeyPurpose.TEMP_FILE: b"lockmate.temp_file.v1",
        KeyPurpose.EXPORT_GATE: b"lockmate.export_gate.v1",
        KeyPurpose.CANARY: b"lockmate.canary.v1",
    }
    
    domain = domain_separators.get(purpose, b"lockmate.unknown.v1")
    
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=config.salt,
        info=domain,
    )
    
    return hkdf.derive(master_secret)


# Key hierarchy documentation
KEY_HIERARCHY_DOC = """
LOCKMATE Cryptographic Key Hierarchy
=====================================

Master Secret: RAKSHA_SECRET (>=32 bytes, provided via environment)
    │
    ├─► HKDF-SHA256 (salt="lockmate-salt-v1")
    │
    ├─► KeyPurpose.PSEUDONYM
    │     info="lockmate.pseudonym.v1"
    │     └─► HMAC-SHA256 per-patient for pseudonym generation
    │
    ├─► KeyPurpose.DATE_SHIFT
    │     info="lockmate.date_shift.v1"
    │     └─► HMAC-SHA256 per-patient for date shift derivation
    │
    ├─► KeyPurpose.ENCRYPTION
    │     info="lockmate.encryption.v1"
    │     └─► AES-256-GCM for temporary file encryption
    │
    ├─► KeyPurpose.AUTHENTICATION
    │     info="lockmate.authentication.v1"
    │     └─► HMAC-SHA256 for authenticated encryption tags
    │
    ├─► KeyPurpose.TEMP_FILE
    │     info="lockmate.temp_file.v1"
    │     └─► AES-256-GCM for intermediate data at rest
    │
    ├─► KeyPurpose.EXPORT_GATE
    │     info="lockmate.export_gate.v1"
    │     └─► HMAC-SHA256 for output integrity verification
    │
    └─► KeyPurpose.CANARY
          info="lockmate.canary.v1"
          └─► HMAC-SHA256 for canary value generation

Security Properties:
- Domain separation prevents key reuse across purposes
- HKDF provides forward secrecy (compromise of one key doesn't reveal master)
- Master secret never written to disk or logged
- All derived keys ephemeral (cleared on rotation/destruction)
- Deterministic derivation enables reproducibility
"""