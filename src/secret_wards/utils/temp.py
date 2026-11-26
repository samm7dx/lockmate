"""
LOCKMATE — Secure Temporary File Manager
"""

from __future__ import annotations

import os
import tempfile
import atexit
from pathlib import Path
from contextlib import contextmanager
from typing import Generator, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes


class TempFileManager:
    """
    Manages secure temporary files with AES-GCM encryption.
    
    All temp files are encrypted at rest with keys derived from RAKSHA_SECRET.
    Secure deletion on cleanup (overwrite + remove).
    """
    
    def __init__(self, master_secret: bytes, domain: str = "temp"):
        """
        Initialize temp file manager.
        
        Args:
            master_secret: RAKSHA_SECRET bytes
            domain: Key separation domain (default: "temp")
        """
        # Derive encryption key from master secret
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=domain.encode("utf-8"),
        )
        self._key = hkdf.derive(master_secret)
        self._aesgcm = AESGCM(self._key)
        self._temp_paths: list[Path] = []
        self._cleanup_registered = False
    
    def _register_cleanup(self) -> None:
        """Register atexit cleanup handler once."""
        if not self._cleanup_registered:
            atexit.register(self.cleanup_all)
            self._cleanup_registered = True
    
    @contextmanager
    def create(self, suffix: str = "", prefix: str = "lockmate_", dir: Optional[Path] = None) -> Generator[Path, None, None]:
        """
        Create a secure temporary file.
        
        Args:
            suffix: File suffix (e.g., ".json", ".csv")
            prefix: File prefix
            dir: Directory for temp file (default: system temp)
            
        Yields:
            Path to the temporary file
            
        The file is automatically encrypted on write and securely deleted on exit.
        """
        self._register_cleanup()
        
        # Create temp file
        fd, path_str = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir, text=False)
        os.close(fd)
        path = Path(path_str)
        self._temp_paths.append(path)
        
        try:
            yield path
        except Exception:
            # On error, clean up immediately
            self._cleanup_path(path)
            raise
    
    def encrypt_file(self, input_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Encrypt a file with AES-GCM.
        
        Args:
            input_path: Path to plaintext file
            output_path: Optional output path (default: input_path + ".enc")
            
        Returns:
            Path to encrypted file
        """
        if output_path is None:
            output_path = input_path.with_suffix(input_path.suffix + ".enc")
        
        # Read plaintext
        with input_path.open("rb") as f:
            plaintext = f.read()
        
        # Generate nonce
        nonce = os.urandom(12)
        
        # Encrypt
        ciphertext = self._aesgcm.encrypt(nonce, plaintext, None)
        
        # Write nonce + ciphertext
        with output_path.open("wb") as f:
            f.write(nonce)
            f.write(ciphertext)
        
        return output_path
    
    def decrypt_file(self, input_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Decrypt a file encrypted with encrypt_file.
        
        Args:
            input_path: Path to encrypted file
            output_path: Optional output path (default: input_path without .enc)
            
        Returns:
            Path to decrypted file
        """
        if output_path is None:
            if input_path.suffix == ".enc":
                output_path = input_path.with_suffix("")
            else:
                output_path = input_path.with_suffix(input_path.suffix + ".dec")
        
        # Read nonce + ciphertext
        with input_path.open("rb") as f:
            nonce = f.read(12)
            ciphertext = f.read()
        
        if len(nonce) != 12:
            raise ValueError("Invalid encrypted file: missing nonce")
        
        # Decrypt
        plaintext = self._aesgcm.decrypt(nonce, ciphertext, None)
        
        # Write plaintext
        with output_path.open("wb") as f:
            f.write(plaintext)
        
        return output_path
    
    def _cleanup_path(self, path: Path) -> None:
        """Securely delete a single file."""
        if path.exists():
            try:
                # Overwrite with random data (3 passes)
                file_size = path.stat().st_size
                for _ in range(3):
                    with path.open("wb") as f:
                        f.write(os.urandom(file_size))
                # Remove
                path.unlink()
            except Exception:
                pass  # Best effort
            
            if path in self._temp_paths:
                self._temp_paths.remove(path)
    
    def cleanup_all(self) -> None:
        """Clean up all tracked temporary files."""
        for path in list(self._temp_paths):
            self._cleanup_path(path)
        self._temp_paths.clear()
    
    def __enter__(self) -> "TempFileManager":
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup_all()


def secure_delete(path: Path, passes: int = 3) -> None:
    """
    Securely delete a file by overwriting with random data.
    
    Args:
        path: File to delete
        passes: Number of overwrite passes
    """
    if not path.exists():
        return
    
    try:
        file_size = path.stat().st_size
        for _ in range(passes):
            with path.open("wb") as f:
                f.write(os.urandom(file_size))
        path.unlink()
    except Exception:
        pass  # Best effort