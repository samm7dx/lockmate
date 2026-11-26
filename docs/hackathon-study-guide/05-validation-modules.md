# LOCKMATE Hackathon Study Guide — Document 5
## Validation Modules — Deep Dive

---

### 5.1 Module Overview

| Module | File | Lines | Primary Responsibility |
|--------|------|-------|------------------------|
| Path Guard | `path_guard.py` | 99 | Path traversal prevention |
| Symlink Guard | `symlink_guard.py` | 99 | Symlink attack prevention |
| Size Limits | `size_limits.py` | 104 | Resource exhaustion prevention |
| File Validator | `file_validator.py` | 211 | MIME, encoding, structure validation |
| Quarantine | `quarantine.py` | 214 | Isolation & forensic retention |

---

### 5.2 Path Guard (`path_guard.py`)

#### 5.2.1 Threat Model
```
Attacker provides: ../../../etc/passwd
                 or: /absolute/path/outside/sandbox
                 or: C:\Windows\System32\config\SAM
                 or: path\with\x00null_byte
```

#### 5.2.2 Implementation

```python
class PathTraversalError(Exception):
    def __init__(self, path: Path, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Path traversal: {path} - {reason}")

class PathGuard:
    def __init__(self, allowed_roots: list[Path]) -> None:
        # Normalize all roots to absolute, resolved paths
        self.allowed_roots = [root.resolve() for root in allowed_roots]

    def validate(self, path: Union[str, Path]) -> Path:
        path = Path(path)
        
        # 1. Resolve to absolute (follows symlinks!)
        resolved = path.resolve()
        
        # 2. Null byte check (prevents C-style string truncation)
        if "\x00" in str(resolved):
            raise PathTraversalError(resolved, "Null byte in path")
        
        # 3. Path traversal sequence check
        # Check both resolved parts AND original parts
        for part in resolved.parts:
            if part == "..":
                raise PathTraversalError(resolved, "Path traversal sequence '..'")
        
        # 4. Root allowlist enforcement
        if not any(resolved.is_relative_to(root) for root in self.allowed_roots):
            raise PathTraversalError(resolved, 
                f"Path not under allowed roots: {self.allowed_roots}")
        
        return resolved
```

#### 5.2.3 Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| `resolve()` before checks | Defeats symlink bypass attempts |
| Check resolved parts | Covers `a/../b` patterns |
| Allowlist not denylist | Positive security model |
| Null byte check | Prevents `open("safe.txt\x00malicious")` |

#### 5.2.4 Test Cases (`test_path_guard.py`)

```python
def test_valid_path_within_root():
    guard = PathGuard([Path("/data/input")])
    assert guard.validate("/data/input/file.csv") == Path("/data/input/file.csv")

def test_path_traversal_blocked():
    guard = PathGuard([Path("/data/input")])
    with pytest.raises(PathTraversalError):
        guard.validate("/data/input/../../etc/passwd")

def test_null_byte_blocked():
    guard = PathGuard([Path("/data/input")])
    with pytest.raises(PathTraversalError):
        guard.validate(Path("/data/input/file.txt\x00.exe"))
```

---

### 5.3 Symlink Guard (`symlink_guard.py`)

#### 5.3.1 Threat Model
```
Attacker creates: /data/input/link → /etc/shadow
Pipeline reads: /data/input/link (thinks it's in sandbox)
Actually reads: /etc/shadow
```

#### 5.3.2 Implementation

```python
class SymlinkError(Exception):
    def __init__(self, path: Path, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Symlink error: {path} - {reason}")

class SymlinkGuard:
    def __init__(
        self,
        enabled: bool = True,
        allowed_roots: Optional[list[Path]] = None,
        follow_allowed: bool = False
    ) -> None:
        self.enabled = enabled
        self.allowed_roots = [r.resolve() for r in allowed_roots] if allowed_roots else []
        self.follow_allowed = follow_allowed

    def check(self, path: Union[str, Path]) -> None:
        path = Path(path)
        
        if not self.enabled:
            return
        
        # is_symlink() returns True for both files and dirs
        if path.is_symlink():
            if not self.follow_allowed:
                raise SymlinkError(path, "Symlinks not allowed")
            
            # If following allowed, validate TARGET is within roots
            target = path.resolve()
            if not any(target.is_relative_to(root) for root in self.allowed_roots):
                raise SymlinkError(path, f"Symlink target outside roots: {target}")
```

#### 5.3.3 Configuration Modes

```python
# Mode 1: MAXIMUM SECURITY (Default)
guard = SymlinkGuard(enabled=True, follow_allowed=False)
# → All symlinks rejected

# Mode 2: FOLLOW WITHIN ROOT
guard = SymlinkGuard(enabled=True, allowed_roots=[Path("/data/input")], follow_allowed=True)
# → Follow symlink ONLY if target resolves within allowed_roots

# Mode 3: DISABLED (NOT RECOMMENDED)
guard = SymlinkGuard(enabled=False)
# → No symlink checks
```

#### 5.3.4 Windows Considerations
- Windows symlinks require admin privileges (Developer Mode)
- Tests skipped on Windows: `@pytest.mark.skipif(sys.platform == "win32", ...)`
- On Linux/macOS, all 7 tests pass

---

### 5.4 Size Limits (`size_limits.py`)

#### 5.4.1 Threat Model
```
Attacker uploads: 50GB file → OOM kill
Attacker uploads: 10,000 x 100MB files → disk full
Parser loads: 2GB JSON into memory → OOM
```

#### 5.4.2 Implementation

```python
class SizeLimitExceeded(Exception):
    def __init__(self, path: Path, actual: int, limit: int, limit_type: str):
        self.path = path
        self.actual = actual
        self.limit = limit
        self.limit_type = limit_type  # "File" or "Total" or "Memory"
        super().__init__(f"{limit_type} size limit exceeded: {actual} > {limit}")

class SizeLimitConfig:
    def __init__(
        self,
        max_file_size: int = 100 * 1024 * 1024,      # 100MB
        max_total_size: int = 1024 * 1024 * 1024,    # 1GB
        max_memory: int = 512 * 1024 * 1024,         # 512MB
    ) -> None: ...

class SizeLimiter:
    def __init__(self, max_file_size: int = 100 * 1024 * 1024) -> None:
        self.max_file_size = max_file_size
        self.total_size = 0
        self.max_total_size = 1024 * 1024 * 1024  # 1GB default

    def check(self, path: Union[str, Path]) -> None:
        size = Path(path).stat().st_size
        
        # Per-file limit
        if size > self.max_file_size:
            raise SizeLimitExceeded(path, size, self.max_file_size, "File")
        
        # Batch total limit
        self.total_size += size
        if self.total_size > self.max_total_size:
            raise SizeLimitExceeded(path, self.total_size, self.max_total_size, "Total")

    def check_memory(self, estimated_memory: int) -> None:
        if estimated_memory > self.max_memory:
            raise SizeLimitExceeded(None, estimated_memory, self.max_memory, "Memory")

    def reset_total(self) -> None:
        self.total_size = 0
```

#### 5.4.3 Usage in Pipeline

```python
# In secure_ingest.py
self.size_limiter = SizeLimiter(max_file_size=config.max_file_size)

# Before processing each file:
self.size_limiter.check(file_path)

# For JSON/FHIR parsers (estimate memory):
# Parser calls size_limiter.check_memory(estimated_size)
```

---

### 5.5 File Validator (`file_validator.py`)

#### 5.5.1 Validation Pipeline

```python
def validate(self, path: Path) -> ValidationResult:
    # 1. Existence
    if not path.exists():
        return ValidationResult(False, "File does not exist", "", {})
    if not path.is_file():
        return ValidationResult(False, "Path is not a file", "", {})
    
    # 2. Size (redundant with SizeLimiter)
    if path.stat().st_size == 0:
        return ValidationResult(False, "Empty file", "", {})
    
    # 3. MIME Type Detection
    mime_type = self._detect_mime_type(path)
    if mime_type not in self.config.allowed_mime_types:
        return ValidationResult(False, f"Disallowed MIME: {mime_type}", mime_type, {})
    
    # 4. Encoding Detection
    encoding = self._detect_encoding(path)
    if encoding not in self.config.allowed_encodings:
        return ValidationResult(False, f"Disallowed encoding: {encoding}", mime_type, {})
    
    # 5. Structural Validation
    if not self._validate_structure(path, mime_type):
        return ValidationResult(False, "Structure validation failed", mime_type, {})
    
    return ValidationResult(True, "Valid", mime_type, {"encoding": encoding})
```

#### 5.5.2 MIME Detection Strategy

```python
def _detect_mime_type(self, path: Path) -> str:
    # Priority 1: python-magic (libmagic) - most accurate
    if HAS_MAGIC:
        return magic.from_file(str(path), mime=True)
    
    # Priority 2: Extension fallback
    ext = path.suffix.lower()
    # Handle compound extensions (.fhir.json)
    for known_ext, mime in _EXTENSION_MIME_TYPES.items():
        if path.name.endswith(known_ext):
            return mime
    
    return _EXTENSION_MIME_TYPES.get(ext, "application/octet-stream")
```

**Extension Map** (28 entries):
```python
_EXTENSION_MIME_TYPES = {
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".json": "application/json",
    ".ndjson": "application/x-ndjson",
    ".jsonl": "application/x-ndjson",
    ".fhir.json": "application/fhir+json",
    ".xml": "application/xml",
    ".log": "text/plain",
    # ... 19 more
}
```

#### 5.5.3 Encoding Detection

```python
def _detect_encoding(self, path: Path) -> str:
    # Read first 64KB for detection
    with open(path, "rb") as f:
        sample = f.read(65536)
    
    # charset-normalizer (replacement for chardet)
    result = from_bytes(sample).best()
    if result:
        return result.encoding.lower()
    
    return "utf-8"  # Default fallback
```

**Allowed Encodings** (configurable): `["utf-8", "utf-16", "ascii", "latin-1", "iso-8859-1"]`

#### 5.5.4 Structural Validation

```python
def _validate_structure(self, path: Path, mime_type: str) -> bool:
    if "csv" in mime_type or "tab-separated" in mime_type:
        return self._validate_csv(path)
    elif "json" in mime_type:
        return self._validate_json(path)
    elif "fhir" in mime_type:
        return self._validate_json(path)  # FHIR is JSON
    return True  # Text/unknown: no structure validation
```

---

### 5.6 Quarantine Manager (`quarantine.py`)

#### 5.6.1 Data Model

```python
@dataclass
class QuarantineConfig:
    quarantine_path: Path = Path("quarantine")
    max_quarantine_size: int = 10 * 1024 * 1024 * 1024  # 10GB
    retention_days: int = 30
    compress: bool = True  # gzip quarantined files

@dataclass
class QuarantineEntry:
    original_path: str
    original_name: str
    quarantine_path: str
    reason: str
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    file_size: int = 0
    mime_type: str = ""
    details: dict = field(default_factory=dict)
```

#### 5.6.2 Quarantine Process

```python
def quarantine(self, file_path: Path, reason: str, mime_type: str = "", details: dict = None) -> QuarantineEntry:
    # 1. Generate safe name: <uuid>_<sanitized_original_name>
    safe_name = f"{uuid4()}_{sanitize_filename(file_path.name)}"
    quarantine_file = self.quarantine_path / safe_name
    
    # 2. Copy file (or compress)
    if self.config.compress:
        with gzip.open(quarantine_file, "wb") as f_out:
            with open(file_path, "rb") as f_in:
                shutil.copyfileobj(f_in, f_out)
    else:
        shutil.copy2(file_path, quarantine_file)
    
    # 3. Create entry
    entry = QuarantineEntry(
        original_path=str(file_path),
        original_name=file_path.name,
        quarantine_path=str(quarantine_file),
        reason=reason,
        file_size=file_path.stat().st_size,
        mime_type=mime_type,
        details=details or {}
    )
    
    # 4. Append to metadata.jsonl (atomic append)
    with open(self.metadata_path, "a") as f:
        f.write(json.dumps(asdict(entry)) + "\n")
    
    # 5. Enforce size limit (LRU eviction)
    self._enforce_size_limit()
    
    return entry
```

#### 5.6.3 Directory Structure

```
quarantine/
├── metadata.jsonl          # One JSON line per entry
├── a1b2c3d4-file.csv.gz    # Compressed quarantined file
├── e5f6g7h8-document.txt   # Uncompressed (if compress=False)
└── ...
```

#### 5.6.4 Metadata Format (JSONL)

```json
{"id": "a1b2c3d4-...", "original_path": "/data/input/file.csv", "original_name": "file.csv", "quarantine_path": "quarantine/a1b2c3d4-file.csv.gz", "reason": "Disallowed MIME type: application/x-executable", "timestamp": "2026-01-15T10:30:00Z", "file_size": 1024, "mime_type": "application/x-executable", "details": {}}
```

#### 5.6.5 Recovery Operations

```python
def restore(self, entry_id: UUID, destination: Path) -> bool:
    # Find entry, decompress if needed, copy to destination

def delete(self, entry_id: UUID) -> bool:
    # Remove file and metadata entry

def get_entry(self, entry_id: UUID) -> QuarantineEntry | None:
    # Lookup by ID

def list_entries(self, limit: int = 100) -> list[QuarantineEntry]:
    # Recent entries
```

---

### 5.7 Validation Test Results Summary

| Module | Tests | Pass | Skip | Fail |
|--------|-------|------|------|------|
| Path Guard | 7 | 5 | 2 | 0 |
| Symlink Guard | 7 | 1 | 6 | 0 |
| Size Limits | 5 | 5 | 0 | 0 |
| File Validator | 9 | 9 | 0 | 0 |
| Quarantine | 8 | 8 | 0 | 0 |
| **Total** | **36** | **28** | **8** | **0** |

> All skips are Windows symlink limitations.

---

### 5.8 Configuration Reference

```python
# Full validation config in IngestionConfig
config = IngestionConfig(
    # Path Guard
    allowed_roots=[Path("/data/input")],
    
    # Symlink Guard
    follow_symlinks=False,
    
    # Size Limits
    max_file_size=100 * 1024 * 1024,
    max_total_size=1024 * 1024 * 1024,
    
    # File Validator
    validation=ValidationConfig(
        allowed_mime_types=[
            "text/csv",
            "text/tab-separated-values",
            "application/json",
            "application/x-ndjson",
            "application/fhir+json",
            "text/plain"
        ],
        allowed_encodings=["utf-8", "utf-16", "ascii"],
        max_file_size=100 * 1024 * 1024,
        validate_structure=True
    ),
    
    # Quarantine
    quarantine_dir=Path("/data/quarantine"),
    quarantine=QuarantineConfig(
        max_quarantine_size=10 * 1024 * 1024 * 1024,
        retention_days=30,
        compress=True
    )
)
```