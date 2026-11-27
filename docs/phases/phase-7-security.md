# Phase 7: Security Hardening, Reliability & Performance

## Overview

Phase 7 establishes the security and operational foundations required to run LOCKMATE safely in the organizer's isolated environment. It implements:

1. **Cryptographic Key Management** - Proper key derivation with domain separation
2. **Intermediate Data Protection** - Encrypted temporary files with authenticated encryption
3. **PII-Safe Logging** - Structured logging that never exposes PII
4. **Safe Exception Handling** - Sanitized error messages
5. **Export Security Controls** - Final output validation and canary verification
6. **Offline Execution Verification** - Network-free operation confirmation
7. **Performance & Reliability Measurement** - Resource monitoring
8. **Reproducibility Verification** - Deterministic output validation

## Implementation Status

### ✅ Implemented Components

| Component | File | Status |
|-----------|------|--------|
| Key Manager | `src/secret_wards/security/key_manager.py` | ✅ Complete |
| Encryption | `src/secret_wards/security/encryption.py` | ✅ Complete |
| Safe Logging | `src/secret_wards/security/safe_logging.py` | ✅ Complete |
| Safe Errors | `src/secret_wards/security/safe_errors.py` | ✅ Complete |
| Export Hardening | `src/secret_wards/security/export_hardening.py` | ✅ Complete |

### 🔧 Key Features Implemented

#### Key Management (`KeyManager` class)
- **Never writes RAKSHA_SECRET to disk**
- **Never includes secrets in logs or exceptions**
- HKDF-SHA256 with domain separation for purpose-specific keys
- Key purposes: pseudonym, date_shift, encryption, authentication, temp_file, export_gate, canary
- Cryptographic failures block unsafe export
- Key rotation support
- Memory clearing on destruction

**Key Hierarchy:**
```
RAKSHA_SECRET (master, ≥32 bytes, from env)
    │
    ├─► HKDF-SHA256 (salt="lockmate-salt-v1")
    │
    ├─► KeyPurpose.PSEUDONYM → HMAC per-patient
    ├─► KeyPurpose.DATE_SHIFT → HMAC per-patient
    ├─► KeyPurpose.ENCRYPTION → AES-256-GCM
    ├─► KeyPurpose.AUTHENTICATION → HMAC-SHA256
    ├─► KeyPurpose.TEMP_FILE → AES-256-GCM
    ├─► KeyPurpose.EXPORT_GATE → HMAC-SHA256
    └─► KeyPurpose.CANARY → HMAC-SHA256
```

#### Encrypted Temporary Files (`TempFileEncryption` class)
- AES-256-GCM authenticated encryption
- Automatic cleanup on exit (atexit handler)
- Atomic file writes (temp + rename)
- Secure deletion (best-effort overwrite)
- Prevents sensitive data in crash dumps
- Tracks all temp files for cleanup verification

#### PII-Safe Logging (`SafeLogger`, `LogSanitizer`)
- Automatic PII redaction from all log data
- Redacts: names, phones, Aadhaar, PAN, ABHA, emails, addresses, DOBs, MRNs, secrets
- Regex patterns for common identifier formats
- Forbidden field name list
- String length truncation (default 500 chars)
- Structured JSON logging
- Exception sanitization (no tracebacks in production)

#### Safe Exception Handling (`SafeErrorHandler`, `PIISafeError`)
- All exceptions inherit from `PIISafeError`
- Error categories: validation, parse, resource, crypto, io, config, internal, quarantine
- Sanitized error messages (PII removed)
- Context sanitization
- Debug traceback separation (debug logger only)
- Decorator for safe function execution

#### Export Hardening (`ExportHardener`, `OutputGate`, `CanaryChecker`)
- **Final output inspection before release**
- PII scanning in sanitized output
- Report.json structure validation
- Records.jsonl format validation
- Filename sanitization (path traversal, reserved names)
- Quarantine isolation verification
- Binary attachment detection
- Temporary file cleanup verification
- **Canary verification** - detects output bypass/tampering

### 📋 Security Guarantees

| Guarantee | Implementation |
|-----------|----------------|
| Secret never on disk | KeyManager keeps master secret in memory only |
| Secret never in logs | LogSanitizer redacts all secret-like fields |
| Temp data encrypted | TempFileEncryption uses AES-256-GCM |
| Temp data cleaned | atexit handler + explicit cleanup |
| No PII in exceptions | SafeErrorHandler sanitizes all messages |
| Output validated | OutputGate runs 9 security checks |
| Canaries prevent bypass | CanaryChecker verifies pipeline execution |
| Offline execution | No network dependencies in code |
| Deterministic | Fixed seeds, sorted processing, no randomness |

### 🧪 Tests

Security tests cover:
1. Secret non-disclosure (logs, errors, files)
2. Key derivation correctness
3. Authenticated encryption (tampering detection)
4. Temporary file cleanup
5. PII-free logging
6. Exception sanitization
7. Offline execution (no network calls)
8. Deterministic output
9. Input immutability
10. Memory measurement
11. Runtime measurement
12. Failure handling
13. Quarantine integrity

### 📝 Remaining Work

- [ ] Integration with main pipeline (`pipeline/full.py`)
- [ ] Network isolation test (requires test environment)
- [ ] Memory profiling integration
- [ ] Crash dump analysis verification
- [ ] Side-channel resistance analysis
- [ ] Formal verification of key hierarchy
- [ ] Penetration testing
- [ ] Security audit checklist completion

## Acceptance Criteria

- [x] Cryptographic abstraction implemented
- [x] Sensitive intermediate persistence protected
- [x] PII-free logging implemented
- [x] Safe exception handling implemented
- [x] Final export security checks implemented
- [ ] Offline execution tested (requires test env)
- [ ] Performance measured
- [ ] Reproducibility verified
- [ ] Full regression suite passed

**Phase 7 Status: FOUNDATION COMPLETE** — Core security components implemented and independently testable. Pipeline integration pending.