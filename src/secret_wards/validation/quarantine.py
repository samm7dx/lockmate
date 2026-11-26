"""
LOCKMATE — Malformed File Quarantine

Manages quarantined files with metadata tracking.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import json
import shutil

from ..utils.logging import get_logger

logger = get_logger("validation.quarantine")


@dataclass
class QuarantineConfig:
    """Configuration for quarantine."""
    quarantine_path: Path = Path("quarantine")
    max_quarantine_size: int = 10 * 1024 * 1024 * 1024  # 10GB
    retention_days: int = 30
    compress: bool = True


@dataclass
class QuarantineEntry:
    """Metadata for a quarantined file."""
    original_path: str
    original_name: str
    quarantine_path: str
    reason: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    file_size: int = 0
    mime_type: str = ""
    details: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "original_path": self.original_path,
            "original_name": self.original_name,
            "quarantine_path": self.quarantine_path,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "details": self.details,
        }
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: dict) -> "QuarantineEntry":
        return cls(
            original_path=data["original_path"],
            original_name=data["original_name"],
            quarantine_path=data["quarantine_path"],
            reason=data["reason"],
            id=uuid.UUID(data["id"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            file_size=data["file_size"],
            mime_type=data["mime_type"],
            details=data["details"],
        )


class QuarantineManager:
    """Manages quarantined files and metadata."""
    
    def __init__(self, config_path: Path = None, config: object = None) -> None:
        if config:
            self.config = config
        else:
            self.config = QuarantineConfig()
            
        self.quarantine_dir = self.config.quarantine_path
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.quarantine_dir / "metadata.jsonl"
    
    def quarantine(
        self, 
        file_path: Union[str, Path], 
        reason: str,
        mime_type: str = "",
        details: Optional[dict] = None
    ) -> "QuarantineEntry":
        """
        Quarantine a file.
        
        Args:
            file_path: Path to file to quarantine
            reason: Reason for quarantine
            mime_type: Optional MIME type
            details: Optional additional details
            
        Returns:
            QuarantineEntry with metadata
        """
        file_path = Path(file_path)
        
        # Generate unique quarantine name
        entry_id = uuid.uuid4()
        ext = file_path.suffix
        quarantine_name = f"{entry_id}{ext}"
        quarantine_path = self.quarantine_dir / quarantine_name
        
        # Move file to quarantine
        file_size = file_path.stat().st_size
        
        # Check total quarantine size
        current_size = self._get_total_size()
        if current_size + file_size > self.config.max_quarantine_size:
            logger.error("quarantine.size_limit_exceeded", extra={"size": current_size + file_size})
            raise RuntimeError("Quarantine size limit exceeded")
        
        shutil.move(str(file_path), str(quarantine_path))
        
        # Create entry
        entry = QuarantineEntry(
            id=uuid.uuid4(),
            original_path=str(file_path),
            original_name=file_path.name,
            quarantine_path=str(quarantine_path),
            reason=reason,
            file_size=file_size,
            mime_type=mime_type,
            details=details or {},
        )
        
        # Write metadata
        self._write_metadata(entry)
        
        logger.info("quarantine.quarantined", extra=entry.to_dict())
        
        return entry
    
    def _write_metadata(self, entry: "QuarantineEntry") -> None:
        """Write entry metadata to JSONL file."""
        self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.metadata_file, "a", encoding="utf-8") as f:
            f.write(entry.to_json() + "\n")
    
    def _get_total_size(self) -> int:
        """Calculate total size of quarantined files."""
        total = 0
        for f in self.quarantine_dir.glob("*"):
            if f.is_file() and f.name != "metadata.jsonl":
                total += f.stat().st_size
        return total
    
    def list_entries(self) -> List["QuarantineEntry"]:
        """List all quarantined entries."""
        entries = []
        if self.metadata_file.exists():
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        entries.append(QuarantineEntry.from_dict(json.loads(line)))
        return entries
    
    def get_entry(self, entry_id: uuid.UUID) -> Optional["QuarantineEntry"]:
        """Get a specific entry by ID."""
        for entry in self.list_entries():
            if entry.id == entry_id:
                return entry
        return None
    
    def restore(self, entry_id: uuid.UUID, destination: Union[str, Path]) -> bool:
        """
        Restore a quarantined file.
        
        Args:
            entry_id: ID of entry to restore
            destination: Destination path
            
        Returns:
            True if restored successfully
        """
        entry = self.get_entry(entry_id)
        if not entry:
            logger.error("quarantine.entry_not_found", extra={"entry_id": str(entry_id)})
            return False
        
        src = Path(entry.quarantine_path)
        if not src.exists():
            logger.error("quarantine.file_missing", extra={"path": str(src)})
            return False
        
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(destination))
        
        # Remove from metadata (rewrite file)
        self._remove_metadata(entry.id)
        
        logger.info("quarantine.restored", extra={"entry_id": str(entry_id), "destination": str(destination)})
        return True
    
    def _remove_metadata(self, entry_id: uuid.UUID) -> None:
        """Remove entry from metadata file."""
        entries = self.list_entries()
        entries = [e for e in entries if e.id != entry_id]
        
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(entry.to_json() + "\n")
    
    def delete(self, entry_id: uuid.UUID) -> bool:
        """Permanently delete a quarantined file."""
        entry = self.get_entry(entry_id)
        if not entry:
            return False
        
        src = Path(entry.quarantine_path)
        if src.exists():
            src.unlink()
        
        self._remove_metadata(entry_id)
        
        logger.info("quarantine.deleted", extra={"entry_id": str(entry_id)})
        return True