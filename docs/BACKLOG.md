# LOCKMATE — Prioritized Implementation Backlog

**Date:** 2026-11-26  
**Status:** Phase 0 — Baseline established, ready for Sprint 0 execution

---

## Backlog Format

| Field | Description |
|-------|-------------|
| **ID** | Unique task identifier (Phase.Task) |
| **Priority** | P0 (blocker), P1 (required), P2 (optional) |
| **Phase** | Engineering phase (0-14) |
| **Owner** | Agent role responsible |
| **Dependencies** | Task IDs that must complete first |
| **Acceptance Criteria** | Measurable definition of done |
| **Status** | NOT STARTED / IN PROGRESS / DONE / BLOCKED |

---

## Sprint 0: Foundation & Contract Audit (Phase 0) — **P0**

| ID | Task | Priority | Phase | Owner | Dependencies | Acceptance Criteria | Status |
|----|------|----------|-------|-------|--------------|---------------------|--------|
| 0.1 | Initialize git repo in project directory | P0 | 0 | Lead | None | `git log --oneline` shows commits; `.gitignore` present | NOT STARTED |
| 0.2 | Create `raksha.toml` with placeholder team name | P0 | 0 | Lead | None | File exists; keys match spec exactly; `name` = "lockmate-team" (placeholder) | NOT STARTED |
| 0.3 | Create minimal `main.py` scaffold | P0 | 0 | Lead | 0.2 | CLI parses `--input` `--output`; reads `RAKSHA_SECRET`; validates ≥32 bytes; stub pipeline call | NOT STARTED |
| 0.4 | Create `requirements.txt` with pinned dependencies | P0 | 0 | Lead | None | All core deps from context.md §20.1 listed with version constraints | NOT STARTED |
| 0.5 | Create `config/policy.yaml` with defaults | P0 | 0 | Lead | None | All config sections from architecture.md §7.1 present | NOT STARTED |
| 0.6 | Request organizer assets (`validate_output.py`, `dev/input/`) | P0 | 0 | Lead | None | Email sent; responses tracked in `ASSET_REPORT.md` | NOT STARTED |
| 0.7 | Produce `REPO_INVENTORY.md` | P0 | 0 | Auditor | None | All files cataloged; official vs generated labeled | ✅ DONE |
| 0.8 | Produce `CONTRACT_CHECKLIST.md` | P0 | 0 | Auditor | None | Every organizer requirement mapped; 112 items tracked | ✅ DONE |
| 0.9 | Produce `ASSET_REPORT.md` | P0 | 0 | Auditor | 0.6 | Validator/dataset status documented | ✅ DONE |
| 0.10 | Define shared interfaces (`contracts.py`) | P0 | 0 | Orchestrator | 0.1-0.9 | All 12 dataclasses defined; frozen; type hints; serialization | NOT STARTED |
| 0.11 | Produce `BACKLOG.md` | P0 | 0 | Orchestrator | 0.1-0.10 | Every task has owner, deps, acceptance criteria | 🔄 IN PROGRESS |

---

## Sprint 1: Shared Models & Interfaces (Phase 1) — **P0**

| ID | Task | Priority | Phase | Owner | Dependencies | Acceptance Criteria | Status |
|----|------|----------|-------|-------|--------------|---------------------|--------|
| 1.1 | Implement `InputFile`, `FormatType`, `RecordLocation` | P0 | 1 | Orchestrator | 0.10 | All fields present; `FormatType` enum complete; frozen | NOT STARTED |
| 1.2 | Implement `ParsedDocument`, `UnifiedRecord`, `FieldValue`, `FieldType` | P0 | 1 | Orchestrator | 1.1 | Offset maps typed; `RecordStatus` enum; frozen | NOT STARTED |
| 1.3 | Implement `PIISpan`, `PIIType`, `MedicalSpan`, `MedicalType` | P0 | 1 | Detection | 1.1 | Confidence 0-1; `PIIType` covers all §9.3 identifiers | NOT STARTED |
| 1.4 | Implement `IdentityCandidate`, `PatientCluster`, `PrivacyTransformation` | P0 | 1 | Linkage | 1.1 | `canonical_identity` format documented | NOT STARTED |
| 1.5 | Implement `SanitizedRecord`, `QuarantineResult`, `ProcessingMetrics` | P0 | 1 | Output | 1.1 | `QuarantineReason` enum complete | NOT STARTED |
| 1.6 | Add `to_dict()`/`from_dict()` serialization for all | P0 | 1 | Orchestrator | 1.1-1.5 | JSON round-trip preserves all fields | NOT STARTED |
| 1.7 | Create `src/secret_wards/__init__.py` exporting contracts | P0 | 1 | Orchestrator | 1.6 | `from secret_wards.contracts import ...` works | NOT STARTED |
| 1.8 | Write `tests/unit/test_contracts.py` | P0 | 1 | Orchestrator | 1.7 | All dataclass instantiation/serialization tests pass | NOT STARTED |

---

## Sprint 2: Secure Intake & Ingestion (Phase 2) — **P0**

| ID | Task | Priority | Phase | Owner | Dependencies | Acceptance Criteria | Status |
|----|------|----------|-------|-------|--------------|---------------------|--------|
| 2.1 | File discovery walker (`intake/discovery.py`) | P0 | 2 | Ingestion | 1.8 | Symlinks resolved; path traversal blocked; size/nesting limits; 1000 files | NOT STARTED |
| 2.2 | SHA-256 streaming calculator (`intake/hashing.py`) | P0 | 2 | Ingestion | 2.1 | Matches `sha256sum`; low memory; empty/100MB files | NOT STARTED |
| 2.3 | Format classifier (`intake/classifier.py`) | P0 | 2 | Ingestion | 2.1 | Extension + content sniffing; UNKNOWN for unsupported | NOT STARTED |
| 2.4 | Encoding detector (`intake/encoding.py`) | P0 | 2 | Ingestion | 2.1 | `charset-normalizer` primary; no Latin-1 fallback; UTF-8/16/CP1252 | NOT STARTED |
| 2.5 | CSV/TSV parser (`parsers/csv_parser.py`) | P0 | 2 | Ingestion | 2.3, 2.4 | Auto-delimiter; header inference; shifted cols; 10k rows | NOT STARTED |
| 2.6 | JSON parser (`parsers/json_parser.py`) | P0 | 2 | Ingestion | 2.3, 2.4 | Streaming; nested walk; JSON Pointer; 50MB stream | NOT STARTED |
| 2.7 | Plain text parser (`parsers/text_parser.py`) | P0 | 2 | Ingestion | 2.3, 2.4 | Line/para segmentation; offset maps | NOT STARTED |
| 2.8 | FHIR R4 parser (`parsers/fhir_parser.py`) | P0 | 2 | Ingestion | 2.3, 2.4 | `fhir.resources` validation; refs/extensions/contained/attachments | NOT STARTED |
| 2.9 | Quarantine classifier (`intake/quarantine.py`) | P0 | 2 | Ingestion | 2.5-2.8 | Reason codes from §17.1; original copied to `quarantined/` | NOT STARTED |
| 2.10 | Intake pipeline integration (`intake/pipeline.py`) | P0 | 2 | Ingestion | 2.1-2.9 | Mixed format dir → URM + quarantine; metrics per file | NOT STARTED |
| 2.11 | Write unit tests for intake module | P0 | 2 | Ingestion | 2.1-2.10 | All intake unit tests pass | NOT STARTED |

---

## Sprint 3: Basic Sanitization Pipeline (Phase 3) — **P0**

| ID | Task | Priority | Phase | Owner | Dependencies | Acceptance Criteria | Status |
|----|------|----------|-------|-------|--------------|---------------------|--------|
| 3.1 | Placeholder PII detector (`detection/placeholder.py`) | P0 | 3 | Detection | 1.8, 2.10 | Regex: email, phone, PAN, 12-digit, dates | NOT STARTED |
| 3.2 | Placeholder medical veto (`clinical/placeholder.py`) | P0 | 3 | Clinical | 1.8 | Regex: dosages, frequencies, disease names | NOT STARTED |
| 3.3 | Span merger + veto (`detection/merger.py`) | P0 | 3 | Detection | 3.1, 3.2 | Medical spans veto overlapping PII | NOT STARTED |
| 3.4 | Text replacer (`transform/replacer.py`) | P0 | 3 | Detection | 1.8 | Offset-map aware; preserves structure | NOT STARTED |
| 3.5 | Structured field sanitizer (`transform/structured.py`) | P0 | 3 | Detection | 3.3 | CSV/JSON/FHIR fields replaced | NOT STARTED |
| 3.6 | Serializer (`output/serializer.py`) | P0 | 3 | Output | 1.8 | Format-preserving, UTF-8, PSN-TEMP placeholder | NOT STARTED |
| 3.7 | Filename sanitizer (`output/namer.py`) | P0 | 3 | Output | 1.8 | SHA-256 prefix + ext; no PII in path | NOT STARTED |
| 3.8 | Atomic writer (`output/writer.py`) | P0 | 3 | Output | 1.8 | Temp → rename; cleanup on error | NOT STARTED |
| 3.9 | Basic pipeline integration (`pipeline/basic.py`) | P0 | 3 | Orchestrator | 2.10, 3.1-3.8 | CSV/JSON/Text → sanitized + reports | NOT STARTED |
| 3.10 | Write integration tests for basic pipeline | P0 | 3 | All | 3.9 | 10-file mixed dir → structural CONTRACT OK | NOT STARTED |

---

## Sprint 4: Production PII Detection (Phase 4) — **P0**

| ID | Task | Priority | Phase | Owner | Dependencies | Acceptance Criteria | Status |
|----|------|----------|-------|-------|--------------|---------------------|--------|
| 4.1 | Unicode normalization (`detection/normalize.py`) | P0 | 4 | Detection | 1.8 | NFC, Devanagari digits, ZWJ/ZWNJ, offset maps | NOT STARTED |
| 4.2 | Structured field scanner (`detection/structured.py`) | P0 | 4 | Detection | 1.8, 2.10 | Headers, JSON keys, FHIR paths, filenames | NOT STARTED |
| 4.3 | Phone detector (`detection/identifiers.py`) | P0 | 4 | Detection | 4.1 | `phonenumbers` + regex; Devanagari digits | NOT STARTED |
| 4.4 | Aadhaar detector (`detection/identifiers.py`) | P0 | 4 | Detection | 4.1 | 12 digits + Verhoeff checksum | NOT STARTED |
| 4.5 | ABHA detector (`detection/identifiers.py`) | P0 | 4 | Detection | 4.1 | 14 digits; format validation | NOT STARTED |
| 4.6 | PAN detector (`detection/identifiers.py`) | P0 | 4 | Detection | 4.1 | Regex `^[A-Z]{5}[0-9]{4}[A-Z]$` | NOT STARTED |
| 4.7 | UHID/MRN detector (`detection/identifiers.py`) | P0 | 4 | Detection | 4.1, 4.2 | Context-aware patterns | NOT STARTED |
| 4.8 | Email/URL detector (`detection/identifiers.py`) | P0 | 4 | Detection | 4.1 | RFC 5322 + URL regex | NOT STARTED |
| 4.9 | PIN/Address detector (`detection/identifiers.py`) | P0 | 4 | Detection | 4.1 | 6-digit PIN; address keywords | NOT STARTED |
| 4.10 | Date detector (`detection/identifiers.py`) | P0 | 4 | Detection | 4.1 | `dateparser` + contextual classification | NOT STARTED |
| 4.11 | Honorific/Relationship triggers (`detection/names.py`) | P0 | 4 | Detection | 4.1 | S/o, D/o, W/o, C/O, श्री, पुत्र, देखभाल | NOT STARTED |
| 4.12 | Gazetteer loader (`detection/gazetteer.py`) | P0 | 4 | Detection | 1.8 | Offline, Latin+Devanagari, transliteration variants | NOT STARTED |
| 4.13 | Transliteration + Double Metaphone (`detection/transliterate.py`) | P0 | 4 | Detection | 4.1 | indic-transliteration → IAST → Latin → Double Metaphone | NOT STARTED |
| 4.14 | Name detector (`detection/names.py`) | P0 | 4 | Detection | 4.1, 4.11, 4.12, 4.13 | Gazetteer + trigger proximity + role classification | NOT STARTED |
| 4.15 | CRF tagger (`detection/crf_tagger.py`) | P0 | 4 | Detection | 4.14 | **Conditional**: only if >5% F1 gain; <50M params | NOT STARTED |
| 4.16 | Residual scanner (`detection/residual.py`) | P0 | 4 | Detection | 4.1-4.15 | Re-scans output for stragglers | NOT STARTED |
| 4.17 | Detection engine (`detection/engine.py`) | P0 | 4 | Detection | 4.1-4.16 | Runs all detectors; merges spans; confidence scoring | NOT STARTED |
| 4.18 | Write unit/integration tests for detection | P0 | 4 | Detection | 4.1-4.17 | PII detection recall ≥95%, precision ≥90%; medical veto ≥98% | NOT STARTED |

---

## Sprint 5: Clinical Preservation (Phase 5) — **P0**

| ID | Task | Priority | Phase | Owner | Dependencies | Acceptance Criteria | Status |
|----|------|----------|-------|-------|--------------|---------------------|--------|
| 5.1 | Drug/strength/dosage detector (`clinical/drugs.py`) | P0 | 5 | Clinical | 1.8, 4.1 | Gazetteer (INN + India brands) + regex | NOT STARTED |
| 5.2 | Lab/vital/unit detector (`clinical/labs.py`) | P0 | 5 | Clinical | 5.1 | LOINC-derived + patterns | NOT STARTED |
| 5.3 | Diagnosis/procedure detector (`clinical/diagnoses.py`) | P0 | 5 | Clinical | 5.1 | ICD-10 + eponyms (Parkinson's, Alzheimer's) | NOT STARTED |
| 5.4 | Doctor context detector (`clinical/doctors.py`) | P0 | 5 | Clinical | 5.1 | Dr./Doctor + clinical context | NOT STARTED |
| 5.5 | Medical veto integration (`clinical/veto.py`) | P0 | 5 | Clinical | 4.3, 5.1-5.4 | Span-level veto; adjacency re-check | NOT STARTED |
| 5.6 | Clinical preservation tests | P0 | 5 | Clinical | 5.5 | 0% corruption; doctor names preserved; relative redacted | NOT STARTED |

---

## Sprint 6: Output Security Gate & Reporting (Phase 6) — **P0**

| ID | Task | Priority | Phase | Owner | Dependencies | Acceptance Criteria | Status |
|----|------|----------|-------|-------|--------------|---------------------|--------|
| 6.1 | Residual PII scanner (`output/residual_scan.py`) | P0 | 6 | Output | 3.10, 4.18 | Detectors on output; any hit → fail | NOT STARTED |
| 6.2 | Canary checker (`output/canary.py`) | P0 | 6 | Output | 3.10 | Scans for `LOCKMATE_CANARY_*` | NOT STARTED |
| 6.3 | Clinical integrity verifier (`output/clinical_check.py`) | P0 | 6 | Output | 3.10, 5.6 | Pre/post medical span comparison | NOT STARTED |
| 6.4 | Schema validator (`output/schema_check.py`) | P0 | 6 | Output | 3.10 | CSV/JSON/FHIR R4 valid | NOT STARTED |
| 6.5 | Filename/metadata scanner (`output/meta_check.py`) | P0 | 6 | Output | 3.10 | No PII in output paths/keys | NOT STARTED |
| 6.6 | Pseudonym consistency checker (`output/pseudonym_check.py`) | P0 | 6 | Output | 3.10, 8.5 | Same patient = same pseudonym in record + records.jsonl | NOT STARTED |
| 6.7 | Security gate orchestrator (`output/security_gate.py`) | P0 | 6 | Output | 6.1-6.6 | All checks PASS; FAIL → quarantine | NOT STARTED |
| 6.8 | report.json generator (`output/report.py`) | P0 | 6 | Output | 2.10, 3.10 | Exact schema per §16.2; hash keys; accurate totals | NOT STARTED |
| 6.9 | records.jsonl generator (`output/records.py`) | P0 | 6 | Output | 3.10, 7.7, 8.5 | Exact schema per §16.3; location conventions; null for uncertain | NOT STARTED |
| 6.10 | Output pipeline (`output/pipeline.py`) | P0 | 6 | Output | 6.7-6.9 | Atomic write of all three outputs | NOT STARTED |
| 6.11 | Self-validator implementation | P0 | 6 | Red-Team | 6.10 | Mirrors organizer spec; validates all checks | NOT STARTED |

---

## Sprint 7: Identity Resolution & Linkage (Phase 7) — **P1**

| ID | Task | Priority | Phase | Owner | Dependencies | Acceptance Criteria | Status |
|----|------|----------|-------|-------|--------------|---------------------|--------|
| 7.1 | Blocking key generator (`linkage/blocking.py`) | P1 | 7 | Linkage | 4.18 | All blocking keys from §11.2 | NOT STARTED |
| 7.2 | Candidate pair generator (`linkage/candidates.py`) | P1 | 7 | Linkage | 7.1 | Deduped; max pairs controlled | NOT STARTED |
| 7.3 | Pairwise scorer (`linkage/scoring.py`) | P1 | 7 | Linkage | 7.2, 4.18 | Fellegi-Sunter features; configurable weights | NOT STARTED |
| 7.4 | Cannot-link constraints (`linkage/constraints.py`) | P1 | 7 | Linkage | 7.3 | Conflicting hard IDs → cannot_link | NOT STARTED |
| 7.5 | Conservative clusterer (`linkage/clustering.py`) | P1 | 7 | Linkage | 7.3, 7.4 | Greedy + consistency check; no transitive closure | NOT STARTED |
| 7.6 | Canonical identity builder (`linkage/canonical.py`) | P1 | 7 | Linkage | 7.5 | Sorted reliable identifiers | NOT STARTED |
| 7.7 | Linkage pipeline (`linkage/pipeline.py`) | P1 | 7 | Linkage | 7.1-7.6 | 500-record multi-hospital; P/R/F1 measured | NOT STARTED |

---

## Sprint 8: Pseudonymization (Phase 8) — **P1**

| ID | Task | Priority | Phase | Owner | Dependencies | Acceptance Criteria | Status |
|----|------|----------|-------|-------|--------------|---------------------|--------|
| 8.1 | Secret loader (`crypto/secret.py`) | P1 | 8 | Linkage | 0.3 | Reads `RAKSHA_SECRET` from env; validates ≥32 bytes; never logs | NOT STARTED |
| 8.2 | HMAC pseudonym service (`crypto/pseudonym.py`) | P1 | 8 | Linkage | 8.1, 7.6 | Domain separation; PSN-XXXX; determinism | NOT STARTED |
| 8.3 | Date-shift derivation (`crypto/date_shift.py`) | P1 | 8 | Linkage | 8.1 | Per-patient offset [-365,+365] from HMAC | NOT STARTED |
| 8.4 | Pseudonym injector (`crypto/injector.py`) | P1 | 8 | Linkage | 8.2, 3.6 | Injects into patient ID field per format | NOT STARTED |
| 8.5 | Pseudonym integration | P1 | 8 | Linkage | 8.2-8.4 | Clusters → pseudonyms; sanitized records updated | NOT STARTED |

---

## Sprint 9: Date & Age Transformations (Phase 9) — **P1**

| ID | Task | Priority | Phase | Owner | Dependencies | Acceptance Criteria | Status |
|----|------|----------|-------|-------|--------------|---------------------|--------|
| 9.1 | Date field identifier (`privacy/date_fields.py`) | P1 | 9 | Privacy | 4.18 | Finds all DATE-type PII + structured date fields | NOT STARTED |
| 9.2 | Date shifter (`privacy/date_shift.py`) | P1 | 9 | Privacy | 8.3, 9.1 | Applies per-patient offset; preserves intervals | NOT STARTED |
| 9.3 | Age generalizer (`privacy/age_bands.py`) | P1 | 9 | Privacy | 4.18 | Bands per §13.2; round down; 90+ ceiling | NOT STARTED |
| 9.4 | Privacy integration (`privacy/pipeline.py`) | P1 | 9 | Privacy | 9.2, 9.3 | Updates URM before serialization | NOT STARTED |

---

## Sprint 10: Location & Rare-Value Protection (Phase 10) — **P1**

| ID | Task | Priority | Phase | Owner | Dependencies | Acceptance Criteria | Status |
|----|------|----------|-------|-------|--------------|---------------------|--------|
| 10.1 | Location gazetteer loader (`privacy/gazetteer.py`) | P1 | 10 | Privacy | 1.8 | Census 2011 CSV bundled; <100MB | NOT STARTED |
| 10.2 | Location generalizer (`privacy/location.py`) | P1 | 10 | Privacy | 10.1 | Village→district, PIN→3-digit, rare→state | NOT STARTED |
| 10.3 | Equivalence class builder (`privacy/equivalence.py`) | P1 | 10 | Privacy | 9.4, 10.2 | Groups by QI tuple; counts per class | NOT STARTED |
| 10.4 | Rare suppressor (`privacy/suppression.py`) | P1 | 10 | Privacy | 10.3 | Iterative: suppress rarest → generalize age → location | NOT STARTED |
| 10.5 | Attacker simulation (`redteam/attacker_sim.py`) | P1 | 10 | Red-Team | 10.2, 10.4 | Synthetic voter roll; <5% unique re-ID | NOT STARTED |
| 10.6 | Privacy pipeline (`privacy/pipeline.py`) | P1 | 10 | Privacy | 9.4, 10.2, 10.4 | Applies location + rare suppression; updates URM | NOT STARTED |

---

## Sprint 11: FHIR & Extended Format Hardening (Phase 11) — **P1**

| ID | Task | Priority | Phase | Owner | Dependencies | Acceptance Criteria | Status |
|----|------|----------|-------|-------|--------------|---------------------|--------|
| 11.1 | FHIR reference scanner (`parsers/fhir_references.py`) | P1 | 11 | Ingestion | 2.8, 4.18 | References, contained, extensions scanned | NOT STARTED |
| 11.2 | FHIR attachment handler (`parsers/fhir_attachments.py`) | P1 | 11 | Ingestion | 2.8 | PDF/image → quarantine; text → extract+scan | NOT STARTED |
| 11.3 | FHIR metadata scanner (`detection/fhir_meta.py`) | P1 | 11 | Detection | 2.8, 4.18 | meta.tag, meta.profile, meta.security | NOT STARTED |
| 11.4 | FHIR serializer validator (`output/fhir_validator.py`) | P1 | 11 | Output | 3.6, 6.4 | `fhir.resources` round-trip validation | NOT STARTED |
| 11.5 | FHIR integration test | P1 | 11 | Ingestion | 11.1-11.4 | Complex Bundle → valid sanitized R4 | NOT STARTED |

---

## Sprint 12: Red-Team Evaluation & Hardening (Phase 12) — **P1**

| ID | Task | Priority | Phase | Owner | Dependencies | Acceptance Criteria | Status |
|----|------|----------|-------|-------|--------------|---------------------|--------|
| 12.1 | Adversarial fixture generator (`redteam/fixtures.py`) | P1 | 12 | Red-Team | 0.10 | Generates all adversarial types | NOT STARTED |
| 12.2 | Canary injection test (`redteam/canary_test.py`) | P1 | 12 | Red-Team | 6.2 | Zero canary leakage | NOT STARTED |
| 12.3 | False-merge test suite (`redteam/false_merge.py`) | P1 | 12 | Red-Team | 7.7 | <1% false merge | NOT STARTED |
| 12.4 | Medical corruption test (`redteam/medical_corruption.py`) | P1 | 12 | Red-Team | 5.6 | 0% corruption | NOT STARTED |
| 12.5 | Privacy attack evaluation (`redteam/privacy_attack.py`) | P1 | 12 | Red-Team | 10.5 | Re-ID metrics documented | NOT STARTED |
| 12.6 | Performance profiling (`redteam/performance.py`) | P1 | 12 | Red-Team | 2.10-11.5 | 2GB < 900s, < 4GB RSS | NOT STARTED |
| 12.7 | Determinism verification (`redteam/determinism.py`) | P1 | 12 | Red-Team | 8.5 | 3 runs same secret = byte-identical | NOT STARTED |
| 12.8 | Secret rotation verification (`redteam/secret_rotation.py`) | P1 | 12 | Red-Team | 8.5 | Different secrets → different pseudonyms/shifts | NOT STARTED |
| 12.9 | Resource limit enforcement (`redteam/resource_limits.py`) | P1 | 12 | Red-Team | 2.1 | Oversized/nested/bomb → quarantine | NOT STARTED |
| 12.10 | Security hardening review (`SECURITY_REVIEW.md`) | P1 | 12 | Red-Team | All | Bandit + semgrep clean | NOT STARTED |

---

## Sprint 13: Performance Optimization (Phase 13) — **P1**

| ID | Task | Priority | Phase | Owner | Dependencies | Acceptance Criteria | Status |
|----|------|----------|-------|-------|--------------|---------------------|--------|
| 13.1 | Profile hot paths | P1 | 13 | All | 12.6 | Top 5 consumers identified | NOT STARTED |
| 13.2 | Optimize blocking | P1 | 13 | Linkage | 13.1 | Candidate pairs reduced 50%+ | NOT STARTED |
| 13.3 | Vectorize detection | P1 | 13 | Detection | 13.1 | Detection time -30% | NOT STARTED |
| 13.4 | Streaming serialization | P1 | 13 | Output | 13.1 | Peak RSS -25% | NOT STARTED |
| 13.5 | Parallel file processing | P1 | 13 | Ingestion | 13.1 | Intake time -40% (2 workers) | NOT STARTED |
| 13.6 | Memory cleanup | P1 | 13 | All | 13.1 | No memory growth across files | NOT STARTED |

---

## Sprint 14: Frontend & Demo (Phase 14) — **P2 (Optional)**

| ID | Task | Priority | Phase | Owner | Dependencies | Acceptance Criteria | Status |
|----|------|----------|-------|-------|--------------|---------------------|--------|
| 14.1 | Demo data curation | P2 | 14 | Frontend | 12.1 | 3 hospitals, 1 patient across scripts | NOT STARTED |
| 14.2 | Pipeline visualization | P2 | 14 | Frontend | 0-13 | Stage progression, timings, highlights | NOT STARTED |
| 14.3 | Before/After viewer | P2 | 14 | Frontend | 14.2 | Side-by-side diff with highlights | NOT STARTED |
| 14.4 | Linkage explorer | P2 | 14 | Frontend | 14.2 | Graph view of clusters | NOT STARTED |
| 14.5 | Privacy dashboard | P2 | 14 | Frontend | 14.2 | k-anonymity, re-ID rate, clinical utility | NOT STARTED |
| 14.6 | Verifier panel | P2 | 14 | Frontend | 14.2 | Runs validator, shows CONTRACT OK | NOT STARTED |
| 14.7 | 5-min demo script | P2 | 14 | Orchestrator | 14.1-14.6 | Matches context.md §23.3 timing | NOT STARTED |

---

## Submission Readiness Tasks (Cross-Phase)

| ID | Task | Priority | Phase | Owner | Dependencies | Acceptance Criteria | Status |
|----|------|----------|-------|-------|--------------|---------------------|--------|
| S.1 | Create `README.md` with all required sections | P0 | 8 | Lead | 0.1-6.11 | Mission, setup, offline exec, arch diagram, pipeline, detection, linkage, pseudonym, privacy, attacker, security, trade-offs, limitations, deps, models, tests, submission cmd | NOT STARTED |
| S.2 | Generate two-page Project Brief PDF | P0 | 8 | Lead | S.1 | Organizer required topics; no unmeasured claims | NOT STARTED |
| S.3 | Verify root layout matches submission spec | P0 | 8 | Lead | All | `raksha.toml`, `requirements.txt`, `README.md`, `main.py`, `config/`, `src/` | NOT STARTED |
| S.4 | Verify Git status clean for submission | P0 | 8 | Lead | 0.1 | No untracked implementation files; all committed | NOT STARTED |
| S.5 | Run official validator (if available) | P0 | 9 | Lead | 6.11 | `python3 validate_output.py --input dev/input --output my_output/` → `CONTRACT OK` | NOT STARTED |
| S.6 | Produce final compliance report | P0 | 10 | Lead | All | Compliance %, mandatory complete/remaining, files created/modified, modules, tests, validator result, offline exec, resources, attacker sim, limitations, exact run cmd, remaining actions | NOT STARTED |

---

## Status Summary

| Phase | Tasks | NOT STARTED | IN PROGRESS | DONE | BLOCKED |
|-------|-------|-------------|-------------|------|---------|
| 0: Foundation | 11 | 8 | 1 | 3 | 0 |
| 1: Shared Models | 8 | 8 | 0 | 0 | 0 |
| 2: Intake & Ingestion | 11 | 11 | 0 | 0 | 0 |
| 3: Basic Sanitization | 10 | 10 | 0 | 0 | 0 |
| 4: PII Detection | 18 | 18 | 0 | 0 | 0 |
| 5: Clinical Preservation | 6 | 6 | 0 | 0 | 0 |
| 6: Output Security & Reporting | 11 | 11 | 0 | 0 | 0 |
| 7: Identity Resolution | 7 | 7 | 0 | 0 | 0 |
| 8: Pseudonymization | 5 | 5 | 0 | 0 | 0 |
| 9: Date & Age | 4 | 4 | 0 | 0 | 0 |
| 10: Location & Rare-Value | 6 | 6 | 0 | 0 | 0 |
| 11: FHIR Hardening | 5 | 5 | 0 | 0 | 0 |
| 12: Red-Team Evaluation | 10 | 10 | 0 | 0 | 0 |
| 13: Performance Optimization | 6 | 6 | 0 | 0 | 0 |
| 14: Frontend & Demo | 7 | 7 | 0 | 0 | 0 |
| Submission Readiness | 6 | 6 | 0 | 0 | 0 |
| **TOTAL** | **131** | **127** | **1** | **3** | **0** |

---

**Next Immediate Action:** Execute Sprint 0 tasks (0.1-0.6, 0.10-0.11) to establish runnable foundation.

---

**END OF BACKLOG**