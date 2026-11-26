# Security Policy and Design

## 1. Threat Model

### Adversary Goals
- Execute path traversal attacks to read arbitrary system files.
- Bypass file size/resource limits (Denial of Service).
- Inject malicious payloads via malformed files.
- Overwrite critical system or application files.
- Expose sensitive PHI/PII through insecure output handling.

### Attack Vectors
- `../` or `..\\` in filenames.
- Symlinks pointing to `/etc/passwd`, `/etc/shadow`, etc.
- Compressed files (Zip bombs) - *Future scope*.
- Extremely large files or many small files.
- Files with incorrect MIME types but valid extensions.
- Race conditions during file writes.

## 2. Security Controls (Ingestion Module)

### 2.1. Path Guard
- **Absolute Resolution**: All paths are resolved to absolute paths before any checks.
- **Allowed Roots**: A configurable list of allowed directory roots is enforced.
- **Traversal Detection**: Explicit check for `..` segments and root-level access.
- **Win32 Specifics**: Support for both `/` and `\` separators, and drive letters.

### 2.2. Symlink Guard
- **No-Follow Policy**: By default, symlinks are not followed.
- **Validation**: If enabled, symlink targets are resolved and validated against allowed roots.
- **Circular Detection**: Protection against circular symlinks.

### 2.3. Resource Limits
- **Max File Size**: Enforced per file (default: 100MB).
- **Total Ingestion Size**: Enforced across a batch (default: 1GB).
- **Memory Thresholds**: Parsers must operate within memory constraints.
- **Timeout**: Processing time per file is capped.

### 2.4. File Validation
- **MIME Type**: Verified using `python-magic` (libmagic).
- **Encoding**: Detected and validated using `charset-normalizer`.
- **Structural Check**: Preliminary check per format (e.g., valid CSV headers, valid JSON).
- **Quarantine**: Files failing validation are moved to a restricted quarantine area for auditing.

### 2.5. Output Security
- **Atomic Writes**: Use temporary files and `os.replace` for atomic updates.
- **Sanitized Filenames**: Output filenames are generated using UUIDs or sanitized versions of input names.
- **Path Isolation**: Output is written to a dedicated, isolated directory.

## 3. Data Handling (Privacy)

- **PHI/PII Detection**: Multi-layer detection (Regex, NLP, Dictionary).
- **Record Linkage**: Deterministic and probabilistic matching.
- **De-identification**: Safe harbor and expert determination support.
- **Serialization**: Ensure sensitive fields are appropriately redacted/masked before write.

## 4. Implementation Guidelines

- No usage of `os.system` or `subprocess.run` with untrusted input.
- Use `pathlib` for all path operations.
- Enforce strict typing with Pydantic.
- Use `secrets` for any required random values.
- Comprehensive logging of security-sensitive events.

## 5. Security Testing

- Fuzzing parsers with `Hypothesis`.
- Security unit tests for all guards.
- Integration tests simulating path traversal and symlink attacks.
- Regular dependency auditing (`pip-audit`).