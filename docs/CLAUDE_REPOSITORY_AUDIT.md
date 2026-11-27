# LOCKMATE Repository Audit

**Date:** 2026-11-26  
**Auditor:** Claude Engineering Agent  
**Status:** Phase 1 Complete

---

## 1. Repository Structure Overview

```
lockmate/
├── main.py                    # CLI entry point (✅ working)
├── raksha.toml                # Submission config (✅ matches spec)
├── requirements.txt           # Pinned dependencies (✅)
├── pyproject.toml             # Build config
├── config/policy.yaml         # Privacy policy (✅)
├── context.md                 # Single source of truth (✅ comprehensive)
├── lockmate-strategy-and-plan.md  # Master execution plan (✅)
├── docs/                      # Documentation
│   ├── phase-3-validation.md
│   ├── track3-compliance-matrix.md
│   ├── testing-strategy.md
│   ├── security-and-threat-model.md
│   ├── REPO_INVENTORY.md
│   ├── engineering-strategy.md
│   ├── development-roadmap.md
│   ├── CONTRACT_CHECKLIST.md
│   ├── BACKLOG.md
│   ├── ASSET_REPORT.md
│   └── implementation-baseline.md
├── src/secret_wards/          # Core package
│   ├── __init__.py            # Exports all contracts
│   ├── contracts.py           # 12 frozen dataclasses (✅ complete)
│   ├── exceptions.py          # Exception hierarchy (✅)
│   ├── intake/                # File discovery & parsing
│   │   ├── discovery.py       # Safe walk, SHA-256, limits (✅)
│   │   ├── classifier.py      # Format detection (✅)
│   │   ├── encoding.py        # charset-normalizer (✅)
│   │   ├── hashing.py         # Streaming SHA-256 (✅)
│   │   ├── quarantine.py      # Quarantine handling (✅)
│   │   └── pipeline.py        # Intake orchestration (✅)
│   ├── parsers/               # Format parsers
│   │   ├── base.py            # BaseParser, utilities (✅)
│   │   ├── csv_parser.py      # CSV/TSV with delimiter detection (✅)
│   │   ├── json_parser.py     # JSON with streaming (✅)
│   │   ├── text_parser.py     # Plain text (✅)
│   │   ├── fhir_parser.py     # FHIR R4 (⚠️ partial)
│   │   ├── fhir_meta.py       # FHIR metadata scanning (⚠️ stub)
│   │   ├── fhir_attachments.py # Binary attachments (⚠️ stub)
│   │   └── fhir_references.py # Reference scanner (⚠️ stub)
│   ├── detection/             # PII detection engine
│   │   ├── placeholder.py     # Phase 3 regex patterns (✅)
│   │   ├── identifiers.py     # Aadhaar, ABHA, PAN, phone, etc. (✅)
│   │   ├── names.py           # Multilingual name detection (⚠️ partial)
│   │   ├── normalize.py       # Unicode normalization (✅)
│   │   ├── gazetteer.py       # Gazetteer loader (✅)
│   │   ├── transliterate.py   # Devanagari → Latin + Double Metaphone (✅)
│   │   ├── structured.py      # Structured field scanner (⚠️ stub)
│   │   ├── merger.py          # Medical veto (✅)
│   │   ├── calibration.py     # Threshold calibration (⚠️ stub)
│   │   └── residual.py        # Second-pass scanner (⚠️ stub)
│   ├── clinical/              # Medical preservation
│   │   ├── drugs.py           # Drug/dosage/frequency/duration (✅)
│   │   ├── labs.py            # Labs/vitals/units (✅)
│   │   ├── diagnoses.py       # Diagnoses/procedures/eponyms (✅)
│   │   ├── doctors.py         # Doctor context detection (✅)
│   │   └── veto.py            # Medical veto integration (✅)
│   ├── transform/             # Text replacement
│   │   ├── replacer.py        # Offset-map aware replacement (✅)
│   │   └── structured.py      # Structured field sanitization (✅)
│   ├── output/                # Serialization & reporting
│   │   ├── serializer.py      # Format-preserving output (✅)
│   │   ├── namer.py           # Filename sanitization (✅)
│   │   ├── writer.py          # Atomic writes (✅)
│   │   ├── security_gate.py   # Residual PII scanner (✅)
│   │   ├── pipeline.py        # Output orchestration (⚠️ format issues)
│   │   └── report.py          # MISSING - report generation
│   ├── utils/                 # Utilities
│   │   ├── logging.py         # PII-scrubbed structured logging (✅)
│   │   ├── metrics.py         # Processing metrics (✅)
│   │   └── temp.py            # Temp file management (⚠️ stub)
│   └── pipeline/              # Pipeline orchestration
│       ├── basic.py           # Basic pipeline (⚠️ stub)
│       └── full.py            # Full pipeline (✅ working)
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_contracts.py  # Contract tests (✅ 42 tests pass)
│   │   └── validation/        # Validation tests (✅ 31 tests pass)
│   └── redteam/               # MISSING - adversarial tests
├── test_input/                # Sample input
│   └── patients.csv           # 3-row CSV with PII
└── test_output/               # Previous test run outputs
```

---

## 2. Module Implementation Status

### ✅ Fully Implemented (Working)

| Module | File | Status | Notes |
|--------|------|--------|-------|
| Contracts | `contracts.py` | **Complete** | All 12 dataclasses + enums + utilities; 42 unit tests pass |
| Intake Discovery | `intake/discovery.py` | **Complete** | Safe walk, symlink protection, SHA-256, size limits |
| Intake Classifier | `intake/classifier.py` | **Complete** | Extension + content sniffing for CSV/TSV/JSON/Text/FHIR |
| Intake Encoding | `intake/encoding.py` | **Complete** | charset-normalizer, no Latin-1 fallback |
| Intake Hashing | `intake/hashing.py` | **Complete** | Streaming SHA-256 |
| Intake Quarantine | `intake/quarantine.py` | **Complete** | All reason codes from spec |
| Intake Pipeline | `intake/pipeline.py` | **Complete** | Orchestrates discovery→classify→encode→parse |
| CSV Parser | `parsers/csv_parser.py` | **Complete** | Auto-delimiter, header inference, shifted columns |
| JSON Parser | `parsers/json_parser.py` | **Complete** | Streaming with ijson, JSON Pointer paths |
| Text Parser | `parsers/text_parser.py` | **Complete** | Single record, offset maps |
| Identifiers | `detection/identifiers.py` | **Complete** | Aadhaar (Verhoeff), ABHA, PAN, phone, email, PIN, UHID, dates |
| Normalize | `detection/normalize.py` | **Complete** | NFC, Devanagari digits, ZWJ/ZWNJ, bidi, confusables, offset maps |
| Gazetteer | `detection/gazetteer.py` | **Complete** | Auto-creates minimal gazetteers, frozenset lookup |
| Transliterate | `detection/transliterate.py` | **Complete** | indic-transliteration + fallback, Double Metaphone |
| Merger | `detection/merger.py` | **Complete** | Medical veto with adjacency threshold |
| Clinical Drugs | `clinical/drugs.py` | **Complete** | Gazetteer + regex for dosage/freq/duration |
| Clinical Labs | `clinical/labs.py` | **Complete** | LOINC-derived + vital patterns |
| Clinical Diagnoses | `clinical/diagnoses.py` | **Complete** | ICD-10 + eponyms + procedures |
| Clinical Doctors | `clinical/doctors.py` | **Complete** | Dr. prefix + clinical verb context |
| Clinical Veto | `clinical/veto.py` | **Complete** | Integrates all medical detectors |
| Replacer | `transform/replacer.py` | **Complete** | Offset-map aware, replacement tokens |
| Structured Transform | `transform/structured.py` | **Complete** | CSV/JSON/FHIR field sanitization |
| Serializer | `output/serializer.py` | **Complete** | CSV/TSV/JSON/FHIR/Text serialization |
| Namer | `output/namer.py` | **Complete** | SHA-256 prefix filenames, PII detection in names |
| Writer | `output/writer.py` | **Complete** | Atomic temp→rename, cross-device fallback |
| Security Gate | `output/security_gate.py` | **Complete** | Residual PII scan, Verhoeff validation |
| Logging | `utils/logging.py` | **Complete** | PII-scrubbed JSON structured logging |
| Metrics | `utils/metrics.py` | **Complete** | Stage timing, memory tracking, aggregation |
| Exceptions | `exceptions.py` | **Complete** | Full hierarchy with context |
| Main Pipeline | `pipeline/full.py` | **Working** | End-to-end run with placeholder detection |

### ⚠️ Partially Implemented (Needs Work)

| Module | File | Status | Missing |
|--------|------|--------|---------|
| FHIR Parser | `parsers/fhir_parser.py` | **Partial** | Uses fhir.resources but missing reference/extension/contained traversal |
| FHIR Meta | `parsers/fhir_meta.py` | **Stub** | Not implemented |
| FHIR Attachments | `parsers/fhir_attachments.py` | **Stub** | Not implemented |
| FHIR References | `parsers/fhir_references.py` | **Stub** | Not implemented |
| Structured Detection | `detection/structured.py` | **Stub** | Header/key/filename scanning not integrated |
| Names Detection | `detection/names.py` | **Partial** | Gazetteer integration broken (circular import), detection logic incomplete |
| Calibration | `detection/calibration.py` | **Stub** | Threshold tuning not implemented |
| Residual Scanner | `detection/residual.py` | **Stub** | Second-pass not implemented |
| Temp Manager | `utils/temp.py` | **Stub** | Encrypted temp files not implemented |
| Basic Pipeline | `pipeline/basic.py` | **Stub** | Not implemented |
| Output Pipeline | `output/pipeline.py` | **Format Issues** | report.json format wrong (dict vs list), file paths use backslashes |
| Report Generation | `output/report.py` | **MISSING** | File does not exist! |

### ❌ Missing Modules

| Module | Expected Location | Priority |
|--------|-------------------|----------|
| Linkage/Blocking | `linkage/blocking.py` | P1 |
| Linkage/Candidates | `linkage/candidates.py` | P1 |
| Linkage/Scoring | `linkage/scoring.py` | P1 |
| Linkage/Constraints | `linkage/constraints.py` | P1 |
| Linkage/Clustering | `linkage/clustering.py` | P1 |
| Linkage/Canonical | `linkage/canonical.py` | P1 |
| Linkage/Pipeline | `linkage/pipeline.py` | P1 |
| Crypto/Secret | `crypto/secret.py` | P1 |
| Crypto/Pseudonym | `crypto/pseudonym.py` | P1 |
| Crypto/DateShift | `crypto/date_shift.py` | P1 |
| Crypto/Injector | `crypto/injector.py` | P1 |
| Privacy/DateFields | `privacy/date_fields.py` | P1 |
| Privacy/DateShift | `privacy/date_shift.py` | P1 |
| Privacy/AgeBands | `privacy/age_bands.py` | P1 |
| Privacy/Location | `privacy/location.py` | P1 |
| Privacy/Gazetteer | `privacy/gazetteer.py` | P1 |
| Privacy/Equivalence | `privacy/equivalence.py` | P1 |
| Privacy/Suppression | `privacy/suppression.py` | P1 |
| Privacy/Pipeline | `privacy/pipeline.py` | P1 |
| Red-team Tests | `tests/redteam/` | P1 |

---

## 3. Current CLI Behavior

### Smoke Test Results (test_input/patients.csv)

```bash
$ RAKSHA_SECRET="..." python main.py --input test_input --output test_output_smoke
```

**Output Structure:**
```
test_output_smoke/
├── sanitized/
│   └── 6c4af52feb2ee737.csv
├── report.json
└── records.jsonl
```

**Sanitized CSV Content:**
```csv
patient_name,age,phone,aadhaar,diagnosis
[NAME],35,[PHONE],[UID],Diabetes
[NAME],28,[PHONE],[UID],Hypertension
[NAME],42,[PHONE],[UID],Cardiology
```

**Issues Found:**
1. `identifiers_detected: 0` in report.json (should be ≥6: 3 names + 3 phones + 3 Aadhaar)
2. `records.jsonl` uses backslashes: `"file":"sanitized\\6c4af52feb2ee737.csv"` (should be forward slashes)
3. `report.json` has `files` as object `{sha: entry}` instead of array `[entry, ...]`
4. `FileReportEntry.to_dict()` outputs `output_path` but validator expects `output`
5. Exit code 1 despite successful completion (false error)

---

## 4. Test Coverage

| Test File | Tests | Status |
|-----------|-------|--------|
| `tests/unit/test_contracts.py` | 42 | ✅ All pass |
| `tests/unit/validation/test_file_validator.py` | 10 | ✅ All pass |
| `tests/unit/validation/test_path_guard.py` | 8 | ✅ 7 pass, 1 skipped (symlinks) |
| `tests/unit/validation/test_quarantine.py` | 7 | ✅ All pass |
| `tests/unit/validation/test_size_limits.py` | 6 | ✅ All pass |
| `tests/unit/validation/test_symlink_guard.py` | 8 | ✅ 1 pass, 7 skipped (Windows) |
| **Total** | **81** | **73 pass, 8 skipped** |

**Missing Test Categories:**
- No detection tests (placeholder, identifiers, names, normalize, gazetteer, transliterate)
- No clinical tests (drugs, labs, diagnoses, doctors, veto)
- No transform tests (replacer, structured)
- No output tests (serializer, namer, writer, security_gate)
- No integration tests
- No red-team/adversarial tests

---

## 5. Dependency Analysis

**requirements.txt** (pinned versions):
```
cryptography==42.0.5           ✅ HMAC, AES-GCM
charset-normalizer==3.3.2      ✅ Encoding detection
phonenumbers==8.13.48          ✅ Phone validation
dateparser==1.2.0              ✅ Date parsing
indic-transliteration==2.3.83  ✅ Devanagari → Latin
fhir.resources==7.1.0          ✅ FHIR R4 validation
jsonschema==4.23.0             ✅ JSON schema validation
regex==2024.7.24               ✅ Unicode regex
pandas==2.2.2                  ✅ CSV/TSV processing
PyYAML==6.0.1                  ✅ Config parsing
ijson==3.6.0                   ✅ Streaming JSON
psutil==5.9.8                  ✅ Memory monitoring
tqdm==4.66.5                   ✅ Progress bars
pytest==8.2.2                  ✅ Testing
pytest-cov==5.0.0              ✅ Coverage
bandit==1.7.8                  ✅ Security audit (dev)
semgrep==1.92.0                ✅ Security audit (dev)
pip-audit==2.7.1               ✅ Dependency audit (dev)
typing-extensions==4.12.2      ✅ Type hints

# Optional (commented out)
# sklearn-crfsuite==0.3.6      ⏳ CRF name tagger
# scikit-learn==1.5.0          ⏳ Classical ML
# rapidfuzz==3.9.0             ⏳ String similarity
# anonymeter==0.2.0            ⏳ Privacy metrics (dev)
# Faker==25.4.0                ⏳ Synthetic data (dev)
```

**All dependencies are CPU-only, offline-compatible, and within organizer constraints.**

---

## 6. Security Weaknesses Identified

| Issue | Severity | Location | Description |
|-------|----------|----------|-------------|
| Report format mismatch | **High** | `output/pipeline.py`, `contracts.py` | `files` is dict not array; `output_path` vs `output` field name |
| Backslash paths in records.jsonl | **High** | `output/pipeline.py` | Windows paths use `\` not `/` |
| identifiers_detected not tracked | **Medium** | `pipeline/full.py`, `detection/placeholder.py` | Detection counts not propagated to metrics |
| Exit code 1 on success | **Medium** | `main.py`, `pipeline/full.py` | False error from QuarantineAllError handling |
| FHIR validation incomplete | **Medium** | `parsers/fhir_parser.py` | Missing reference/contained/extension traversal |
| Structured field PII scanning | **Medium** | `detection/structured.py` | Stub only - JSON keys, CSV headers, filenames not scanned |
| Names detection broken | **High** | `detection/names.py` | Circular import with gazetteer, incomplete logic |
| Temp file encryption | **Medium** | `utils/temp.py` | Stub only - no AES-GCM encryption |
| No linkage/identity resolution | **Critical** | Missing modules | No PatientCluster, no pseudonym injection |
| No date shifting/age bands | **Critical** | Missing modules | Privacy transformations absent |
| No location generalization | **Critical** | Missing modules | Quasi-identifier protection absent |

---

## 7. Architecture Consistency

**Alignment with `context.md` §6 Architecture:**

| Stage | context.md | Implementation | Status |
|-------|------------|----------------|--------|
| Secure Intake | ✅ | `intake/pipeline.py` | **Complete** |
| Format Detection | ✅ | `intake/classifier.py` | **Complete** |
| Unified Record Model | ✅ | `contracts.py` + parsers | **Complete** |
| Unicode Normalization | ✅ | `detection/normalize.py` | **Complete** |
| PII Detection | ⚠️ | `detection/` (partial) | **Partial** |
| Clinical Preservation | ✅ | `clinical/` | **Complete** |
| Identity Resolution | ❌ | Missing `linkage/` | **Missing** |
| HMAC Pseudonymization | ❌ | Missing `crypto/` | **Missing** |
| Quasi-ID Transformation | ❌ | Missing `privacy/` | **Missing** |
| Serialization | ✅ | `output/serializer.py` | **Complete** |
| Output Security Gate | ✅ | `output/security_gate.py` | **Complete** |
| Sanitized Output + Reports | ⚠️ | `output/pipeline.py` | **Format Issues** |

---

## 8. Compliance with Organizer Constraints

| Constraint | Status | Evidence |
|------------|--------|----------|
| Fully offline | ✅ | No network calls in code; all deps bundled |
| CPU-only | ✅ | No CUDA/GPU deps; no transformers |
| ≤2 CPUs | ⚠️ | No parallelization yet; single-threaded |
| ≤4 GB RAM | ✅ | Streaming parsers, chunked hashing |
| ≤15 min | ⚠️ | Not benchmarked on large data |
| Synthetic data only | ✅ | Test input is synthetic |
| No runtime network | ✅ | Verified |
| No LLMs/transformers >50M | ✅ | Only classical ML deps (commented) |
| No custom crypto | ✅ | Uses `cryptography` library |
| No hardcoded secrets | ✅ | RAKSHA_SECRET from env only |
| No raw PII leakage | ⚠️ | Logging scrubs PII; but metrics leak possible |

---

## 9. Git Status

```bash
M docs/phase-3-validation.md
M src/secret_wards/detection/placeholder.py
M src/secret_wards/parsers/csv_parser.py
M src/secret_wards/parsers/fhir_parser.py
M src/secret_wards/transform/structured.py
M src/secret_wards/utils/logging.py
?? src/data/
?? src/secret_wards/clinical/
?? src/secret_wards/detection/__init__.py
?? src/secret_wards/detection/calibration.py
?? src/secret_wards/detection/gazetteer.py
?? src/secret_wards/detection/identifiers.py
?? src/secret_wards/detection/names.py
?? src/secret_wards/detection/normalize.py
?? src/secret_wards/detection/structured.py
?? src/secret_wards/detection/transliterate.py
```

**Uncommitted new files** in `src/secret_wards/` indicate active development.

---

## 10. Summary

**LOCKMATE is at ~40% implementation completeness.**

**Strengths:**
- Solid foundation: contracts, intake, parsing, clinical preservation, output serialization, security gate
- All 73 unit tests pass
- Clean architecture with clear module boundaries
- Proper offline/CPU-only dependencies
- PII-scrubbed logging, atomic writes, streaming parsers

**Critical Gaps (P0 - Must Fix for Contract Compliance):**
1. **Report.json format wrong** - dict vs array, wrong field names
2. **Records.jsonl paths use backslashes** - Windows path separator
3. **Identifiers_detected not counted** - metrics not connected to detection
4. **Exit code 1 on success** - false error handling
5. **Names detection broken** - circular import, incomplete
6. **Structured field PII scanning missing** - JSON keys, CSV headers, filenames
7. **FHIR incomplete** - references, extensions, contained, attachments
8. **Output report.py MISSING** - file doesn't exist

**Missing P1 Features (Competitive Differentiation):**
- Identity resolution / linkage (entire `linkage/` package)
- HMAC pseudonymization (entire `crypto/` package)
- Date shifting, age bands, location generalization (entire `privacy/` package)
- Red-team tests

**Recommendation:** Fix P0 issues first to achieve `CONTRACT OK` on practice data, then implement P1 linkage/privacy modules.