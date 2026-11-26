# LOCKMATE — System Architecture

**Version:** 1.0  
**Date:** 2026-11-26  
**Status:** Authoritative architecture specification

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LOCKMATE PIPELINE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  INPUT DIR                                                                   │
│      │                                                                       │
│      ▼                                                                       │
│  ┌─────────────────┐                                                         │
│  │  SECURE INTAKE  │  ── Discovery, SHA-256, Format Classification,        │
│  └────────┬────────┘     Resource Limits, Quarantine Classification        │
│           │                                                                    │
│           ▼                                                                    │
│  ┌─────────────────┐                                                         │
│  │ FORMAT PARSERS  │  ── CSV/TSV, JSON, FHIR R4, Text → Unified Record     │
│  │   (5 parsers)   │     Model (URM)                                        │
│  └────────┬────────┘                                                         │
│           │                                                                    │
│           ▼                                                                    │
│  ┌─────────────────┐                                                         │
│  │ UNICODE NORMAL  │  ── NFC, Devanagari digits, Zero-width, Bidi,          │
│  └────────┬────────┘     Offset Maps (norm ↔ orig)                          │
│           │                                                                    │
│           ▼                                                                    │
│  ┌─────────────────┐                                                         │
│  │ PII DETECTION   │  ── Structured fields, Direct IDs, Multilingual Names, │
│  │    ENGINE       │     Contextual Classification, Medical Veto            │
│  └────────┬────────┘                                                         │
│           │                                                                    │
│           ▼                                                                    │
│  ┌─────────────────┐                                                         │
│  │ IDENTITY RESOL. │  ── Blocking, Pairwise Scoring, Cannot-Link,           │
│  │   (LINKAGE)     │     Conservative Clustering, Canonical Identity        │
│  └────────┬────────┘                                                         │
│           │                                                                    │
│           ▼                                                                    │
│  ┌─────────────────┐                                                         │
│  │ PSEUDONYM SVC   │  ── HMAC-SHA256(RAKSHA_SECRET, canonical_identity)     │
│  │   (CRYPTO)      │     Domain separation: pseudonym, date_shift, rare     │
│  └────────┬────────┘                                                         │
│           │                                                                    │
│           ▼                                                                    │
│  ┌─────────────────┐                                                         │
│  │ PRIVACY TRANSF. │  ── Date Shift, Age Bands, Location Gen, Rare Suppress │
│  └────────┬────────┘                                                         │
│           │                                                                    │
│           ▼                                                                    │
│  ┌─────────────────┐                                                         │
│  │  SERIALIZATION  │  ── URM → Original Format, Pseudonym Injection,        │
│  │   & OUTPUT      │     Filename Sanitization, Atomic Write                │
│  └────────┬────────┘                                                         │
│           │                                                                    │
│           ▼                                                                    │
│  ┌─────────────────┐                                                         │
│  │ OUTPUT SECURITY │  ── Independent Residual PII Scan, Canary Check,       │
│  │      GATE       │     Clinical Integrity, Schema Validity, Meta Safety   │
│  └────────┬────────┘                                                         │
│           │                                                                    │
│     ┌─────┴─────┐                                                             │
│     ▼           ▼                                                             │
│  SANITIZED   REPORT.JSON    RECORDS.JSONL    QUARANTINE                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Architectural Invariants

| # | Invariant | Description | Enforcement |
|---|-----------|-------------|-------------|
| 1 | **Unified Record Model (URM)** | All parsers emit URM; preserves structure for lossless round-trip serialization | `contracts.py` dataclasses; parser contract |
| 2 | **Offset Mappings** | Normalized ↔ Original text offsets maintained per record for safe in-place replacement | `UnifiedRecord.offset_map`; `TextReplacer` |
| 3 | **Independent Output Security Gate** | Output validated by separate scanner, not the detector that transformed it | `OutputSecurityGate` class; separate detector instance |
| 4 | **No Raw Intermediates on Disk** | Process in memory; encrypt temp files if unavoidable; secure delete | `TempFileManager` with AES-GCM |
| 5 | **Deterministic Pipeline** | Same input + same `RAKSHA_SECRET` = byte-identical `sanitized/` content | Sorted file iteration (by SHA-256); fixed seeds; HMAC determinism |
| 5 | **Fail-Safe Quarantine** | Uncertain → quarantine; never silent pass; never copy raw to output | `QuarantineClassifier`; `SecurityGate` FAIL → quarantine |

---

## 3. Module Architecture

### 3.1 Package Structure

```
src/secret_wards/
├── contracts.py              # 12 frozen dataclasses — single integration contract
├── __init__.py               # Exports contracts, version
├── config.py                 # Policy loading (config/policy.yaml)
├── main.py                   # CLI entry point, pipeline orchestration
├── exceptions.py             # Custom exception hierarchy
│
├── intake/                   # Agent 2: Secure Intake & Ingestion
│   ├── __init__.py
│   ├── discovery.py          # File walker, symlink check, path traversal protection
│   ├── hashing.py            # Streaming SHA-256
│   ├── classifier.py         # Format classification (extension + content sniffing)
│   ├── encoding.py           # Encoding detection (charset-normalizer)
│   ├── quarantine.py         # QuarantineResult, reason codes, file copy
│   └── pipeline.py           # Intake orchestration → List[ParsedDocument] + QuarantineResults
│
├── parsers/                  # Agent 2: Format Parsers → URM
│   ├── __init__.py
│   ├── base.py               # Parser base class, common utilities
│   ├── csv_parser.py         # CSV/TSV: auto-delimiter, header inference, shifted cols
│   ├── json_parser.py        # JSON: streaming, nested walk, JSON Pointer paths
│   ├── text_parser.py        # Text: line/paragraph segmentation, offset maps
│   ├── fhir_parser.py        # FHIR R4: fhir.resources validation, refs, extensions, contained
│   ├── fhir_references.py    # FHIR reference/contained/extension scanner
│   ├── fhir_attachments.py   # FHIR Binary attachment handler (quarantine/extract)
│   └── fhir_meta.py          # FHIR metadata scanner
│
├── detection/                # Agent 3: PII Detection Engine
│   ├── __init__.py
│   ├── normalize.py          # Unicode normalization pipeline + offset maps
│   ├── structured.py         # Structured field scanner (headers, keys, FHIR, filenames)
│   ├── identifiers.py        # Direct identifier detectors (phone, Aadhaar, ABHA, PAN, UHID, email, PIN, date)
│   ├── names.py              # Multilingual name detection (triggers, gazetteer, transliteration, role classification)
│   ├── gazetteer.py          # Gazetteer loader (offline, Latin + Devanagari)
│   ├── transliterate.py      # Devanagari → IAST → Latin → Double Metaphone
│   ├── crf_tagger.py         # CRF name tagger (conditional, <50M params)
│   ├── residual.py           # Second-pass residual scanner
│   ├── merger.py             # Span merger + medical veto
│   └── engine.py             # Detection orchestration → List[PIISpan] per record
│
├── clinical/                 # Agent 5: Clinical Preservation
│   ├── __init__.py
│   ├── drugs.py              # Drug/strength/dosage/frequency/duration detector
│   ├── labs.py               # Lab/vital/unit detector (LOINC-derived)
│   ├── diagnoses.py          # Diagnosis/procedure detector (ICD-10 + eponyms)
│   ├── doctors.py            # Doctor context detector (Dr./Doctor + clinical context)
│   └── veto.py               # Medical veto integration (span-level, adjacency re-check)
│
├── linkage/                  # Agent 4: Identity Resolution
│   ├── __init__.py
│   ├── blocking.py           # Blocking key generator
│   ├── candidates.py         # Candidate pair generator
│   ├── scoring.py            # Pairwise scorer (Fellegi-Sunter inspired)
│   ├── constraints.py        # Cannot-link constraints
│   ├── clustering.py         # Conservative clusterer (greedy, consistency check)
│   ├── canonical.py          # Canonical identity builder
│   └── pipeline.py           # Linkage orchestration → List[PatientCluster]
│
├── crypto/                   # Agent 4: Pseudonymization & Cryptography
│   ├── __init__.py
│   ├── secret.py             # RAKSHA_SECRET loader (env, validation, no logging)
│   ├── pseudonym.py          # HMAC-SHA256 pseudonym service (domain separation)
│   ├── date_shift.py         # Per-patient date shift derivation (HMAC domain)
│   └── injector.py           # Pseudonym injection into sanitized records
│
├── privacy/                  # Agent 5: Privacy Transformations
│   ├── __init__.py
│   ├── gazetteer.py          # Location gazetteer loader (Census 2011 CSV)
│   ├── location.py           # Location generalizer (village→district, PIN→3-digit)
│   ├── equivalence.py        # Quasi-identifier equivalence class builder
│   ├── suppression.py        # Rare suppressor (iterative k-anonymity)
│   ├── date_fields.py        # Date field identifier
│   ├── date_shift.py         # Date shifter (applies per-patient offset)
│   ├── age_bands.py          # Age generalizer (bands per context.md §13.2)
│   └── pipeline.py           # Privacy transformation orchestration
│
├── output/                   # Agent 6: Output & Security Gate
│   ├── __init__.py
│   ├── serializer.py         # Format-preserving serialization (CSV/JSON/FHIR/text)
│   ├── namer.py              # Filename sanitizer (SHA-256 prefix for PII names)
│   ├── writer.py             # Atomic writer (temp → rename)
│   ├── security_gate.py      # Independent security gate orchestrator
│   ├── residual_scan.py      # Residual PII scanner (detectors on output)
│   ├── canary.py             # Canary checker (LOCKMATE_CANARY_*)
│   ├── clinical_check.py     # Clinical integrity verifier (pre/post medical spans)
│   ├── schema_check.py       # Schema validator (CSV/JSON/FHIR R4)
│   ├── meta_check.py         # Filename/metadata scanner
│   ├── pseudonym_check.py    # Pseudonym consistency checker
│   ├── report.py             # report.json generator (exact schema)
│   ├── records.py            # records.jsonl generator (exact schema)
│   └── pipeline.py           # Output orchestration (atomic write all three)
│
├── pipeline/                 # Agent 0: Integration
│   ├── __init__.py
│   ├── basic.py              # Basic pipeline (Phases 2-3 integration)
│   └── full.py               # Full pipeline (all phases integrated)
│
├── redteam/                  # Agent 7: Red-Team Evaluation
│   ├── __init__.py
│   ├── attacker_sim.py       # Voter-list-style attacker simulation
│   ├── fixtures.py           # Synthetic adversarial fixture generator
│   └── metrics.py            # Privacy-utility metrics computation
│
└── utils/                    # Shared utilities
    ├── __init__.py
    ├── logging.py            # PII-scrubbed structured logging
    ├── temp.py               # Secure temp file manager (AES-GCM)
    ├── metrics.py            # ProcessingMetrics collector
    └── constants.py          # Shared constants, enums
```

### 3.2 Data Flow Contracts (per `contracts.py`)

All modules communicate **only** through the 12 frozen dataclasses defined in `contracts.py`:

| Dataclass | Producer | Consumers |
|-----------|----------|-----------|
| `InputFile` | `intake.discovery` | `intake.classifier`, `parsers.*`, `output.namer` |
| `ParsedDocument` | `parsers.*` | `detection.engine`, `linkage.pipeline`, `output.serializer` |
| `UnifiedRecord` | `parsers.*` | All downstream modules |
| `FieldValue` | `parsers.*` | `detection.structured`, `detection.identifiers` |
| `PIISpan` | `detection.*` | `detection.merger`, `clinical.veto`, `linkage.blocking`, `privacy.date_fields`, `output.residual_scan` |
| `MedicalSpan` | `clinical.*` | `detection.merger`, `output.clinical_check` |
| `IdentityCandidate` | `linkage.candidates` | `linkage.scoring`, `linkage.constraints` |
| `PatientCluster` | `linkage.clustering` | `linkage.canonical`, `linkage.pipeline`, `crypto.injector`, `output.records` |
| `PrivacyTransformation` | `privacy.*` | `output.serializer` |
| `SanitizedRecord` | `output.serializer` | `output.writer`, `output.security_gate`, `crypto.injector` |
| `QuarantineResult` | `intake.quarantine`, `output.security_gate` | `output.report`, `output.pipeline` |
| `ProcessingMetrics` | All modules | `output.report` |

---

## 4. Security Architecture

### 4.1 Secret Management

```
RAKSHA_SECRET (env var, ≥32 bytes)
         │
         ▼
┌─────────────────────────────────────────┐
│         SecretManager (crypto/secret.py) │
│  • Validates length, format             │
│  • Stores in memory only (bytes)        │
│  • No __repr__, no logging              │
│  • Provides domain-separated keys       │
└─────────────────────────────────────────┘
         │
    ┌────┴────┐
    ▼         ▼
Pseudonym   Date Shift   Rare Suppression
Domain      Domain       Domain
```

### 4.2 Temporary File Security

```
Temp File Needed?
       │
       ▼
┌──────────────────┐
│ TempFileManager  │  (utils/temp.py)
│ • mkstemp()      │
│ • AES-GCM encrypt│
│   (key from      │
│   secret +       │
│   "temp" domain) │
│ • Secure delete  │
│   (overwrite +   │
│   remove)        │
└──────────────────┘
```

### 4.3 Logging Security

```
All Logs → StructuredLogHandler (utils/logging.py)
                │
                ▼
         ┌──────────────┐
         │ PII Scrubber │  ← Uses detection engine patterns
         │ • Hash only  │
         │ • Counts only│
         │ • No raw text│
         └──────────────┘
                │
                ▼
         JSON Lines Output
```

---

## 5. Determinism Architecture

| Requirement | Implementation |
|-------------|----------------|
| **File iteration order** | Sort `InputFile` list by `sha256` before processing |
| **Random seeds** | `random.seed(0)`, `numpy.random.seed(0)` at pipeline start |
| **No `datetime.now()` in content** | Fixed reference timestamps; use `time.monotonic()` for timing only |
| **Hash iteration** | Use `sorted(dict.items())` for all dictionary iterations |
| **HMAC determinism** | Same canonical identity + same secret = same pseudonym |
| **Date shift determinism** | Same patient pseudonym + same secret = same offset |
| **Floating point** | Avoid in privacy transforms; use integer days for date shifts |

---

## 5. Resource Management

| Resource | Limit | Enforcement |
|----------|-------|-------------|
| **Max file size** | 100 MB | `intake.discovery` checks `stat().st_size` |
| **Max nesting depth** | 50 | JSON/FHIR parsers track depth; exceed → quarantine |
| **Max decompression ratio** | 100:1 | Not applicable (no auto-decompression); but check if added |
| **Max total input** | 2 GB | `intake.discovery` accumulates size; exceed → stop with error |
| **Max memory (RSS)** | 4 GB | Streaming parsers; `gc.collect()` at stage boundaries; monitor via `psutil` |
| **Max CPU** | 2 cores | `ProcessPoolExecutor(max_workers=2)` for file-level parallelism |
| **Max time** | 15 min | Per-stage budgets; early termination if exceeded |

---

## 6. Error Handling & Quarantine Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    PIPELINE EXECUTION                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  PROCESS FILE   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌───────────┐  ┌───────────┐  ┌───────────┐
        │  SUCCESS  │  │ PARSE ERR │  │  EXCEPTION│
        └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
              │              │              │
              ▼              ▼              ▼
        ┌───────────┐  ┌───────────┐  ┌───────────┐
        │ Continue  │  │QUARANTINE │  │QUARANTINE │
        │ to next   │  │ (reason:  │  │ (reason:  │
        │ stage     │  │ parse_    │  │ exception)│
        │           │  │ error)    │  │           │
        └───────────┘  └───────────┘  └───────────┘
              │              │              │
              └──────────────┼──────────────┘
                             ▼
                    ┌─────────────────┐
                    │ SECURITY GATE   │
                    │ (on sanitized)  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌───────────┐  ┌───────────┐  ┌───────────┐
        │   PASS    │  │   FAIL    │  │ EXCEPTION │
        └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
              │              │              │
              ▼              ▼              ▼
        ┌───────────┐  ┌───────────┐  ┌───────────┐
        │  WRITE    │  │QUARANTINE │  │QUARANTINE │
        │ OUTPUT    │  │ OUTPUT    │  │ OUTPUT    │
        └───────────┘  └───────────┘  └───────────┘
```

---

## 7. Configuration

### 7.1 `config/policy.yaml`

```yaml
# LOCKMATE Policy Configuration
# All values can be overridden by environment variables

# Resource limits
resources:
  max_file_size_mb: 100
  max_nesting_depth: 50
  max_total_input_gb: 2
  max_workers: 2

# Detection thresholds
detection:
  name_confidence_threshold: 0.85
  identifier_confidence_threshold: 0.9
  enable_crf: false  # Only if >5% F1 gain proven

# Linkage thresholds
linkage:
  pairwise_threshold: 0.85
  blocking_keys:
    - normalized_name
    - transliterated_name
    - double_metaphone
    - phone
    - aadhaar
    - abha
    - pan
    - dob_year_gender
    - district_pin_prefix

# Privacy transformation
privacy:
  date_shift_range_days: 365
  age_bands:
    - [0, 4]
    - [5, 9]
    - [10, 14]
    - [15, 19]
    - [20, 24]
    - [25, 29]
    - [30, 34]
    - [35, 39]
    - [40, 44]
    - [45, 49]
    - [50, 54]
    - [55, 59]
    - [60, 64]
    - [65, 69]
    - [70, 74]
    - [75, 79]
    - [80, 84]
    - [85, 89]
    - [90, null]  # 90+
  k_anonymity_min: 5
  rare_suppression_order:
    - diagnosis_category
    - age_band
    - location

# Security
security:
  temp_encryption: true
  canary_prefix: "LOCKMATE_CANARY_"
  log_level: "INFO"

# Output
output:
  filename_scheme: "sha256_prefix"  # or "uuid"
  pseudonym_format: "PSN-{base32_8}"
  quarantine_dir: "quarantined"
```

### 7.2 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `RAKSHA_SECRET` | **YES** | HMAC key (≥32 bytes, base64 or hex) |
| `LOCKMATE_CONFIG` | No | Path to `policy.yaml` (default: `config/policy.yaml`) |
| `LOCKMATE_LOG_LEVEL` | No | Override log level (DEBUG, INFO, WARNING, ERROR) |

---

## 8. Testing Architecture

### 8.1 Test Organization

```
tests/
├── unit/
│   ├── test_contracts.py
│   ├── intake/
│   ├── parsers/
│   ├── detection/
│   ├── clinical/
│   ├── linkage/
│   ├── crypto/
│   ├── privacy/
│   └── output/
├── integration/
│   ├── test_basic_pipeline.py
│   ├── test_full_pipeline.py
│   ├── test_multi_hospital.py
│   ├── test_fhir_integration.py
│   └── test_quarantine_propagation.py
├── adversarial/
│   ├── test_canary_leakage.py
│   ├── test_false_merge.py
│   ├── test_medical_corruption.py
│   ├── test_privacy_attack.py
│   ├── test_performance.py
│   ├── test_determinism.py
│   ├── test_secret_rotation.py
│   └── test_resource_limits.py
├── fixtures/
│   ├── generator.py
│   ├── hospital_a/
│   ├── hospital_b/
│   ├── hospital_c/
│   ├── hospital_d/
│   └── adversarial/
└── conftest.py
```

### 8.2 Test Data Principles

- **Synthetic only** — no real patient data
- **Four hospital systems** — different schemas, formats, naming conventions
- **Known ground truth** — labeled PII, linkages, clinical values
- **Adversarial cases** — ambiguous names, transliteration variants, medical-adjacent PII, shifted columns, nested JSON, FHIR extensions
- **Deliberate non-matches** — same name, different DOB/Aadhaar → must not link

---

## 9. Deployment & Execution

### 9.1 Submission Package Layout

```
lockmate/
├── raksha.toml
├── requirements.txt
├── README.md
├── main.py
├── config/
│   └── policy.yaml
├── src/
│   └── secret_wards/          # All implementation
├── tests/                     # Not required for submission but included
├── docs/                      # Documentation
└── data/                      # Bundled gazetteers (offline)
    ├── names/
    │   ├── indian_first_names_latin.txt
    │   ├── indian_first_names_devanagari.txt
    │   ├── indian_surnames_latin.txt
    │   └── indian_surnames_devanagari.txt
    ├── medical/
    │   ├── drugs_inn.txt
    │   ├── drugs_india_brands.txt
    │   ├── loinc_labs.txt
    │   ├── icd10_diagnoses.txt
    │   └── clinical_units.txt
    └── locations/
        └── census2011_village_district_state.csv
```

### 9.2 Execution Command

```bash
# Set secret (provided by organizer at eval time)
export RAKSHA_SECRET="<base64-or-hex-secret>"

# Run pipeline
python main.py --input /path/to/input --output /path/to/output

# Validate (if organizer validator available)
python3 validate_output.py --input /path/to/input --output /path/to/output
# Expected: CONTRACT OK
```

---

## 10. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-11-26 | Lead Architect | Initial authoritative architecture from context.md & engineering-strategy.md |

---

**END OF ARCHITECTURE SPECIFICATION**