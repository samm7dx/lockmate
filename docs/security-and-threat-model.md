# LOCKMATE — Security & Threat Model

**Version:** 1.0  
**Date:** 2026-11-26  
**Status:** Authoritative security specification

---

## 1. Threat Model

### 1.1 Attacker Profile

| Attribute | Assumption |
|-----------|------------|
| **Identity** | Motivated external adversary |
| **Access** | Sanitized output directory only |
| **Auxiliary Data** | Public voter rolls, census data, social media, hospital directories, leaked databases |
| **Knowledge** | Full knowledge of LOCKMATE algorithms (Kerckhoffs's principle) |
| **Capabilities** | Record linkage, quasi-identifier join, statistical inference, script/transliteration matching, brute force |
| **No Access To** | `RAKSHA_SECRET`, raw inputs, internal processing state, temporary files (encrypted) |

### 1.2 Attack Surface

| Surface | Risk | Mitigation |
|---------|------|------------|
| Sanitized file contents | Direct PII leakage | Multi-layer detection + second-pass + independent gate |
| Sanitized file metadata | PII in JSON keys, FHIR meta | Structured scanner + metadata sanitizer |
| Filenames | PII in paths | Filename sanitizer (SHA-256 prefix) |
| `report.json` | PII in fields, original filenames | Hash-keyed entries; no raw PII; no original names |
| `records.jsonl` | Pseudonym linkage | Consistency checker; null for uncertain |
| Temporary files | Raw PII at rest | AES-GCM encryption; secure delete; minimize disk |
| Logs | Raw PII in traces | Structured JSON logging; PII scrubber |
| Exceptions | Raw PII in stack traces | Global exception handler; log hash only |
| Memory dumps | `RAKSHA_SECRET`, raw data | Secret in memory only; no `__repr__`; overwrite on exit |
| Side channels | Timing, memory patterns | Constant-time HMAC; fixed iteration order |

---

## 2. Attack Vectors & Defenses

### 2.1 Direct Identifier Leakage (A1)

| Vector | Example | Defense |
|--------|---------|---------|
| Names in free text | "Patient Rahul admitted" | Multilingual name detection + role classification |
| Names in structured fields | `{"patient_name": "Rahul"}` | Structured field scanner (headers, keys, FHIR) |
| Phone numbers | "Mobile: 9876543210" | `phonenumbers` + regex; Devanagari digits |
| Aadhaar/ABHA/PAN | `{"aadhaar": "123456789012"}` | Format validation + checksums (Verhoeff) |
| UHID/MRN | `UHID: ABC123` | Context-aware patterns |
| Email/URL | `patient@hospital.com` | RFC 5322 regex |
| PIN codes | `110001` | 6-digit regex + context |
| Dates | `DOB: 15/08/1990` | `dateparser` + contextual classification |

**Defense in Depth:**
1. **Primary detection** — Rule-based + gazetteer + transliteration
2. **Medical veto** — Span-level protection preserves clinical values
3. **Second-pass sweep** — Re-scans sanitized output for stragglers
4. **Independent security gate** — Separate detector instance scans final output

### 2.2 Quasi-Identifier Linkage (A2)

| Vector | Example | Defense |
|--------|---------|---------|
| Age + District + Diagnosis | 45, Delhi, TB → unique | Age bands (round down), location generalization (district→state), rare suppression |
| Admission date + LOS | 2024-01-15, 3 days → unique | Per-patient date shift (preserves intervals, hides exact dates) |
| Rare diagnosis + Village | Rare disease + small village | k-anonymity diagnostic (k=5); iterative suppression |
| PIN + Age | 110001, 67 → unique | PIN → 3-digit prefix; age bands |

**Defense in Depth:**
1. **Per-patient date shift** — HMAC-derived offset [-365, +365]; preserves intervals
2. **Age banding** — 19 bands (0-4, 5-9, ..., 90+); always round down
3. **Location hierarchy** — Village→District→State; PIN→3-digit
4. **Rare-value suppression** — Iterative: suppress rarest attribute → generalize age → generalize location
5. **Attacker simulation** — Synthetic voter roll measures re-ID risk (<5% target)

### 2.3 Residual Name Fragments (A3)

| Vector | Example | Defense |
|--------|---------|---------|
| Partial redaction | "Rahul S." → "R. S." | Second-pass sweep searches for patient's known identifiers |
| Missed mentions | "Patient Rahul" in note after "Patient Rahul Sharma" in header | Document-level consistency + cross-file linkage |
| Transliteration variants | "मोहम्मद" missed after "Mohammed" caught | Double Metaphone on transliterated names; gazetteer covers variants |

### 2.4 Metadata/Filename Leakage (A4)

| Vector | Example | Defense |
|--------|---------|---------|
| PII in filename | `rahul_sharma_report.csv` | Filename sanitizer → SHA-256 prefix + ext |
| PII in JSON keys | `{"patient_name": "..."}` | Structured scanner redacts keys in output |
| PII in FHIR meta | `meta.tag.code = "patient-rahul"` | FHIR metadata scanner |
| PII in CSV headers | `patient_name,mobile,aadhaar` | Header scanner + sanitizer |

### 2.5 Date/Shift Reversibility (A5)

| Vector | Example | Defense |
|--------|---------|---------|
| Known shift algorithm | Attacker knows HMAC-SHA256 + domain | 128-bit HMAC output; secret never exposed; brute force infeasible |
| Known patient pseudonym | Attacker has `PSN-a1b2c3d4` | Pseudonym is truncated HMAC; cannot reverse to canonical identity |
| Multiple dates per patient | Admission, discharge, DOB, labs | All shifted by same offset; intervals preserved but absolute dates hidden |

### 2.6 Pseudonym Collision/Linkage (A6)

| Vector | Example | Defense |
|--------|---------|---------|
| Weak canonicalization | "Rahul Sharma" + "Sharma Rahul" → different canonical | Sorted, pipe-joined reliable identifiers only |
| Birthday paradox | 10k patients → pseudonym collision | 128-bit HMAC truncated to 8 base32 chars (40 bits); collision probability negligible |
| Cross-patient correlation | Same pseudonym → same patient | Canonical identity includes hard IDs (Aadhaar, phone) when available |

### 2.7 Format-Specific Leaks (A7)

| Format | Vector | Defense |
|--------|--------|---------|
| FHIR | `Patient.telecom`, `Practitioner.name`, `reference` fields | Deep traversal: references, contained, extensions |
| FHIR | `Binary` attachments (Base64 PDF) | Attachment handler: quarantine PDF/image; extract text |
| FHIR | `meta.tag`, `meta.profile`, `meta.security` | Metadata scanner |
| JSON | Nested PII in arrays/objects | Schema-agnostic recursive walk with JSON Pointer paths |
| CSV | PII in headers + shifted columns | Content-based column matching |

---

## 3. Security Controls Implementation

### 3.1 Cryptography

| Primitive | Library | Usage |
|-----------|---------|-------|
| HMAC-SHA256 | `cryptography.hazmat.primitives.hmac` | Pseudonyms, date shifts, rare suppression seeds |
| AES-GCM | `cryptography.hazmat.primitives.ciphers.aead.AESGCM` | Temporary file encryption |
| Key derivation | `cryptography.hazmat.primitives.kdf.hkdf.HKDF` | Domain separation from `RAKSHA_SECRET` |

**Domain Separation:**
```
RAKSHA_SECRET (HKDF)
    │
    ├── "pseudonym"     → Pseudonym HMAC key
    ├── "date_shift"    → Date shift HMAC key
    ├── "rare_suppress" → Rare suppression HMAC key
    └── "temp"          → Temp file AES-GCM key
```

### 3.2 Secret Management

```python
# crypto/secret.py
class SecretManager:
    def __init__(self):
        raw = os.environ["RAKSHA_SECRET"]
        # Accept base64 or hex; validate ≥32 bytes
        self._secret = self._decode_and_validate(raw)
        # Derive domain keys
        self._keys = {domain: hkdf(self._secret, domain) for domain in DOMAINS}
    
    def get_key(self, domain: str) -> bytes:
        return self._keys[domain]
    
    def __del__(self):
        # Overwrite memory on deletion
        if hasattr(self, '_secret'):
            self._secret = b'\x00' * len(self._secret)
```

**Rules:**
- Read `RAKSHA_SECRET` **once** at startup
- Store in memory only (bytes)
- **Never** log, print, write to disk, include in reports
- No `__repr__`, `__str__`, or serialization
- Overwrite on cleanup

### 3.3 Temporary File Handling

```python
# utils/temp.py
class TempFileManager:
    def __init__(self, secret_manager: SecretManager):
        self._key = secret_manager.get_key("temp")
        self._paths = []
    
    @contextmanager
    def create(self, suffix: str = "") -> Generator[Path, None, None]:
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        self._paths.append(path)
        try:
            yield Path(path)
        finally:
            self._cleanup(path)
    
    def _cleanup(self, path: Path):
        # Encrypt if not already encrypted
        # Secure delete: overwrite + remove
        self._secure_delete(path)
        self._paths.remove(path)
    
    def _secure_delete(self, path: Path):
        # Overwrite with random bytes (3 passes)
        # Then os.remove()
        pass
```

**Rules:**
- Use `tempfile.mkstemp()` with `O_EXCL`
- Encrypt with AES-GCM (fresh nonce per file)
- Track all temp paths
- Cleanup in `finally` block
- Secure delete: overwrite + `os.remove()`

### 3.4 Logging Security

```python
# utils/logging.py
class PIIScrubbingFormatter(logging.Formatter):
    def __init__(self, detector):
        self.detector = detector  # Detection engine instance
    
    def format(self, record: LogRecord) -> str:
        # Convert to dict
        log_dict = self._record_to_dict(record)
        # Scrub any string fields
        log_dict = self._scrub_dict(log_dict)
        return json.dumps(log_dict)
    
    def _scrub_dict(self, d: dict) -> dict:
        for k, v in d.items():
            if isinstance(v, str):
                # Run through detection patterns
                if self._contains_pii(v):
                    d[k] = "[REDACTED]"
            elif isinstance(v, dict):
                d[k] = self._scrub_dict(v)
        return d
```

**Rules:**
- Structured JSON lines only
- **Never** log raw text, field values, filenames with PII
- Log: hashes, counts, timing, memory, status codes
- If debug logging needed: redact via detection engine before emit

### 3.5 Exception Handling

```python
# main.py
def main():
    try:
        run_pipeline()
    except Exception as e:
        # Log error (hash only)
        logger.error("pipeline_failed", file_sha256=current_file_sha, error_type=type(e).__name__)
        # Quarantine all unprocessed files
        quarantine_remaining_files()
        # Write partial report.json
        write_partial_report()
        sys.exit(1)
```

**Rules:**
- Catch all exceptions at top level
- Log error with **file hash only** (no raw content)
- Quarantine all unprocessed files
- Write partial `report.json` with what completed
- Exit non-zero

---

## 4. Canary Testing

### 4.1 Canary Injection

```python
# Generate unique canary strings per run
CANARY_PREFIX = "LOCKMATE_CANARY_"

def inject_canaries(input_dir: Path, canary_map: Dict[Path, str]):
    """Inject canaries into input files for leakage detection."""
    for file_path, canary in canary_map.items():
        # Inject into content, filename, metadata
        pass
```

### 4.2 Canary Verification

```python
# output/canary.py
def scan_for_canaries(output_dir: Path, log_dir: Path, temp_dir: Path) -> bool:
    """Returns True if clean (no canaries found)."""
    canary_pattern = re.compile(r"LOCKMATE_CANARY_[A-F0-9-]+")
    
    for root in [output_dir, log_dir, temp_dir]:
        for file in root.rglob("*"):
            if file.is_file():
                content = file.read_bytes()
                if canary_pattern.search(content):
                    logger.critical("canary_leaked", file=str(file))
                    return False
    return True
```

**Requirement:** Zero canary leakage in output, logs, or temp directories.

---

## 5. Secure Development Practices

### 5.1 Code Review Requirements

| Requirement | Enforcement |
|-------------|-------------|
| No `eval()` / `exec()` | Bandit rule B101, B102 |
| No `shell=True` in subprocess | Bandit rule B602 |
| No hardcoded secrets | Bandit rule B105, B106, B107 |
| No `pickle` deserialization | Bandit rule B301 |
| No `yaml.load()` without `SafeLoader` | Bandit rule B506 |
| All crypto via `cryptography` library | Manual review |

### 5.2 Dependency Security

```bash
# Run on every build
pip-audit -r requirements.txt
safety check -r requirements.txt
bandit -r src/secret_wards/
semgrep --config=auto src/secret_wards/
```

### 5.3 Memory Safety

```python
# Process large files in chunks
def stream_json(file_path: Path) -> Generator[dict, None, None]:
    with file_path.open('r') as f:
        for line in f:
            yield json.loads(line)

# Explicit cleanup at stage boundaries
def process_stage(records: List[UnifiedRecord]):
    try:
        # ... processing ...
    finally:
        del large_intermediate
        gc.collect()
```

### 5.4 Input Validation

```python
# intake/classifier.py
def classify_file(file_path: Path) -> FormatType:
    # Check path traversal
    if not file_path.resolve().is_relative_to(input_root.resolve()):
        raise SecurityError("path_traversal")
    
    # Check symlinks
    if file_path.is_symlink():
        target = file_path.resolve()
        if not target.is_relative_to(input_root.resolve()):
            raise SecurityError("path_traversal")
    
    # Check size
    if file_path.stat().st_size > MAX_FILE_SIZE:
        raise SecurityError("resource_limit_exceeded")
    
    # ... content-based classification ...
```

---

## 6. Security Testing

### 6.1 Automated Security Tests (`tests/adversarial/`)

| Test | Description |
|------|-------------|
| `test_canary_leakage.py` | Inject canaries → verify zero leakage |
| `test_false_merge.py` | Same name, different hard IDs → separate pseudonyms |
| `test_medical_corruption.py` | Clinical values adjacent to names → 0% corruption |
| `test_privacy_attack.py` | Voter roll linkage → <5% unique re-ID |
| `test_resource_limits.py` | Oversized/nested/bomb files → quarantine |
| `test_path_traversal.py` | Symlinks, `../` paths → blocked |

### 6.2 Static Analysis

```bash
# Bandit (security linting)
bandit -r src/secret_wards/ -f json -o bandit-report.json

# Semgrep (pattern-based)
semgrep --config=auto src/secret_wards/ --json -o semgrep-report.json

# Dependency audit
pip-audit -r requirements.txt --format=json -o pip-audit-report.json
```

### 6.3 Penetration Testing (Manual)

| Area | Test |
|------|------|
| Temp files | Verify AES-GCM encryption; verify secure delete |
| Logs | Inject PII → verify scrubbed in output |
| Exceptions | Trigger errors → verify no PII in traces |
| Memory | Dump process → verify no secret/raw data |
| Network | Run in air-gapped env → verify no connections |

---

## 7. Incident Response (If Leakage Detected)

### 7.1 Detection Points

1. **Security Gate** — Residual PII scan fails → quarantine output
2. **Canary Check** — Canary found → immediate alert
3. **Log Review** — PII in logs → alert
4. **Adversarial Tests** — Regression detected → block merge

### 7.2 Response Procedure

```
LEAKAGE DETECTED
       │
       ▼
┌──────────────────┐
│  QUARANTINE ALL  │  ← Immediate: quarantine all output from this run
│  OUTPUT FILES    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  ROOT CAUSE      │  ← Identify: which detector failed? which file?
│  ANALYSIS        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  FIX & REGRESSION│  ← Fix detector; add test case for this pattern
│  TEST            │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  RE-RUN FULL     │  ← Full pipeline + all adversarial tests
│  PIPELINE        │
└────────┬─────────┘
         │
         ▼
   VERIFY CLEAN
```

---

## 8. Compliance Mapping

| Organizer Requirement | Security Control | Implementation |
|----------------------|------------------|----------------|
| Offline execution | No network calls | `socket` monkey-patch in tests; no network deps |
| CPU only | No GPU code | No CUDA/torch/tensorflow |
| No LLMs >50M params | Model audit | `pip-audit` + manual review |
| `RAKSHA_SECRET` never logged | SecretManager | No `__repr__`; scrubbed logging |
| No raw PII in output | Security Gate | Independent residual scan |
| No raw PII in temp | TempFileManager | AES-GCM + secure delete |
| No raw PII in logs | PIIScrubbingFormatter | Detection-based redaction |
| Deterministic output | Sorted iteration + fixed seeds | `random.seed(0)`; sort by SHA-256 |
| Different secret → different output | HMAC domain separation | Separate keys per domain |

---

## 9. Known Limitations & Residual Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Unknown PII pattern not in gazetteer | Medium | Direct leakage | Second-pass sweep; canary testing; adversarial fixtures |
| Transliteration ambiguity | Low | False merge/linkage miss | Double Metaphone + strict cannot-link |
| Medical veto over-preservation | Low | Clinical name preserved | Context window + role markers; adversarial tests |
| FHIR extension PII | Medium | Metadata leakage | Deep traversal test suite; quarantine on validation fail |
| Side-channel timing | Very Low | Secret extraction | Constant-time HMAC; not high-value target |
| Organizer validator mismatch | Medium | False `CONTRACT OK` | Self-validator mirrors spec; test against organizer when available |

---

## 10. Security Checklist (Pre-Submission)

- [ ] `RAKSHA_SECRET` read from env only; never logged/written
- [ ] All temp files encrypted with AES-GCM; securely deleted
- [ ] Structured logging only; PII scrubber active
- [ ] Global exception handler; no PII in traces
- [ ] Canary injection + verification passes
- [ ] Security gate: residual PII scan passes on clean output
- [ ] Security gate: fails on injected PII
- [ ] Bandit + Semgrep + pip-audit clean
- [ ] No `eval`, `exec`, `shell=True`, `pickle`, unsafe `yaml.load`
- [ ] All crypto via `cryptography` library
- [ ] Domain separation for all HMAC uses
- [ ] Deterministic: 3 runs same secret = byte-identical
- [ ] Secret rotation: 2 runs different secrets = different pseudonyms/shifts
- [ ] Resource limits enforced: file size, nesting, decompression
- [ ] Path traversal blocked; symlinks resolved safely
- [ ] `report.json`/`records.jsonl` contain no PII
- [ ] Sanitized filenames contain no PII
- [ ] Quarantine behavior: explicit, never silent, reason codes

---

**END OF SECURITY & THREAT MODEL**