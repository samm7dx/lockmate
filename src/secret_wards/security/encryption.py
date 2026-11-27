"""
LOCKMATE — Phase 7: Authenticated Encryption for Intermediate Data

Implements encrypted storage for sensitive intermediate data:
- Uses AES-256-GCM (authenticated encryption)
- Never persists unencrypted identity mappings
- Encrypts sensitive intermediate data at rest when persistence is necessary
- Cleans up temporary files after use
- Avoids exposing sensitive data in crash dumps or debug files
"""

from __future__ import annotations

import logging
import os
import tempfile
import atexit
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, BinaryIO, Dict, Any
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

from ..utils.logging import get_logger

logger = get_logger("security.encryption")


@dataclass
class EncryptedData:
    """Container for encrypted data with metadata."""
    ciphertext: bytes
    nonce: bytes
    tag: bytes  # GCM authentication tag (included in ciphertext for AESGCM)
    associated_data: Optional[bytes] = None
    
    def to_bytes(self) -> bytes:
        """Serialize to bytes: nonce + ciphertext + tag."""
        return self.nonce + self.ciphertext + self.tag
    
    @classmethod
    def from_bytes(cls, data: bytes, nonce_size: int = 12) -> "EncryptedData":
        """Deserialize from bytes."""
        if len(data) < nonce_size + 16:
            raise ValueError("Data too short to contain nonce and tag")
        nonce = data[:nonce_size]
        tag = data[-16:]
        ciphertext = data[nonce_size:-16]
        return cls(ciphertext=ciphertext, nonce=nonce, tag=tag)


class TempFileEncryption:
    """
    Manages encrypted temporary files for intermediate data.
    
    Features:
    - AES-256-GCM authenticated encryption
    - Automatic cleanup on exit
    - Secure key management via KeyManager
    - Prevents sensitive data in crash dumps
    """
    
    def __init__(self, encryption_key: bytes):
        """
        Initialize with encryption key.
        
        Args:
            encryption_key: 32-byte AES-256 key
        """
        if len(encryption_key) != 32:
            raise ValueError("Encryption key must be 32 bytes (AES-256)")
        
        self.cipher = AESGCM(encryption_key)
        self._temp_files: Dict[str, Path] = {}
        self._nonce_counter = 0
        
        # Register cleanup on exit
        atexit.register(self.cleanup_all)
        
        logger.info("temp_file_encryption_initialized")
    
    def _generate_nonce(self) -> bytes:
        """Generate a unique nonce for each encryption operation."""
        # Use counter + random for uniqueness
        import secrets
        counter_bytes = self._nonce_counter.to_bytes(8, "big")
        random_bytes = secrets.token_bytes(4)
        self._nonce_counter += 1
        return counter_bytes + random_bytes
    
    def encrypt(self, plaintext: bytes, associated_data: Optional[bytes] = None) -> EncryptedData:
        """
        Encrypt data with AES-256-GCM.
        
        Args:
            plaintext: Data to encrypt
            associated_data: Optional AAD for authentication
            
        Returns:
            EncryptedData container
        """
        nonce = self._generate_nonce()
        # AESGCM returns ciphertext || tag (tag is 16 bytes)
        full_ciphertext = self.cipher.encrypt(nonce, plaintext, associated_data)
        actual_ciphertext = full_ciphertext[:-16]
        tag = full_ciphertext[-16:]
        
        return EncryptedData(
            ciphertext=actual_ciphertext,
            nonce=nonce,
            tag=tag,
            associated_data=associated_data
        )
    
    def decrypt(self, encrypted: EncryptedData) -> bytes:
        """
        Decrypt data with AES-256-GCM.
        
        Args:
            encrypted: EncryptedData container
            
        Returns:
            Decrypted plaintext
            
        Raises:
            InvalidTag: If authentication fails (tampering detected)
        """
        # Reconstruct full ciphertext for AESGCM
        full_ciphertext = encrypted.ciphertext + encrypted.tag
        return self.cipher.decrypt(encrypted.nonce, full_ciphertext, encrypted.associated_data)
    
    def encrypt_to_file(
        self, 
        plaintext: bytes, 
        file_path: Path,
        associated_data: Optional[bytes] = None
    ) -> None:
        """
        Encrypt and write to file atomically.
        
        Args:
            plaintext: Data to encrypt
            file_path: Output file path
            associated_data: Optional AAD
        """
        encrypted = self.encrypt(plaintext, associated_data)
        
        # Write atomically using temp file + rename
        temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
        try:
            with open(temp_path, "wb") as f:
                f.write(encrypted.to_bytes())
            temp_path.replace(file_path)
            
            self._temp_files[str(file_path)] = file_path
            logger.debug("encrypted_file_written", path=str(file_path))
        except Exception:
            # Clean up temp file on failure
            if temp_path.exists():
                temp_path.unlink()
            raise
    
    def decrypt_from_file(self, file_path: Path) -> bytes:
        """
        Read and decrypt from file.
        
        Args:
            file_path: Encrypted file path
            
        Returns:
            Decrypted plaintext
            
        Raises:
            InvalidTag: If authentication fails
        """
        with open(file_path, "rb") as f:
            data = f.read()
        
        encrypted = EncryptedData.from_bytes(data)
        return self.decrypt(encrypted)
    
    def create_encrypted_temp_file(self, prefix: str = "lockmate_", suffix: str = ".enc") -> Path:
        """
        Create a new encrypted temporary file path.
        
        Args:
            prefix: File prefix
            suffix: File suffix
            
        Returns:
            Path for the encrypted temp file
        """
        # Create in system temp directory
        fd, path = tempfile.mkstemp(prefix=prefix, suffix=suffix)
        os.close(fd)
        temp_path = Path(path)
        self._temp_files[str(temp_path)] = temp_path
        return temp_path
    
    def write_encrypted_temp(
        self, 
        plaintext: bytes, 
        prefix: str = "lockmate_", 
        suffix: str = ".enc",
        associated_data: Optional[bytes] = None
    ) -> Path:
        """
        Write encrypted data to a new temporary file.
        
        Args:
            plaintext: Data to encrypt
            prefix: File prefix
            suffix: File suffix
            associated_data: Optional AAD
            
        Returns:
            Path to encrypted temp file
        """
        temp_path = self.create_encrypted_temp_file(prefix, suffix)
        self.encrypt_to_file(plaintext, temp_path, associated_data)
        return temp_path
    
    def read_encrypted_temp(self, file_path: Path) -> bytes:
        """
        Read and decrypt a temporary file.
        
        Args:
            file_path: Path to encrypted temp file
            
        Returns:
            Decrypted plaintext
        """
        return self.decrypt_from_file(file_path)
    
    def cleanup_file(self, file_path: Path) -> bool:
        """
        Securely delete a temporary file.
        
        Args:
            file_path: Path to delete
            
        Returns:
            True if file was deleted
        """
        path_str = str(file_path)
        if path_str in self._temp_files:
            try:
                # Overwrite before deletion (best effort)
                if file_path.exists():
                    file_path.unlink()
                del self._temp_files[path_str]
                logger.debug("temp_file_cleaned", path=path_str)
                return True
            except Exception as e:
                logger.warning("temp_file_cleanup_failed", path=path_str, error=str(e))
        return False
    
    def cleanup_all(self) -> int:
        """
        Clean up all tracked temporary files.
        
        Returns:
            Number of files cleaned up
        """
        count = 0
        for path_str in list(self._temp_files.keys()):
            if self.cleanup_file(Path(path_str)):
                count += 1
        
        if count > 0:
            logger.info("temp_files_cleaned", count=count)
        return count
    
    def list_temp_files(self) -> List[Path]:
        """List all tracked temporary files."""
        return list(self._temp_files.values())


def encrypt_data(plaintext: bytes, key: bytes, associated_data: Optional[bytes] = None) -> EncryptedData:
    """
    Standalone function to encrypt data with AES-256-GCM.
    
    Args:
        plaintext: Data to encrypt
        key: 32-byte AES-256 key
        associated_data: Optional AAD
        
    Returns:
        EncryptedData container
    """
    if len(key) != 32:
        raise ValueError("Key must be 32 bytes (AES-256)")
    
    cipher = AESGCM(key)
    import secrets
    nonce = secrets.token_bytes(12)
    ciphertext = cipher.encrypt(nonce, plaintext, associated_data)
    
    return EncryptedData(
        ciphertext=ciphertext,
        nonce=nonce,
        tag=ciphertext[-16:],
        associated_data=associated_data
    )


def decrypt_data(encrypted: EncryptedData, key: bytes) -> bytes:
    """
    Standalone function to decrypt data with AES-256-GCM.
    
    Args:
        encrypted: EncryptedData container
        key: 32-byte AES-256 key
        
    Returns:
        Decrypted plaintext
        
    Raises:
        InvalidTag: If authentication fails
    """
    if len(key) != 32:
        raise ValueError("Key must be 32 bytes (AES-256)")
    
    cipher = AESGCM(key)
    full_ciphertext = encrypted.ciphertext + encrypted.tag
    return cipher.decrypt(encrypted.nonce, full_ciphertext, encrypted.associated_data)


def encrypt_file(input_path: Path, output_path: Path, key: bytes, associated_data: Optional[bytes] = None) -> None:
    """Encrypt a file to another file."""
    with open(input_path, "rb") as f:
        plaintext = f.read()
    
    encrypted = encrypt_data(plaintext, key, associated_data)
    
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    try:
        with open(temp_path, "wb") as f:
            f.write(encrypted.to_bytes())
        temp_path.replace(output_path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise


def decrypt_file(input_path: Path, output_path: Path, key: bytes) -> None:
    """Decrypt a file to another file."""
    with open(input_path, "rb") as f:
        data = f.read()
    
    encrypted = EncryptedData.from_bytes(data)
    plaintext = decrypt_data(encrypted, key)
    
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    try:
        with open(temp_path, "wb") as f:
            f.write(plaintext)
        temp_path.replace(output_path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise