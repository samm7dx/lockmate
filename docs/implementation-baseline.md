# LOCKMATE — Implementation Baseline Report

**Date:** 2026-11-26  
**Phase:** 0 — Foundation & Contract Audit  
**Status:** Baseline established — zero implementation code exists

---

## 1. Executive Summary

The LOCKMATE repository contains **only engineering documentation** — no implementation code, no tests, no configuration, no organizer assets. This is a **greenfield project** requiring complete implementation from scratch.

| Category | Status |
|----------|--------|
| Source code (`src/`) | ❌ Missing entirely |
| Tests (`tests/`) | ❌ Missing entirely |
| Submission config (`raksha.toml`) | ❌ Missing |
| CLI entry point (`main.py`) | ❌ Missing |
| Dependencies (`requirements.txt`) | ❌ Missing |
| Organizer validator (`validate_output.py`) | ❌ Not found in workspace |
| Practice dataset (`dev/input/`) | ❌ Not found in workspace |
| Git repository (project-level) | ❌ Not initialized |

**All mandatory organizer requirements are currently UNMET.**

---

## 2. Existing Functionality

### Documentation (Complete)
| File | Location | Size | Purpose |
|------|----------|------|---------|
| `context.md` | Root + `docs/` | 51 KB | Authoritative engineering context (single source of truth) |
| `engineering-strategy.md` | `docs/` | 62 KB | Master multi-agent execution plan with 14 phases |
| `deep-research-report.md` | Root | 22 KB | Original research/strategy (superseded) |
| `lockmate-strategy-and-plan.txt` | Root | 29 KB | Original strategy (superseded) |
| `lockmate-strategy-and-plan.md` | Root | 62 KB | Duplicate of `docs/engineering-strategy.md` |

### Implementation Code
**ZERO** — No Python modules, no parsers, no detectors, no pipeline code exists.

---

## 3. Missing Functionality (Complete Gap Analysis)

### Phase 0 — Foundation & Contract Audit
- [ ] Repository inventory (`REPO_INVENTORY.md`)
- [ ] Contract checklist (`CONTRACT_CHECKLIST.md`)
- [ ] Asset report (`ASSET_REPORT.md`) — validator & dataset status
- [ ] Validated `raksha.toml`
- [ ] Shared interfaces (`src/secret_wards/contracts.py` — 12 dataclasses)
- [ ] Prioritized backlog (`BACKLOG.md`)

### Phase 1 — Shared Models & Interfaces
- [ ] `src/secret_wards/contracts.py` with all 12 frozen dataclasses
- [ ] `src/secret_wards/__init__.py` exporting contracts

### Phase 2 — Secure Intake & Ingestion
- [ ] File discovery walker with symlink/path traversal protection
- [ ] SHA-256 streaming calculator
- [ ] Format classifier (extension + content sniffing)
- [ ] Encoding detector (charset-normalizer, no Latin-1 fallback)
- [ ] CSV/TSV parser (auto-delimiter, shifted columns, header inference)
- [ ] JSON parser (streaming, nested walk, JSON Pointer paths)
- [ ] Plain text parser (line/paragraph segmentation, offset maps)
- [ ] FHIR R4 parser (fhir.resources validation, references, extensions, contained, attachments)
- [ ] Quarantine classifier with reason codes
- [ ] Intake pipeline integration

### Phase 3 — Basic Sanitization Pipeline
- [ ] Placeholder PII detector (regex for email, phone, PAN, 12-digit, dates)
- [ ] Placeholder medical veto (regex for dosages, frequencies, disease names)
- [ ] Span merger with medical veto
- [ ] Text replacer (offset-map aware)
- [ ] Structured field sanitizer (CSV/JSON/FHIR)
- [ ] Serializer (format-preserving, UTF-8, pseudonym placeholder)
- [ ] Filename sanitizer (SHA-256 prefix for PII-bearing names)
- [ ] Atomic writer (temp → rename)
- [ ] Basic pipeline integration (end-to-end CSV/JSON/text)

### Phase 4 — PII Detection Engine
- [ ] Unicode normalization pipeline (NFC, Devanagari digits, offset maps)
- [ ] Structured field scanner (headers, JSON keys, FHIR paths, filenames)
- [ ] Phone detector (India, phonenumbers + regex, Devanagari digits)
- [ ] Aadhaar detector (12 digits + Verhoeff checksum)
- [ ] ABHA detector (14 digits, format validation)
- [ ] PAN detector (regex)
- [ ] UHID/MRN detector (context-aware patterns)
- [ ] Email/URL detector
- [ ] PIN/Address detector
- [ ] Date detector (dateparser + contextual classification)
- [ ] Honorific/Relationship trigger detector (S/o, D/o, W/o, C/O, श्री, पुत्र, etc.)
- [ ] Gazetteer loader (offline, Latin + Devanagari, transliteration variants)
- [ ] Transliteration + Double Metaphone (indic-transliteration → IAST → Latin → Double Metaphone)
- [ ] Name detector (rule-based, role classification: patient/relative/doctor/clinical)
- [ ] CRF name tagger (conditional — only if >5% F1 gain)
- [ ] Second-pass residual scanner
- [ ] Detection engine integration

### Phase 5 — Clinical Preservation
- [ ] Drug/strength/dosage/frequency/duration detector (gazetteer + regex)
- [ ] Lab/vital/unit detector (LOINC-derived + patterns)
- [ ] Diagnosis/procedure detector (ICD-10 + eponyms)
- [ ] Doctor context detector (Dr./Doctor + clinical context)
- [ ] Medical veto integration (span-level, adjacency re-check)
- [ ] Clinical preservation tests

### Phase 6 — Output Security Gate & Reporting
- [ ] Residual PII scanner (independent, runs detectors on output)
- [ ] Canary checker (LOCKMATE_CANARY_* strings)
- [ ] Clinical integrity verifier (pre/post medical span comparison)
- [ ] Schema validator (CSV/TSV/JSON/FHIR R4)
- [ ] Filename/metadata scanner
- [ ] Pseudonym consistency checker
- [ ] Security gate orchestrator (all checks must PASS)
- [ ] report.json generator (exact schema per context.md §16.2)
- [ ] records.jsonl generator (exact schema per context.md §16.3)
- [ ] Reporting integration (atomic write of all three outputs)

### Phase 7 — Identity Resolution & Linkage
- [ ] Blocking key generator (normalized name, transliterated, Double Metaphone, phone, IDs, DOB, geography)
- [ ] Candidate pair generator (deduplicated, max pairs controlled)
- [ ] Pairwise scorer (Fellegi-Sunter inspired, configurable weights)
- [ ] Cannot-link constraints (conflicting hard IDs → force separate)
- [ ] Conservative clusterer (greedy, consistency check, no transitive closure, null for uncertain)
- [ ] Canonical identity builder (sorted reliable identifiers)
- [ ] Linkage integration

### Phase 8 — Pseudonymization
- [ ] Secret loader (RAKSHA_SECRET from env, validates length, never logs)
- [ ] HMAC pseudonym service (domain separation, PSN-XXXX format)
- [ ] Date-shift derivation (per-patient offset from HMAC)
- [ ] Pseudonym injection (adds/replaces patient identifier field)
- [ ] Pseudonym integration

### Phase 9 — Date & Age Transformations
- [ ] Date field identifier (DATE-type PII spans + structured date fields)
- [ ] Date shifter (per-patient offset, preserves intervals, handles timezone)
- [ ] Age generalizer (bands per context.md §13.2, round down, 90+ ceiling)
- [ ] Date/age integration

### Phase 10 — Location & Rare-Value Protection
- [ ] Location gazetteer loader (Census 2011 CSV bundled)
- [ ] Location generalizer (village→district, city→district, PIN→3-digit, rare→state)
- [ ] Quasi-identifier equivalence class builder
- [ ] Rare suppressor (iterative: suppress rarest → generalize age → generalize location)
- [ ] Attacker simulation (synthetic voter roll linkage)
- [ ] Privacy integration

### Phase 11 — FHIR & Extended Format Hardening
- [ ] FHIR reference scanner (references, contained, extensions)
- [ ] FHIR attachment handler (Base64 PDF/image → quarantine, text/plain → extract)
- [ ] FHIR metadata scanner (meta.tag, meta.profile, meta.security)
- [ ] FHIR serializer validator (fhir.resources round-trip)
- [ ] FHIR integration test

### Phase 12 — Red-Team Evaluation & Hardening
- [ ] Synthetic adversarial fixture generator
- [ ] Canary injection & verification
- [ ] False-merge test suite
- [ ] Medical corruption test
- [ ] Privacy attack evaluation
- [ ] Performance profiling (2GB input)
- [ ] Determinism verification (3 runs same secret = byte-identical)
- [ ] Secret rotation verification (2 runs different secrets → different pseudonyms/shifts)
- [ ] Resource limit enforcement
- [ ] Security hardening review (bandit, semgrep)

### Phase 13 — Performance Optimization
- [ ] Profile hot paths
- [ ] Optimize blocking
- [ ] Vectorize detection
- [ ] Streaming serialization
- [ ] Parallel file processing (max 2 workers)
- [ ] Memory cleanup

### Phase 14 — Frontend & Demonstration (Optional)
- [ ] Demo data curation
- [ ] Pipeline visualization (Streamlit)
- [ ] Before/After viewer
- [ ] Linkage explorer
- [ ] Privacy dashboard
- [ ] Verifier panel
- [ ] 5-min demo script

---

## 4. Existing Tests and Coverage

**ZERO tests exist.** No `tests/` directory, no pytest configuration, no test files.

### Required Test Coverage (per context.md §22)
| Test Category | Required | Implemented |
|---------------|----------|-------------|
| Unit tests per module | 14+ modules | 0 |
| Integration tests | Full pipeline, multi-hospital, quarantine, atomic write | 0 |
| Adversarial/Red-team | Canary, false-merge, medical corruption, privacy attack, performance, determinism, secret rotation, resource limits | 0 |
| Organizer contract validation | validate_output.py runs | 0 (validator not available) |
| Performance tests | 2GB input < 900s, < 4GB RSS | 0 |

---

## 5. Dependency Status

### Core Dependencies (Required per context.md §20.1)
| Package | Purpose | Status |
|---------|---------|--------|
| `cryptography` | HMAC, AES-GCM | ❌ Not installed |
| `charset-normalizer` | Encoding detection | ❌ Not installed |
| `phonenumbers` | Phone validation | ❌ Not installed |
| `dateparser` | Date parsing | ❌ Not installed |
| `indic-transliteration` | Devanagari→Latin | ❌ Not installed |
| `fhir.resources` | FHIR R4 validation | ❌ Not installed |
| `jsonschema` | JSON schema validation | ❌ Not installed |
| `regex` | Enhanced regex (Unicode) | ❌ Not installed |
| `pandas` | CSV/TSV, vectorized ops | ❌ Not installed |
| `pyyaml` | Config parsing | ❌ Not installed |

### Optional/Conditional Dependencies
| Package | Purpose | Condition |
|---------|---------|-----------|
| `sklearn-crfsuite` | CRF name tagger | Only if >5% F1 gain over rule baseline |
| `scikit-learn` | Classical ML utilities | If CRF used |
| `rapidfuzz` | Fast string similarity | If Jaro-Winkler bottleneck |

### Excluded (Must Not Use)
- `torch`, `tensorflow`, `transformers`, `sentence-transformers`, `spacy` (large models)
- Any package pulling >50M parameter models
- Network-dependent packages

### Python Version
- Target: Python 3.11+ (organizer environment)
- Current: Not verified (no implementation to test)

---

## 6. Submission Contract Status

| Requirement | Spec Reference | Status | Evidence |
|-------------|----------------|--------|----------|
| `raksha.toml` exists | §3.4 | ❌ Missing | File does not exist |
| `raksha.toml` exact keys | §3.4 | ❌ Missing | — |
| `main.py` exists | §3.5 | ❌ Missing | File does not exist |
| CLI: `python main.py --input --output` | §3.5 | ❌ Missing | — |
| `RAKSHA_SECRET` from env only | §3.4, §12.4 | ❌ Missing | No code to read env |
| Output structure: `sanitized/`, `report.json`, `records.jsonl` | §3.6 | ❌ Missing | No pipeline |
| `report.json` schema (SHA-256 keys, exact fields) | §3.6.2, §16.2 | ❌ Missing | No generator |
| `records.jsonl` schema (file, loc, patient) | §3.6.3, §16.3 | ❌ Missing | No generator |
| Sanitized files preserve format & structure | §3.6.1 | ❌ Missing | No serializer |
| Quarantine behavior (explicit, never silent) | §3.6.1, §17 | ❌ Missing | No quarantine logic |
| Offline execution (no network) | §3.2 | ❓ Unknown | No code to verify |
| CPU-only, 2 CPUs, 4GB RAM, 15 min | §3.2 | ❓ Unknown | No code to measure |
| No LLMs / transformers >50M params | §3.3 | ✅ Compliant | No ML dependencies planned |
| Deterministic (same input+secret = byte-identical) | §18 | ❓ Unknown | No pipeline |
| Secret rotation (different secret = different pseudonyms) | §12.1, §18.2 | ❓ Unknown | No pseudonymization |

---

## 7. Official Assets Found / Not Found

| Asset | Expected Location | Found | Notes |
|-------|-------------------|-------|-------|
| `validate_output.py` | Workspace / organizer repo | ❌ Not found | Critical blocker for official validation |
| `dev/input/` (practice dataset) | Workspace / organizer repo | ❌ Not found | Critical for detection/linkage tuning |
| Official rules/spec document | Organizer package | ❌ Not found | Must be obtained from organizer |

**Action Required:** Obtain organizer assets from competition organizers. Cannot claim official `CONTRACT OK` without `validate_output.py`.

---

## 8. Risks and Implementation Priorities

### Critical Risks (P0 — Blockers)
| Risk | Impact | Mitigation |
|------|--------|------------|
| No `validate_output.py` | Cannot verify official `CONTRACT OK` | Build self-validator from contract spec; request from organizers |
| No `dev/input/` practice data | No ground truth for detection/linkage tuning | Generate synthetic fixtures with known labels |
| No `raksha.toml` / `main.py` | Cannot submit | Create immediately in Phase 0/1 |
| No implementation code | 100% gap | Begin Phase 1 (contracts) → Phase 2 (intake) immediately |
| FHIR complexity | References, extensions, contained leak PII | Deep traversal test suite; quarantine on validation fail |
| Multilingual false merges | "Rahul Sharma" (Hindi) ≠ "Rahul Sharma" (different person) | Strict cannot-link (DOB, gender, hard IDs); high threshold |
| Medical veto over-redaction | Real patient name "Parkinson" preserved as disease | Context window + role markers override veto |
| Performance at scale | 2GB/15min/4GB hard limits | Streaming, blocking, profiling from Day 1 |

### High-Priority Decisions Needed (P0)
1. **Gazetteer sources** — Census 2011? Voter rolls? Wikipedia? (affects bundling/licensing)
2. **Location mapping** — Census 2011 CSV bundled? Custom? (affects `privacy/gazetteer.py`)
3. **FHIR attachments** — Quarantine vs. text extraction? (unresolved per context.md §24.2)
4. **Output filename scheme** — SHA-256 prefix + ext vs. UUID?
4. **Age reference date** — Earliest record date vs. fixed epoch?
5. **Team name** — For `raksha.toml` `name` field

---

## 9. Recommended Phase 0.2 Actions (Immediate)

### Must Complete Before Any Implementation
1. **Initialize project git repo** in `C:\Users\samri\lockmate`
2. **Create `raksha.toml`** with placeholder team name:
   ```toml
   [submission]
   name = "lockmate-team"  # Team to update
   setup = "pip install -r requirements.txt"
   run = "python main.py --input {input} --output {output}"
   ```
3. **Create minimal `main.py`** scaffold:
   - `argparse` for `--input` / `--output`
   - `RAKSHA_SECRET` env var read (validate ≥32 bytes)
   - Top-level try/except with quarantine-all fallback
   - Stub pipeline call
4. **Create `requirements.txt`** with pinned core dependencies
5. **Create `src/secret_wards/contracts.py`** with all 12 frozen dataclasses
6. **Produce deliverables:**
   - `REPO_INVENTORY.md`
   - `CONTRACT_CHECKLIST.md` (every organizer requirement mapped)
   - `ASSET_REPORT.md` (validator + dataset status)
   - `BACKLOG.md` (prioritized, with owners)

### Architecture Decisions to Freeze (Phase 1)
- Gazetteer data sources and bundling strategy
- Location mapping data source
- FHIR attachment handling policy
- Output filename scheme
- Age reference date convention
- CRF inclusion criteria (rule baseline first)

---

## 10. Conclusion

**What is working:** Documentation only — comprehensive engineering context and execution plan.

**What is missing:** 100% of implementation, all submission files, all tests, all organizer assets.

**What must be verified before implementation:** Organizer assets availability; team name for `raksha.toml`; gazetteer/location data sources.

**What to avoid:** Do not implement any detection/logic before `contracts.py` interfaces are frozen and approved. Do not install dependencies until `requirements.txt` is created with pinned versions. Do not claim official validation without `validate_output.py`.

---

**Next Step:** Begin Phase 0.2 — Create submission files (`raksha.toml`, `main.py`, `requirements.txt`), initialize git, produce contract checklist, and implement `src/secret_wards/contracts.py`.