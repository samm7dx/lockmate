# LOCKMATE — Master Engineering Execution Plan

**Document Status:** Authoritative multi-agent execution plan  
**Track:** Yugaantar DevForge — Track 3: Secret Wards  
**Primary Reference:** `context.md` (single source of truth)  
**Implementation Target:** Offline, CPU-only, multilingual healthcare privacy firewall  
**Last Updated:** 2026-11-26

---

## 1. Executive Technical Strategy

LOCKMATE is engineered as a **contract-first, attack-focused privacy firewall**. The strategy prioritizes:

1. **Exact Organizer Contract Compliance** — Every output field, CLI flag, config key, and environment variable matches the specification. Non-negotiable.
2. **Working Vertical Slice First** — End-to-end pipeline that sanitizes CSV/JSON/text and passes validation, before adding multilingual detection, linkage, or advanced privacy.
3. **Conservative Identity Resolution** — False merge (two patients → one pseudonym) is catastrophic; missed link is acceptable. High thresholds, cannot-link constraints, no transitive closure.
4. **Contextual Medical Preservation** — Span-level veto, not blanket whitelist. Clinical values survive adjacent to redacted names.
5. **Independent Verification** — Output security gate separate from detection engine. Canary testing on every run.
6. **Measurable Privacy** — Attacker simulation with synthetic auxiliary data, k-anonymity diagnostics, clinical utility metrics.

**Differentiators (Must Demonstrate):**
| Differentiator | Evidence Required |
|----------------|-------------------|
| Cross-Script Identity Intelligence | Link patient across English/Hindi/Hinglish with stable pseudonym |
| Clinical Integrity Protection | Before/after showing medicine/dosage/diagnosis preserved |
| Attacker-Aware Privacy Shield | Quasi-identifier attack success measured before/after transforms |

---

## 2. Final Architecture Decisions

| Decision | Rationale | Source |
|----------|-----------|--------|
| **Unified Record Model (URM)** preserves structure for lossless serialization | Flattening to text breaks FHIR/JSON round-trip | `context.md` §6 |
| **Offset mappings** (normalized ↔ original) | Safe in-place replacement after Unicode normalization | `context.md` §9.1 |
| **Independent Output Security Gate** | Detector cannot validate its own output | `context.md` §6, §16 |
| **Conservative linkage: pairwise + cannot-link + greedy clustering** | Prevents transitive false merges | `context.md` §11 |
| **HMAC-SHA256 pseudonyms with domain separation** | Cryptographically sound, secret-dependent, deterministic | `context.md` §12 |
| **Per-patient date shift from HMAC** | Preserves intervals, hides exact dates, secret-dependent | `context.md` §13.1 |
| **Age bands + location hierarchy + rare suppression** | HIPAA-style generalization, measurable k-anonymity | `context.md` §13 |
| **No CRF until rule baseline measured** | Avoids wasted effort; <50M param rule if added | `context.md` §9.4, §24.2 |
| **Latin-1 never used as fallback** | Arbitrary binary → false text → leakage | `context.md` §4, §8.3 |
| **Streaming parsers for large files** | 4 GB RAM limit with 2 GB input | `context.md` §19 |
| **Atomic writes (temp → rename)** | No partial outputs exposed | `context.md` §16, §17 |
| **Structured logging only, PII-scrubbed** | No raw PII in logs/temp/reports | `context.md` §15 |

---

## 3. Implementation Phases (Dependency Order)

```
Phase 0: Foundation & Contract Audit          [P0] ──┐
Phase 1: Shared Models & Interfaces           [P0]    ├── All agents depend on these
Phase 2: Secure Intake & Ingestion            [P0]    │
Phase 3: Basic Sanitization (CSV/JSON/Text)   [P0]    │
Phase 4: PII Detection Engine                 [P0]    │
Phase 5: Clinical Preservation                [P0]    ├── Core detection pipeline
Phase 6: Output Security Gate & Reporting     [P0]    │
Phase 7: Identity Resolution & Linkage        [P1]    │
Phase 8: Pseudonymization                     [P1]    ├── Privacy pipeline
Phase 9: Date & Age Transformations           [P1]    │
Phase 10: Location & Rare-Value Protection    [P1]    │
Phase 11: FHIR & Extended Format Hardening    [P1]    │
Phase 12: Red-Team Evaluation & Hardening     [P1]    ├── Validation
Phase 13: Performance Optimization            [P1]    │
Phase 14: Frontend & Demonstration            [P2]    └── Optional
```

**Critical Path:** Phases 0-6 must complete before Phases 7-11 can integrate. Phase 12 validates all prior phases.

---

## 4. Detailed Phase Tasks

### Phase 0 — Foundation & Contract Audit (P0)

**Objective:** Establish ground truth. Verify official assets. Define shared interfaces.

| Task | Objective | Inputs | Expected Outputs | Dependencies | Owner | Files Affected | Acceptance Criteria | Tests Required |
|------|-----------|--------|------------------|--------------|-------|----------------|---------------------|----------------|
| 0.1 | Repository inventory | Workspace root | `REPO_INVENTORY.md` | None | Agent 1 (Contract Auditor) | — | All files cataloged; official vs team-generated labeled | Manual review |
| 0.2 | Read organizer rules & validator | Organizer repo/package | `CONTRACT_CHECKLIST.md` | None | Agent 1 | — | Every contract item mapped to implementation plan | Checklist review |
| 0.3 | Inspect `raksha.toml` | Existing file | Validated config | 0.1 | Agent 1 | `raksha.toml` | Keys match spec exactly; `run` command correct | Diff against spec |
| 0.4 | Inspect `main.py` | Existing file | Entry point analysis | 0.1 | Agent 1 | `main.py` | CLI signature matches; reads `RAKSHA_SECRET`; calls pipeline | Smoke test |
| 0.5 | Inspect `src/secret_wards/` | Existing modules | Module map | 0.1 | Agent 1 | `src/secret_wards/**` | All modules documented; interfaces identified | Import test |
| 0.6 | Run existing tests | Test suite | Test baseline | 0.1 | Agent 1 | `tests/**` | Current pass/fail recorded | `pytest -v` |
| 0.7 | CLI smoke test | `main.py`, sample input | `SMOKE_TEST.log` | 0.4 | Agent 1 | — | Runs without crash; produces output structure | Manual run |
| 0.8 | Locate official assets | Organizer package | `ASSET_REPORT.md` | 0.2 | Agent 1 | — | `validate_output.py`, `dev/input/` found or confirmed missing | File existence |
| 0.9 | Define shared interfaces | `context.md` §21 | `src/secret_wards/contracts.py` | 0.1-0.8 | Agent 0 (Orchestrator) | `contracts.py` | All 12 dataclasses defined; frozen where appropriate; type hints complete | Import + instantiation test |
| 0.10 | Prioritized backlog | All above | `BACKLOG.md` (ordered tasks) | 0.1-0.9 | Agent 0 | — | Every task has owner, dependencies, acceptance criteria | Review with all agents |

**Phase 0 Deliverables:** `REPO_INVENTORY.md`, `CONTRACT_CHECKLIST.md`, validated `raksha.toml`, `contracts.py`, `BACKLOG.md`  
**Phase 0 Acceptance:** All assumptions labelled (official/verified/recommended/unverified); interfaces approved by Agent 0.

---

### Phase 1 — Shared Models & Interfaces (P0)

**Objective:** Implement the 12 shared dataclasses from `context.md` §21 as the single integration contract.

| Task | Objective | Inputs | Expected Outputs | Dependencies | Owner | Files Affected | Acceptance Criteria | Tests Required |
|------|-----------|--------|------------------|--------------|-------|----------------|---------------------|----------------|
| 1.1 | Implement `InputFile`, `FormatType`, `RecordLocation` | `contracts.py` stub | Complete types | Phase 0.9 | Agent 0 | `contracts.py` | All fields present; `FormatType` enum complete | Unit: enum values, frozen immutability |
| 1.2 | Implement `ParsedDocument`, `UnifiedRecord`, `FieldValue`, `FieldType` | `contracts.py` | Complete types | 1.1 | Agent 0 | `contracts.py` | Offset maps typed correctly; `RecordStatus` enum | Unit: offset map round-trip |
| 1.3 | Implement `PIISpan`, `PIIType`, `MedicalSpan`, `MedicalType` | `contracts.py` | Complete types | 1.1 | Agent 3 (Detection) | `contracts.py` | Confidence 0-1; `PIIType` covers all §9.3 identifiers | Unit: span containment checks |
| 1.4 | Implement `IdentityCandidate`, `PatientCluster`, `PrivacyTransformation` | `contracts.py` | Complete types | 1.1 | Agent 4 (Linkage) | `contracts.py` | `canonical_identity` string format documented | Unit: cluster merge logic |
| 1.5 | Implement `SanitizedRecord`, `QuarantineResult`, `ProcessingMetrics` | `contracts.py` | Complete types | 1.1 | Agent 6 (Output) | `contracts.py` | `QuarantineReason` enum complete | Unit: metrics aggregation |
| 1.6 | Add serialization helpers | `contracts.py` | `to_dict()` / `from_dict()` for all | 1.1-1.5 | Agent 0 | `contracts.py` | JSON-roundtrip preserves all fields | Unit: round-trip test per type |
| 1.7 | Publish interface package | `contracts.py` | `secret_wards.contracts` importable | 1.6 | Agent 0 | `src/secret_wards/__init__.py` | All agents can `from secret_wards.contracts import ...` | Import test in each agent env |

**Phase 1 Deliverables:** Complete `src/secret_wards/contracts.py`  
**Phase 1 Acceptance:** All 12 dataclasses implementable by each agent without modification; serialization round-trips.

---

### Phase 2 — Secure Intake & Ingestion (P0)

**Objective:** Safe file discovery, SHA-256, format classification, parsing to URM.

| Task | Objective | Inputs | Expected Outputs | Dependencies | Owner | Files Affected | Acceptance Criteria | Tests Required |
|------|-----------|--------|------------------|--------------|-------|----------------|---------------------|----------------|
| 2.1 | File discovery walker | Input directory | `List[InputFile]` sorted by SHA-256 | Phase 1 | Agent 2 (Ingestion) | `src/secret_wards/intake/discovery.py` | Symlinks resolved; path traversal blocked; size/nesting limits enforced | Unit: symlink, traversal, oversize, 1000 files |
| 2.2 | SHA-256 calculator | File path | 64-char hex string | 2.1 | Agent 2 | `src/secret_wards/intake/hashing.py` | Streaming hash (low memory); matches `sha256sum` | Unit: known files, empty, 100MB |
| 2.3 | Format classifier | `InputFile` | `FormatType` enum | 2.1 | Agent 2 | `src/secret_wards/intake/classifier.py` | Extension + content sniffing; UNKNOWN for unsupported | Unit: CSV/TSV/JSON/text/FHIR/binary/PDF |
| 2.4 | Encoding detector | `InputFile` | Encoding name (UTF-8, UTF-16, CP1252) | 2.1 | Agent 2 | `src/secret_wards/intake/encoding.py` | `charset-normalizer` primary; no Latin-1 fallback | Unit: UTF-8/BOM, UTF-16LE, CP1252, binary |
| 2.5 | CSV/TSV parser | `InputFile`, encoding | `ParsedDocument` with URM records | 2.3, 2.4 | Agent 2 | `src/secret_wards/parsers/csv_parser.py` | Auto-delimiter; header inference; quote handling; shifted columns tolerant | Unit: comma, tab, semicolon; no header; quoted commas; 10k rows |
| 2.6 | JSON parser | `InputFile`, encoding | `ParsedDocument` with URM records | 2.3, 2.4 | Agent 2 | `src/secret_wards/parsers/json_parser.py` | Streaming for large files; nested walk; JSON pointer paths | Unit: nested obj, arrays, 50MB stream, malformed |
| 2.7 | Plain text parser | `InputFile`, encoding | `ParsedDocument` (single record, `loc="doc"`) | 2.3, 2.4 | Agent 2 | `src/secret_wards/parsers/text_parser.py` | Line/paragraph segmentation; offset maps | Unit: multiline, empty, Unicode |
| 2.8 | FHIR R4 parser | `InputFile`, encoding | `ParsedDocument` with URM records | 2.3, 2.4 | Agent 2 | `src/secret_wards/parsers/fhir_parser.py` | `fhir.resources` validation; references, extensions, contained, attachments | Unit: Bundle, Patient, Observation; invalid resource → quarantine |
| 2.9 | Quarantine classifier | Parse errors, unsupported formats | `QuarantineResult` | 2.5-2.8 | Agent 2 | `src/secret_wards/intake/quarantine.py` | Reason codes from `context.md` §17.1; original copied to `quarantined/` | Unit: each reason code |
| 2.10 | Intake pipeline integration | All above | `List[ParsedDocument]` + `List[QuarantineResult]` | 2.1-2.9 | Agent 2 | `src/secret_wards/intake/pipeline.py` | Processes all files; continues on quarantine; metrics per file | Integration: mixed format dir, 100 files |

**Phase 2 Deliverables:** Complete intake package; all parsers output valid URM  
**Phase 2 Acceptance:** Mixed-format directory (CSV, JSON, text, FHIR, PDF) → parsed URM + quarantined PDF; no crashes; metrics recorded.

---

### Phase 3 — Basic Sanitization Pipeline (P0)

**Objective:** End-to-end CSV/JSON/text sanitization with placeholder detection (regex-only) to validate serialization and output contract.

| Task | Objective | Inputs | Expected Outputs | Dependencies | Owner | Files Affected | Acceptance Criteria | Tests Required |
|------|-----------|--------|------------------|--------------|-------|----------------|---------------------|----------------|
| 3.1 | Placeholder PII detector (regex) | `UnifiedRecord` | `List[PIISpan]` | Phase 1, 2 | Agent 3 | `src/secret_wards/detection/placeholder.py` | Detects: email, phone (simple), PAN, 12-digit numbers, dates | Unit: each pattern; precision/recall on fixtures |
| 3.2 | Placeholder medical veto | `UnifiedRecord` | `List[MedicalSpan]` | Phase 1 | Agent 5 (Clinical) | `src/secret_wards/clinical/placeholder.py` | Detects: `\d+\s*mg`, `OD|BD|TDS`, `Parkinson's` | Unit: clinical patterns preserved |
| 3.3 | Span merger + veto | PIISpans + MedicalSpans | Filtered `List[PIISpan]` | 3.1, 3.2 | Agent 3 | `src/secret_wards/detection/merger.py` | Medical spans veto overlapping PII spans | Unit: overlap, adjacency, containment |
| 3.4 | Text replacer (offset-map aware) | `UnifiedRecord`, filtered spans | `SanitizedRecord` | Phase 1 | Agent 3 | `src/secret_wards/transform/replacer.py` | Uses offset maps; replaces in original text; preserves structure | Unit: replacement at boundaries, multi-byte chars |
| 3.5 | Structured field sanitizer | `ParsedDocument`, spans | `ParsedDocument` with sanitized fields | 3.3 | Agent 3 | `src/secret_wards/transform/structured.py` | CSV/JSON fields replaced; FHIR elements replaced | Unit: CSV cell, JSON leaf, FHIR Patient.name |
| 3.6 | Serializer (CSV/JSON/text) | `ParsedDocument` + `SanitizedRecord`s | Output files in `sanitized/` | Phase 1 | Agent 6 (Output) | `src/secret_wards/output/serializer.py` | Preserves format, dialect, encoding (UTF-8); pseudonym placeholder `PSN-TEMP` | Unit: round-trip parse → sanitize → parse |
| 3.7 | Filename sanitizer | Original path, `InputFile` | Safe output path | Phase 1 | Agent 6 | `src/secret_wards/output/namer.py` | SHA-256 prefix + original ext; no PII in path | Unit: PII in filename, Unicode, long names |
| 3.8 | Atomic writer | Output path, content | File on disk | Phase 1 | Agent 6 | `src/secret_wards/output/writer.py` | Temp file → `os.rename`; cleanup on error | Unit: power-cut simulation (kill -9) |
| 3.9 | Basic pipeline integration | All above | `sanitized/`, partial `report.json`, `records.jsonl` | 2.10, 3.1-3.8 | Agent 0 | `src/secret_wards/pipeline/basic.py` | Runs end-to-end; produces valid output structure | Integration: 10-file mixed dir → `CONTRACT OK` (structural) |

**Phase 3 Deliverables:** Working basic pipeline; `validate_output.py` passes structural checks (if available)  
**Phase 3 Acceptance:** CSV/JSON/text input → sanitized output with placeholder pseudonyms; no raw PII in output; `report.json` and `records.jsonl` structurally valid.

---

### Phase 4 — PII Detection Engine (P0)

**Objective:** Production-grade multilingual PII detection replacing placeholder.

| Task | Objective | Inputs | Expected Outputs | Dependencies | Owner | Files Affected | Acceptance Criteria | Tests Required |
|------|-----------|--------|------------------|--------------|-------|----------------|---------------------|----------------|
| 4.1 | Unicode normalization pipeline | `UnifiedRecord` | Normalized text + offset maps | Phase 1 | Agent 3 | `src/secret_wards/detection/normalize.py` | NFC, Devanagari digits, ZWJ/ZWNJ, bidi checks; offset map correctness | Unit: each normalization; offset map round-trip |
| 4.2 | Structured field scanner | `ParsedDocument` | `List[PIISpan]` (headers, keys, FHIR paths, filenames) | Phase 1, 2 | Agent 3 | `src/secret_wards/detection/structured.py` | Scans all structural locations; JSON pointers for nested | Unit: CSV header, JSON nested key, FHIR Patient.telecom, filename |
| 4.3 | Phone detector (India) | Normalized text | `List[PIISpan]` (type=PHONE) | 4.1 | Agent 3 | `src/secret_wards/detection/identifiers.py` | `phonenumbers` + regex; +91/0 prefix; 10 digits 6-9; Devanagari digits | Unit: all Indian formats; false positive on non-phones |
| 4.4 | Aadhaar detector | Normalized text | `List[PIISpan]` (type=AADHAAR) | 4.1 | Agent 3 | `src/secret_wards/detection/identifiers.py` | 12 digits + Verhoeff checksum | Unit: valid/invalid checksum; embedded in text |
| 4.5 | ABHA detector | Normalized text | `List[PIISpan]` (type=ABHA) | 4.1 | Agent 3 | `src/secret_wards/detection/identifiers.py` | 14 digits; format validation | Unit: valid format; similar non-ABHA numbers |
| 4.6 | PAN detector | Normalized text | `List[PIISpan]` (type=PAN) | 4.1 | Agent 3 | `src/secret_wards/detection/identifiers.py` | Regex `^[A-Z]{5}[0-9]{4}[A-Z]$` | Unit: valid/invalid; case insensitivity |
| 4.7 | UHID/MRN detector | Normalized text + context | `List[PIISpan]` (type=UHID) | 4.1, 4.2 | Agent 3 | `src/secret_wards/detection/identifiers.py` | Patterns from practice data; context keywords ("UHID:", "MRN:") | Unit: hospital-specific formats; context required |
| 4.8 | Email/URL detector | Normalized text | `List[PIISpan]` (type=EMAIL/URL) | 4.1 | Agent 3 | `src/secret_wards/detection/identifiers.py` | RFC 5322 regex + `email-validator`; URL regex | Unit: valid emails/URLs; adjacent punctuation |
| 4.9 | PIN/Address detector | Normalized text | `List[PIISpan]` (type=ADDRESS/PIN) | 4.1 | Agent 3 | `src/secret_wards/detection/identifiers.py` | 6-digit PIN; address keywords (village, district, taluk) | Unit: PIN in text; address phrases |
| 4.10 | Date detector | Normalized text | `List[PIISpan]` (type=DATE) | 4.1 | Agent 3 | `src/secret_wards/detection/identifiers.py` | `dateparser` + contextual classification (health-related vs admin) | Unit: multiple formats; lab value numbers not detected |
| 4.11 | Honorific/Relationship trigger detector | Normalized text | `List[PIISpan]` (type=NAME/RELATIVE) | 4.1 | Agent 3 | `src/secret_wards/detection/names.py` | Patterns: `S/o`, `D/o`, `W/o`, `C/O`, `Mr.`, `Mrs.`, `Dr.`, `श्री`, `पुत्र`, `देखभाल` | Unit: each trigger; `C/O fever` vs `C/O Rahul` |
| 4.12 | Gazetteer loader | Bundled data files | `FrozenSet[str]` for names/surnames | Phase 1 | Agent 3 | `src/secret_wards/detection/gazetteer.py` | Loads at startup; Latin + Devanagari; transliteration variants | Unit: load time <1s; coverage spot-check |
| 4.13 | Transliteration + Double Metaphone | Devanagari text | Latin + phonetic codes | 4.1 | Agent 3 | `src/secret_wards/detection/transliterate.py` | `indic-transliteration` → IAST → Latin → Double Metaphone | Unit: मोहम्मद → mohammad → MMT; round-trip consistency |
| 4.14 | Name detector (rule-based) | Normalized text, gazetteer, triggers | `List[PIISpan]` (type=NAME/RELATIVE/DOCTOR) | 4.1, 4.11, 4.12, 4.13 | Agent 3 | `src/secret_wards/detection/names.py` | Gazetteer match + trigger proximity + script consistency; role classification | Unit: English/Hindi/Hinglish names; doctor vs patient vs relative |
| 4.15 | CRF name tagger (conditional) | Labeled practice data | Trained model (if justified) | 4.14 | Agent 3 | `src/secret_wards/detection/crf_tagger.py` | **Only if** >5% F1 gain over rule baseline; model <50M params | Unit: model loads; inference <10ms/record; comparison test |
| 4.16 | Second-pass residual scanner | Sanitized text | `List[PIISpan]` (stragglers) | 4.1-4.15 | Agent 3 | `src/secret_wards/detection/residual.py` | Re-scans output; searches for patient's known identifiers | Unit: planted stragglers detected |
| 4.17 | Detection engine integration | All detectors | `List[PIISpan]` per record | 4.1-4.16 | Agent 3 | `src/secret_wards/detection/engine.py` | Runs all detectors; merges spans; confidence scoring; outputs per §21.5 | Integration: full detection on 100-record fixture; P/R/F1 measured |

**Phase 4 Deliverables:** Complete detection engine; all identifier types covered; multilingual name detection  
**Phase 4 Acceptance:** On labeled synthetic fixture: PII detection recall ≥95%, precision ≥90%; medical veto precision ≥98%; no crashes.

---

### Phase 5 — Clinical Preservation (P0)

**Objective:** Contextual medical span detection and veto integration.

| Task | Objective | Inputs | Expected Outputs | Dependencies | Owner | Files Affected | Acceptance Criteria | Tests Required |
|------|-----------|--------|------------------|--------------|-------|----------------|---------------------|----------------|
| 5.1 | Drug/strength/dosage detector | Normalized text | `List[MedicalSpan]` (DRUG, DOSAGE, FREQUENCY, DURATION) | Phase 1, 4.1 | Agent 5 (Clinical) | `src/secret_wards/clinical/drugs.py` | Gazetteer (INN + India brands) + regex for strengths/frequencies | Unit: `Dolo 650 BD`, `5 mg`, `TDS`, `10 days` |
| 5.2 | Lab/vital/unit detector | Normalized text | `List[MedicalSpan]` (LAB, VITAL, UNIT) | 5.1 | Agent 5 | `src/secret_wards/clinical/labs.py` | LOINC-derived lab names; vital patterns (`BP 120/80`); unit gazetteer | Unit: `HbA1c 7.2%`, `BP 130/85`, `mg/dL` |
| 5.3 | Diagnosis/procedure detector | Normalized text | `List[MedicalSpan]` (DIAGNOSIS, PROCEDURE) | 5.1 | Agent 5 | `src/secret_wards/clinical/diagnoses.py` | ICD-10 derived list + eponyms (Parkinson's, Alzheimer's, Crohn's) | Unit: `Diabetes`, `Parkinson's disease`, `Appendectomy` |
| 5.4 | Doctor context detector | Normalized text | `List[MedicalSpan]` (DOCTOR) | 5.1 | Agent 5 | `src/secret_wards/clinical/doctors.py` | `Dr.`/`Doctor` + name in clinical context (prescription, referral) | Unit: `Dr. Rahul prescribed` vs `Rahul is patient` |
| 5.5 | Medical veto integration | PIISpans + MedicalSpans | Filtered PIISpans | 4.3, 5.1-5.4 | Agent 5 | `src/secret_wards/clinical/veto.py` | Span-level: medical vetoes overlapping PII; adjacency re-check | Unit: `Rahul 5 mg` → Rahul redacted, `5 mg` kept; `Parkinson's` kept |
| 5.6 | Clinical preservation tests | Synthetic fixtures | Test report | 5.5 | Agent 5 | `tests/test_clinical_preservation.py` | >99% clinical values preserved; <1% false medical veto on real PII | Adversarial: `Patient Parkinson admitted` → Parkinson kept, Patient redacted |

**Phase 5 Deliverables:** Complete clinical preservation layer integrated with detection  
**Phase 5 Acceptance:** On clinical fixture: 0 clinical values corrupted; doctor names preserved in context; relative names redacted.

---

### Phase 6 — Output Security Gate & Reporting (P0)

**Objective:** Independent validation of sanitized output; contract-compliant `report.json` and `records.jsonl`.

| Task | Objective | Inputs | Expected Outputs | Dependencies | Owner | Files Affected | Acceptance Criteria | Tests Required |
|------|-----------|--------|------------------|--------------|-------|----------------|---------------------|----------------|
| 6.1 | Residual PII scanner | Sanitized files | `List[PIISpan]` (should be empty) | Phase 3, 4 | Agent 6 (Output) | `src/secret_wards/output/security_gate.py` | Runs same detectors as Phase 4 on OUTPUT; any high-confidence hit → fail | Unit: planted PII in sanitized → detected |
| 6.2 | Canary checker | Sanitized files, logs, temp | Boolean (clean) | Phase 3 | Agent 6 | `src/secret_wards/output/canary.py` | Scans for `LOCKMATE_CANARY_*` strings; any hit → fail | Unit: injected canary → detected |
| 6.3 | Clinical integrity verifier | Original + sanitized URM | Boolean (intact) | Phase 3, 5 | Agent 6 | `src/secret_wards/output/clinical_check.py` | Compares medical spans pre/post; any corruption → fail | Unit: corrupted clinical value → detected |
| 6.4 | Schema validator | Sanitized files | Boolean (valid) | Phase 3 | Agent 6 | `src/secret_wards/output/schema_check.py` | CSV/TSV parseable; JSON valid; FHIR R4 valid (`fhir.resources`) | Unit: invalid FHIR → detected |
| 6.5 | Filename/metadata scanner | Sanitized paths, output JSON | Boolean (safe) | Phase 3 | Agent 6 | `src/secret_wards/output/meta_check.py` | No PII in output paths; no PII in JSON keys of sanitized output | Unit: PII in sanitized filename → detected |
| 6.6 | Pseudonym consistency checker | `records.jsonl`, sanitized records | Boolean (consistent) | Phase 3, 8 | Agent 6 | `src/secret_wards/output/pseudonym_check.py` | Same patient → same pseudonym in records.jsonl AND in sanitized record | Unit: mismatch → detected |
| 6.7 | Security gate orchestrator | All checks | `GateResult` (PASS/QUARANTINE) | 6.1-6.6 | Agent 6 | `src/secret_wards/output/security_gate.py` | All checks must PASS; any FAIL → quarantine entire file | Integration: gate passes clean file; fails each check type |
| 6.8 | report.json generator | All `ProcessingMetrics`, `QuarantineResult`s | `report.json` (exact schema) | Phase 2, 3 | Agent 6 | `src/secret_wards/output/report.py` | Matches `context.md` §16.2 exactly; hash keys; accurate totals | Unit: schema validation; totals match actual counts |
| 6.9 | records.jsonl generator | `PatientCluster`s, sanitized records | `records.jsonl` (exact schema) | Phase 3, 7, 8 | Agent 6 | `src/secret_wards/output/records.py` | Matches `context.md` §16.3; location conventions; null for uncertain | Unit: location formats; pseudonym consistency |
| 6.10 | Reporting integration | All above | Complete `output/` directory | 6.7-6.9 | Agent 6 | `src/secret_wards/output/pipeline.py` | Atomic write of all three outputs; cleanup on failure | Integration: full run → `validate_output.py` → `CONTRACT OK` |

**Phase 6 Deliverables:** Complete output pipeline with independent security gate; contract-compliant reports  
**Phase 6 Acceptance:** `validate_output.py` passes on practice input (or synthetic equivalent); all security gate checks pass on clean output; fail correctly on injected violations.

---

### Phase 7 — Identity Resolution & Linkage (P1)

**Objective:** Conservative cross-record patient linkage with stable clusters.

| Task | Objective | Inputs | Expected Outputs | Dependencies | Owner | Files Affected | Acceptance Criteria | Tests Required |
|------|-----------|--------|------------------|--------------|-------|----------------|---------------------|----------------|
| 7.1 | Blocking key generator | `UnifiedRecord` (with detected PII) | `List[str]` blocking keys | Phase 4 | Agent 4 (Linkage) | `src/secret_wards/linkage/blocking.py` | Keys: normalized name, transliterated name, Double Metaphone, phone, Aadhaar, ABHA, PAN, DOB year, district | Unit: each key type; collision rate on synthetic data |
| 7.2 | Candidate pair generator | Blocking keys per record | `List[IdentityCandidate]` | 7.1 | Agent 4 | `src/secret_wards/linkage/candidates.py` | Records sharing ≥1 key → candidate; deduplicated; max pairs controlled | Unit: 1000 records → <50k pairs (blocking effective) |
| 7.3 | Pairwise scorer | `IdentityCandidate` | Scored `IdentityCandidate` | 7.2, 4 | Agent 4 | `src/secret_wards/linkage/scoring.py` | Features from `context.md` §11.3; weights configurable; cannot-link detection | Unit: each feature; known match/non-match pairs |
| 7.4 | Cannot-link constraints | `IdentityCandidate` | `cannot_link: bool` | 7.3 | Agent 4 | `src/secret_wards/linkage/constraints.py` | Conflicting Aadhaar/ABHA/PAN/DOB/gender → cannot_link=True | Unit: conflicting IDs → cannot_link |
| 7.5 | Conservative clusterer | Scored candidates | `List[PatientCluster]` | 7.3, 7.4 | Agent 4 | `src/secret_wards/linkage/clustering.py` | Greedy by score; cluster consistency check; no transitive closure; null for uncertain | Unit: chain A-B, B-C, A-C low → no merge; singleton → null |
| 7.6 | Canonical identity builder | `PatientCluster` | `canonical_identity` string | 7.5 | Agent 4 | `src/secret_wards/linkage/canonical.py` | Sorted reliable identifiers (Aadhaar, phone, DOB, normalized name) | Unit: deterministic sort; weak cluster → random UUID + HMAC |
| 7.7 | Linkage integration | All above | `List[PatientCluster]` per run | 7.1-7.6 | Agent 4 | `src/secret_wards/linkage/pipeline.py` | Processes all records; outputs clusters with pseudonyms (Phase 8) | Integration: 500-record multi-hospital fixture; P/R/F1 measured |

**Phase 7 Deliverables:** Complete linkage pipeline; conservative clustering  
**Phase 7 Acceptance:** On labeled fixture: linkage precision ≥98%, recall ≥85%, false-merge rate <1%; null assignment for uncertain.

---

### Phase 8 — Pseudonymization (P1)

**Objective:** HMAC-SHA256 stable pseudonyms with secret-dependent determinism.

| Task | Objective | Inputs | Expected Outputs | Dependencies | Owner | Files Affected | Acceptance Criteria | Tests Required |
|------|-----------|--------|------------------|--------------|-------|----------------|---------------------|----------------|
| 8.1 | Secret loader | `RAKSHA_SECRET` env | `bytes` (32+ bytes) | Phase 0 | Agent 4 | `src/secret_wards/crypto/secret.py` | Reads from `os.environ`; validates length; never logs; error if missing | Unit: missing env → clear error; set env → loads |
| 8.2 | HMAC pseudonym service | `canonical_identity`, secret | `PSN-XXXX` string | 8.1, 7.6 | Agent 4 | `src/secret_wards/crypto/pseudonym.py` | `context.md` §12.2 algorithm; domain separation; truncation to 8 chars base32 | Unit: determinism; secret rotation → different; collision test (1M) |
| 8.3 | Date-shift derivation | `patient_pseudonym`, secret | `int` offset days [-365,365] | 8.1 | Agent 4 | `src/secret_wards/crypto/date_shift.py` | `context.md` §13.1 algorithm; domain `"date_shift"` | Unit: same patient+secret → same offset; different secret → different |
| 8.4 | Pseudonym injection | `PatientCluster`, `SanitizedRecord` | Records with pseudonym in structured field | 8.2, 3.6 | Agent 4 | `src/secret_wards/crypto/injector.py` | Adds/replaces patient identifier field; `null` cluster → no pseudonym | Unit: FHIR Patient.identifier, CSV patient_id, JSON patient.pseudonym |
| 8.5 | Pseudonym integration | All above | `PatientCluster.pseudonym` populated | 8.2-8.4 | Agent 4 | `src/secret_wards/linkage/pipeline.py` | Links Phase 7 clusters to pseudonyms; updates sanitized records | Integration: full pipeline → pseudonyms in output + records.jsonl match |

**Phase 8 Deliverables:** Complete pseudonym service; secret rotation verified  
**Phase 8 Acceptance:** 3 runs same secret → identical pseudonyms; 2 runs different secrets → different pseudonyms; clinical content unchanged.

---

### Phase 9 — Date & Age Transformations (P1)

**Objective:** Patient-consistent date shifting and age generalization.

| Task | Objective | Inputs | Expected Outputs | Dependencies | Owner | Files Affected | Acceptance Criteria | Tests Required |
|------|-----------|--------|------------------|--------------|-------|----------------|---------------------|----------------|
| 9.1 | Date field identifier | `UnifiedRecord` + PIISpans | `List[FieldPath]` (date fields) | Phase 4 | Agent 5 (Privacy) | `src/secret_wards/privacy/date_fields.py` | Finds all DATE-type PII spans + structured date fields (DOB, admission, etc.) | Unit: FHIR date elements, CSV date columns, JSON date strings |
| 9.2 | Date shifter | Date fields + patient pseudonym + secret | Shifted dates (preserving intervals) | 8.3, 9.1 | Agent 5 | `src/secret_wards/privacy/date_shift.py` | Applies per-patient offset; handles date-only, datetime, timezone; preserves order | Unit: interval preservation; chronological order; timezone; leap years |
| 9.3 | Age generalizer | Age/DOB fields + patient pseudonym | Age band strings | Phase 4 | Agent 5 | `src/secret_wards/privacy/age_bands.py` | Bands from `context.md` §13.2; round down; 90+ ceiling; unknown → null | Unit: boundary values (4,5,9,10...89,90); unknown; invalid |
| 9.4 | Date/age integration | All above | `PrivacyTransformation` per record | 9.2, 9.3 | Agent 5 | `src/secret_wards/privacy/pipeline.py` | Applies to URM before serialization; updates structured + text | Integration: patient with 10 dates → all shifted consistently; intervals exact |

**Phase 9 Deliverables:** Date shifting and age bands applied  
**Phase 9 Acceptance:** Intervals preserved exactly; age bands correct; different secrets → different shifts; chronological order maintained.

---

### Phase 10 — Location & Rare-Value Protection (P1)

**Objective:** Location generalization hierarchy and k-anonymity-based rare suppression.

| Task | Objective | Inputs | Expected Outputs | Dependencies | Owner | Files Affected | Acceptance Criteria | Tests Required |
|------|-----------|--------|------------------|--------------|-------|----------------|---------------------|----------------|
| 10.1 | Location gazetteer loader | Bundled Census 2011 CSV | `Dict[village→district, district→state, PIN→district]` | Phase 1 | Agent 5 | `src/secret_wards/privacy/gazetteer.py` | Loads at startup; memory <100MB; covers target states | Unit: lookup accuracy; missing → next level |
| 10.2 | Location generalizer | Location fields (village, city, PIN, district) | Generalized values | 10.1 | Agent 5 | `src/secret_wards/privacy/location.py` | Village→district; city→district; PIN→3-digit; rare district→state | Unit: each level; rare threshold; missing data |
| 10.3 | Quasi-identifier equivalence class builder | Age band, district, gender, diagnosis category, LOS band | Equivalence class sizes | Phase 9, 10.2 | Agent 5 | `src/secret_wards/privacy/equivalence.py` | Groups records by QI tuple; counts per class | Unit: class sizes match manual calculation |
| 10.4 | Rare suppressor | Equivalence classes < k_min | Suppression/generalization actions | 10.3 | Agent 5 | `src/secret_wards/privacy/suppression.py` | Iterative: suppress rarest attribute → generalize age → generalize location | Unit: k=5; convergence; max suppression |
| 10.5 | Attacker simulation | Sanitized output + synthetic voter roll | Re-identification rate | 10.2, 10.4 | Agent 7 (Red-Team) | `src/secret_wards/redteam/attacker_sim.py` | Links sanitized QIs to voter roll; measures unique matches | Integration: target <5% unique re-ID |
| 10.6 | Privacy integration | All above | `PrivacyTransformation` per record | 9.4, 10.2, 10.4 | Agent 5 | `src/secret_wards/privacy/pipeline.py` | Applies location + rare suppression; updates URM | Integration: full pipeline → k-anonymity report; attacker sim results |

**Phase 10 Deliverables:** Location generalization, rare suppression, attacker simulation metrics  
**Phase 10 Acceptance:** k-anonymity ≥5 for >95% records; attacker simulation unique re-ID <5%; clinical utility >95%.

---

### Phase 11 — FHIR & Extended Format Hardening (P1)

**Objective:** Production-ready FHIR R4 handling; attachments; nested structures.

| Task | Objective | Inputs | Expected Outputs | Dependencies | Owner | Files Affected | Acceptance Criteria | Tests Required |
|------|-----------|--------|------------------|--------------|-------|----------------|---------------------|----------------|
| 11.1 | FHIR reference scanner | `ParsedDocument` (FHIR) | `List[PIISpan]` in references | Phase 2.8, 4 | Agent 2/3 | `src/secret_wards/parsers/fhir_references.py` | Traverses `reference` fields; `contained` resources; `extension` URLs/values | Unit: Patient.reference, Practitioner.reference, contained Observation |
| 11.2 | FHIR attachment handler | `Binary` resources, base64 data | Quarantine or text extraction | Phase 2.8 | Agent 2 | `src/secret_wards/parsers/fhir_attachments.py` | Base64 PDF/image → quarantine; text/plain → extract + scan | Unit: PDF → quarantine; text → sanitized |
| 11.3 | FHIR metadata scanner | `Resource.meta`, `Bundle.metadata` | `List[PIISpan]` | Phase 2.8, 4 | Agent 3 | `src/secret_wards/detection/fhir_meta.py` | Scans `meta.tag`, `meta.profile`, `meta.security` for PII | Unit: PII in meta.tag.code |
| 11.4 | FHIR serializer validator | Sanitized FHIR | Boolean (valid R4) | Phase 3.6, 6.4 | Agent 6 | `src/secret_wards/output/fhir_validator.py` | `fhir.resources` round-trip validation; all required elements present | Unit: sanitized Patient → valid; missing required → fail |
| 11.5 | FHIR integration test | Multi-resource Bundle | Sanitized Bundle | 11.1-11.4 | Agent 2 | `tests/test_fhir_integration.py` | Patient + Observation + MedicationRequest → all sanitized, valid R4 | Integration: complex Bundle; references preserved |

**Phase 11 Deliverables:** FHIR R4 fully supported; attachments safe; metadata clean  
**Phase 11 Acceptance:** Complex FHIR Bundle → valid sanitized R4 output; no PII in references/extensions/attachments/meta.

---

### Phase 12 — Red-Team Evaluation & Hardening (P1)

**Objective:** Adversarial testing, canary verification, performance profiling, security hardening.

| Task | Objective | Inputs | Expected Outputs | Dependencies | Owner | Files Affected | Acceptance Criteria | Tests Required |
|------|-----------|--------|------------------|--------------|-------|----------------|---------------------|----------------|
| 12.1 | Synthetic adversarial fixture generator | Schema specs | `test_fixtures/adversarial/` | Phase 0 | Agent 7 (Red-Team) | `tests/fixtures/generator.py` | Generates: Hinglish names, transliterated variants, false merges, medical-adjacent PII, shifted columns, nested JSON, FHIR extensions, filename PII, metadata PII, path traversal, symlinks, oversized, decompression bombs | Unit: each fixture type validates |
| 12.2 | Canary injection & verification | Pipeline | Zero canary leakage | Phase 6.2 | Agent 7 | `tests/redteam/canary_test.py` | Injects `LOCKMATE_CANARY_<UUID>` in input; scans output, logs, temp; asserts zero | Integration: full pipeline run with canaries |
| 12.3 | False-merge test suite | Labeled patient pairs | False-merge rate | Phase 7 | Agent 7 | `tests/redteam/false_merge.py` | Pairs: same name diff DOB, same name diff gender, same name diff Aadhaar → separate pseudonyms | Unit: each pair type; target <1% false merge |
| 12.4 | Medical corruption test | Clinical fixtures | Corruption rate | Phase 5 | Agent 7 | `tests/redteam/medical_corruption.py` | Verifies no drug/dosage/diagnosis/lab/vital corrupted | Unit: each clinical type; target 0% corruption |
| 12.5 | Privacy attack evaluation | Sanitized output + voter roll | Re-ID metrics | Phase 10.5 | Agent 7 | `tests/redteam/privacy_attack.py` | Measures: direct ID leakage, quasi-ID uniqueness, linkage attack success | Integration: target <5% unique re-ID |
| 12.6 | Performance profiling | Max-scale input | Time/memory profile | Phase 2-11 | Agent 7 | `tests/redteam/performance.py` | Runs 2GB input; measures per-stage time, peak RSS, CPU utilization | Benchmark: <900s, <4GB RSS, 2 CPUs |
| 12.7 | Determinism verification | 3 runs same secret | Byte-identical sanitized/ | Phase 8 | Agent 7 | `tests/redteam/determinism.py` | Compares sanitized/ byte-for-byte; records.jsonl identical; report totals identical | Integration: 3 runs → all identical |
| 12.8 | Secret rotation verification | 2 runs different secrets | Different pseudonyms/shifts | Phase 8 | Agent 7 | `tests/redteam/secret_rotation.py` | Verifies pseudonyms differ, date shifts differ, clinical content identical | Integration: 2 runs → clinical same, privacy different |
| 12.9 | Resource limit enforcement | Oversized input | Graceful quarantine | Phase 2 | Agent 7 | `tests/redteam/resource_limits.py` | 101MB file → quarantine; 51 nesting → quarantine; 101:1 zip → quarantine | Unit: each limit |
| 12.10 | Security hardening review | Codebase | `SECURITY_REVIEW.md` | All phases | Agent 7 | — | Checks: no raw PII in logs, no secret in memory dumps, temp files encrypted, no eval/exec, no shell injection | Manual + automated (bandit, semgrep) |

**Phase 12 Deliverables:** Test evidence for all adversarial scenarios; performance benchmarks; security review  
**Phase 12 Acceptance:** All red-team tests pass; performance within limits; determinism verified; secret rotation verified; security review clean.

---

### Phase 13 — Performance Optimization (P1)

**Objective:** Meet 15min/4GB/2CPU constraints with margin.

| Task | Objective | Inputs | Expected Outputs | Dependencies | Owner | Files Affected | Acceptance Criteria | Tests Required |
|------|-----------|--------|------------------|--------------|-------|----------------|---------------------|----------------|
| 13.1 | Profile hot paths | Phase 12.6 results | Bottleneck report | Phase 12 | Agent 0/All | — | Identifies top 5 time/memory consumers | `cProfile`, `memory_profiler` |
| 13.2 | Optimize blocking | Phase 7.1 | Reduced candidate pairs | 13.1 | Agent 4 | `linkage/blocking.py` | Additional blocking keys; early filtering | Benchmark: pairs reduced 50%+ |
| 13.3 | Vectorize detection | Phase 4 | Faster PII scanning | 13.1 | Agent 3 | `detection/engine.py` | Compiled regexes; pandas vectorized where applicable | Benchmark: detection time -30% |
| 13.4 | Streaming serialization | Phase 3.6, 11.4 | Lower peak memory | 13.1 | Agent 6 | `output/serializer.py` | Chunked CSV/JSON write; FHIR stream | Benchmark: peak RSS -25% |
| 13.5 | Parallel file processing | Phase 2.10 | 2x throughput | 13.1 | Agent 2 | `intake/pipeline.py` | `ProcessPoolExecutor(max_workers=2)` for parsing | Benchmark: intake time -40% |
| 13.6 | Memory cleanup | All phases | Explicit `del` + `gc.collect()` | 13.1 | All | Per-module | Large intermediates released at stage boundaries | Benchmark: no memory growth across files |

**Phase 13 Deliverables:** Optimized pipeline meeting constraints with 20% margin  
**Phase 13 Acceptance:** Full 2GB input → <720s (12 min), <3.2 GB RSS.

---

### Phase 14 — Frontend & Demonstration (P2, Optional)

**Objective:** Visual demonstration for judging; not required for CLI evaluation.

| Task | Objective | Inputs | Expected Outputs | Dependencies | Owner | Files Affected | Acceptance Criteria | Tests Required |
|------|-----------|--------|------------------|--------------|-------|----------------|---------------------|----------------|
| 14.1 | Demo data curation | Synthetic fixtures | `demo/data/` | Phase 12.1 | Frontend Eng | `demo/data/` | 3 hospitals, 1 patient across scripts, clear PII + clinical | Manual review |
| 14.2 | Pipeline visualization | Stage logs | Web UI (Streamlit) | Phase 0-13 | Frontend Eng | `demo/app.py` | Shows stage progression, timings, detection highlights | Manual demo |
| 14.3 | Before/After viewer | Original + sanitized URM | Side-by-side diff | Phase 14.2 | Frontend Eng | `demo/components/diff.py` | Highlights: removed (red), preserved (green), shifted (blue) | Manual demo |
| 14.4 | Linkage explorer | `PatientCluster`s | Graph view | Phase 14.2 | Frontend Eng | `demo/components/linkage.py` | Nodes=records, edges=link evidence, clusters colored | Manual demo |
| 14.5 | Privacy dashboard | Attacker sim results | Metrics panel | Phase 14.2 | Frontend Eng | `demo/components/privacy.py` | k-anonymity dist, re-ID rate, clinical utility | Manual demo |
| 14.6 | Verifier panel | `validate_output.py` | Live validation | Phase 14.2 | Frontend Eng | `demo/components/verifier.py` | Runs validator, shows `CONTRACT OK` | Manual demo |
| 14.7 | 5-min demo script | All above | `DEMO_SCRIPT.md` | Phase 14.1-14.6 | Agent 0 | `DEMO_SCRIPT.md` | Matches `context.md` §23.3 timing | Rehearsal |

**Phase 14 Deliverables:** Working demo app; rehearsed 5-minute script  
**Phase 14 Acceptance:** Demo runs smoothly; all 5 minutes covered; no CLI dependency.

---

## 5. Multi-Agent Role Allocation

| Agent | Role | Primary Ownership | Key Files/Modules |
|-------|------|-------------------|-------------------|
| **Agent 0** | Orchestrator / Architect | `contracts.py`, overall integration, phase gates, demo script | `src/secret_wards/contracts.py`, `BACKLOG.md`, `DEMO_SCRIPT.md` |
| **Agent 1** | Contract Auditor | Official contract mapping, validator inspection, repo audit | `CONTRACT_CHECKLIST.md`, `ASSET_REPORT.md`, `REPO_INVENTORY.md` |
| **Agent 2** | Ingestion Engineer | File discovery, parsing (CSV/TSV/JSON/text/FHIR), encoding, quarantine | `src/secret_wards/intake/`, `src/secret_wards/parsers/` |
| **Agent 3** | Detection Engineer | Unicode normalization, PII detection (identifiers, names), residual scan | `src/secret_wards/detection/` |
| **Agent 4** | Linkage Engineer | Blocking, pairwise scoring, constraints, clustering, pseudonyms, crypto | `src/secret_wards/linkage/`, `src/secret_wards/crypto/` |
| **Agent 5** | Clinical/Privacy Engineer | Medical preservation, date shifting, age bands, location generalization, rare suppression | `src/secret_wards/clinical/`, `src/secret_wards/privacy/` |
| **Agent 6** | Output Engineer | Serialization, security gate, report.json, records.jsonl, atomic writes | `src/secret_wards/output/` |
| **Agent 7** | Red-Team Engineer | Adversarial fixtures, canary tests, false-merge, privacy attack, performance, security | `tests/redteam/`, `tests/fixtures/`, `SECURITY_REVIEW.md` |
| **Frontend Eng** | Demo Engineer (Optional) | Visualization, before/after, linkage graph, privacy dashboard | `demo/` |

---

## 6. Ownership Boundaries & File Map

```
src/secret_wards/
├── contracts.py                    ← Agent 0 (all agents read)
├── __init__.py                     ← Agent 0
├── intake/                         ← Agent 2
│   ├── discovery.py
│   ├── hashing.py
│   ├── classifier.py
│   ├── encoding.py
│   ├── quarantine.py
│   └── pipeline.py
├── parsers/                        ← Agent 2
│   ├── csv_parser.py
│   ├── json_parser.py
│   ├── text_parser.py
│   ├── fhir_parser.py
│   ├── fhir_references.py
│   ├── fhir_attachments.py
│   └── fhir_meta.py
├── detection/                      ← Agent 3
│   ├── normalize.py
│   ├── structured.py
│   ├── identifiers.py
│   ├── names.py
│   ├── gazetteer.py
│   ├── transliterate.py
│   ├── crf_tagger.py        (conditional)
│   ├── residual.py
│   ├── merger.py
│   └── engine.py
├── clinical/                       ← Agent 5
│   ├── drugs.py
│   ├── labs.py
│   ├── diagnoses.py
│   ├── doctors.py
│   └── veto.py
├── linkage/                        ← Agent 4
│   ├── blocking.py
│   ├── candidates.py
│   ├── scoring.py
│   ├── constraints.py
│   ├── clustering.py
│   ├── canonical.py
│   └── pipeline.py
├── crypto/                         ← Agent 4
│   ├── secret.py
│   ├── pseudonym.py
│   ├── date_shift.py
│   └── injector.py
├── privacy/                        ← Agent 5
│   ├── gazetteer.py
│   ├── location.py
│   ├── equivalence.py
│   ├── suppression.py
│   ├── date_fields.py
│   ├── date_shift.py
│   ├── age_bands.py
│   └── pipeline.py
├── output/                         ← Agent 6
│   ├── serializer.py
│   ├── namer.py
│   ├── writer.py
│   ├── security_gate.py
│   ├── canary.py
│   ├── clinical_check.py
│   ├── schema_check.py
│   ├── meta_check.py
│   ├── pseudonym_check.py
│   ├── report.py
│   ├── records.py
│   └── pipeline.py
└── pipeline/                       ← Agent 0 (integration)
    ├── basic.py
    └── main.py
```

**Tests:**
```
tests/
├── test_contracts.py               ← Agent 0
├── test_intake/                    ← Agent 2
├── test_parsers/                   ← Agent 2
├── test_detection/                 ← Agent 3
├── test_clinical/                  ← Agent 5
├── test_linkage/                   ← Agent 4
├── test_crypto/                    ← Agent 4
├── test_privacy/                   ← Agent 5
├── test_output/                    ← Agent 6
├── test_fhir_integration.py        ← Agent 2
├── fixtures/
│   └── generator.py                ← Agent 7
└── redteam/
    ├── canary_test.py
    ├── false_merge.py
    ├── medical_corruption.py
    ├── privacy_attack.py
    ├── performance.py
    ├── determinism.py
    ├── secret_rotation.py
    ├── resource_limits.py
    └── adversarial/                ← Agent 7 (generated fixtures)
```

---

## 7. Shared Interfaces & Integration Contracts

**All agents MUST implement the exact interfaces in `src/secret_wards/contracts.py` (Phase 1).**

### Integration Protocol
1. **Agent 0 publishes `contracts.py`** (Phase 1 complete) → all agents pull
2. **Each agent develops against interfaces** — no direct imports of other agents' modules
3. **Integration checkpoints** (Agent 0 orchestrates):
   - **Checkpoint A (End Phase 3):** Basic pipeline runs → `sanitized/` + reports
   - **Checkpoint B (End Phase 6):** Security gate passes → `CONTRACT OK` on synthetic
   - **Checkpoint C (End Phase 8):** Linkage + pseudonyms integrated → records.jsonl consistent
   - **Checkpoint D (End Phase 11):** FHIR hardened → full format support
   - **Checkpoint E (End Phase 12):** Red-team passes → all adversarial tests green
4. **Agent 0 merges** via PR review; no direct pushes to `main` by implementation agents
5. **Shared test fixtures** in `tests/fixtures/` — Agent 7 generates; all agents consume

### Interface Stability Rules
- **No breaking changes to `contracts.py` after Phase 1** without Agent 0 approval
- **New optional fields** allowed with default values
- **Agent 0 mediates** any cross-agent interface disputes

---

## 8. Parallelizable vs Sequential Work

| Parallelizable (After Phase 1) | Sequential (Dependencies) |
|--------------------------------|---------------------------|
| Phase 2 (Intake) | Phase 3 needs Phase 2 |
| Phase 4 (Detection) | Phase 5 needs Phase 4 |
| Phase 5 (Clinical) | Phase 6 needs Phase 3, 4, 5 |
| Phase 7 (Linkage) | Phase 8 needs Phase 7 |
| Phase 9 (Date/Age) | Phase 10 needs Phase 9, 5 |
| Phase 11 (FHIR hardening) | Phase 12 needs all prior |
| Phase 13 (Optimization) | Phase 14 needs Phase 12 |

**Max Parallelism:** Agents 2, 3, 5 can work simultaneously after Phase 1. Agent 4 waits for Phase 4 output. Agent 6 waits for Phase 3. Agent 7 waits for Phase 3+4+5+7+9+10.

---

## 9. Integration Checkpoints (Detailed)

| Checkpoint | Trigger | Validation | Gatekeeper |
|------------|---------|------------|------------|
| **A: Basic Pipeline** | Phase 3 complete | `python main.py --input test_fixtures/basic --output test_out/` → produces `sanitized/`, `report.json`, `records.jsonl` with placeholder pseudonyms; no crashes | Agent 0 |
| **B: Security Gate** | Phase 6 complete | Run Checkpoint A + `validate_output.py` (or self-validator) → `CONTRACT OK`; security gate catches injected PII in sanitized output | Agent 0 + Agent 6 |
| **C: Linkage + Pseudonyms** | Phase 8 complete | Run on multi-hospital fixture → `records.jsonl` shows same pseudonym for linked records; pseudonyms in sanitized records match; secret rotation changes pseudonyms | Agent 0 + Agent 4 |
| **D: FHIR Hardened** | Phase 11 complete | Complex FHIR Bundle → valid sanitized R4; no PII in references/extensions/attachments; `validate_output.py` passes | Agent 0 + Agent 2 |
| **E: Red-Team Clear** | Phase 12 complete | All `tests/redteam/*.py` pass; performance <12min/3.2GB; determinism verified; secret rotation verified; security review clean | Agent 0 + Agent 7 |

**Each checkpoint requires:** Agent 0 sign-off + evidence (logs, test output, metrics) recorded in `INTEGRATION_LOG.md`.

---

## 10. Testing Strategy for Every Module

### 10.1 Unit Test Standards
- **Location:** `tests/` mirroring `src/`
- **Naming:** `test_<module>.py`
- **Coverage Target:** ≥90% on business logic; 100% on contract dataclasses
- **Fixtures:** Synthetic, labeled, in `tests/fixtures/`
- **Execution:** `pytest -xvs tests/` — must pass in <60s

### 10.2 Integration Test Standards
- **Location:** `tests/test_*_integration.py`
- **Scope:** Multi-module flows (intake→detection, detection→linkage, full pipeline)
- **Data:** Realistic synthetic datasets (100-1000 records)
- **Assertions:** Output structure, contract compliance, key metrics

### 10.3 Adversarial Test Standards (Agent 7)
- **Location:** `tests/redteam/`
- **Categories:** Canary, false-merge, medical corruption, privacy attack, performance, determinism, secret rotation, resource limits
- **Evidence:** JSON reports with metrics; committed to repo

### 10.4 Organizer Contract Validation
- **Frequency:** Every checkpoint + pre-submission
- **Command:** `python3 validate_output.py --input dev/input --output test_output/`
- **Success:** `CONTRACT OK` (stdout)
- **Failure:** Full debug output captured; blocking issue created

---

## 11. Adversarial and Hidden-Dataset Testing

### 11.1 Synthetic Adversarial Fixtures (Agent 7 Generates)
| Fixture | Description | Tests |
|---------|-------------|-------|
| `hinglish_names/` | Mixed script names (राहुल Sharma, Rahul शर्मा) | Detection recall |
| `transliterated_variants/` | Mohammad/Mohammed/Mohd./मोहम्मद/मुहम्मद | Linkage precision |
| `false_merge_pairs/` | Same name, different DOB/Aadhaar/gender | False-merge rate |
| `medical_adjacent/` | `Patient Rahul 5mg Dolo` vs `Rahul has fever` | Medical veto precision |
| `shifted_columns/` | CSV with misaligned headers | Structured detection |
| `nested_json/` | Deeply nested PII in JSON | Recursive scanning |
| `fhir_extensions/` | Custom extensions with PII | FHIR metadata scan |
| `filename_pii/` | `rahul_sharma_report.csv` | Filename sanitization |
| `metadata_pii/` | JSON keys with PII | Structured scanner |
| `path_traversal/` | `../../etc/passwd` symlinks | Intake safety |
| `decompression_bomb/` | 1KB zip → 1GB | Resource limits |

### 11.2 Hidden Dataset Simulation
- Agent 7 creates **undisclosed** test sets (not shared with other agents)
- Run at Checkpoint E (Phase 12)
- Measures: Detection P/R, linkage F1, clinical preservation, privacy attack
- **No overfitting:** Agents 2-6 cannot see hidden fixtures

---

## 12. Organizer Contract Validation

### 12.1 Self-Validator (Built by Agent 6)
Implements all `context.md` §3 checks:
- Output directory structure
- `report.json` schema + totals accuracy
- `records.jsonl` schema + pseudonym consistency
- Sanitized file format validity (CSV/JSON/FHIR)
- No PII in output (scan with detection engine)
- Filename/metadata safety
- Quarantine handling

### 12.2 Official Validator
- **Obtain early** (Phase 0.8)
- **Run at every checkpoint**
- **Pre-submission:** Full `dev/input/` → `CONTRACT OK` required

### 12.3 Validation Evidence
Record in `VALIDATION_LOG.md`:
```
Date | Validator Version | Input Dataset | Result | Notes
```

---

## 13. Performance Optimization

### 13.1 Targets (With 20% Margin)
| Metric | Organizer Limit | Internal Target |
|--------|-----------------|-----------------|
| Wall-clock time | 15 min (900s) | ≤ 720s (12 min) |
| Peak RSS | 4 GB | ≤ 3.2 GB |
| CPU utilization | 2 cores | ≤ 1.8 cores average |

### 13.2 Optimization Priorities (Phase 13)
1. **Linkage blocking** — reduce candidate pairs (biggest O(N²) risk)
2. **Detection regex compilation** — pre-compile, reuse
3. **Streaming serialization** — avoid full-document memory
4. **Parallel file intake** — 2 workers max
5. **Explicit memory release** — `del` + `gc.collect()` at stage boundaries

### 13.3 Profiling Infrastructure
- `cProfile` + `snakeviz` for CPU
- `memory_profiler` + `mprof` for RSS
- Per-stage timing in `ProcessingMetrics`

---

## 14. Security Hardening

### 14.1 Mandatory Controls
| Control | Implementation | Verification |
|---------|----------------|--------------|
| No `RAKSHA_SECRET` in logs/memory dumps | `secret.py` loads to bytes; `del` after use; no `__repr__` | `grep -r RAKSHA_SECRET` on code + memory dump test |
| No raw PII in temp files | Minimize temp; AES-GCM if needed; secure delete | Red-team scan of temp dir |
| No shell injection | No `subprocess` with shell=True; no `eval`/`exec` | Bandit scan |
| No path traversal | `Path.resolve()` + `is_relative_to(input_root)` | Red-team symlink test |
| No decompression bombs | `zipfile`/`tarfile` with size checks | Red-team bomb test |
| Dependencies pinned | `requirements.txt` with exact versions | `pip-audit` / `safety` |

### 14.2 Security Review (Phase 12.10)
- Automated: `bandit -r src/`, `semgrep --config=auto src/`
- Manual: `SECURITY_REVIEW.md` checklist
- **Sign-off:** Agent 7 + Agent 0

---

## 15. Final Submission Preparation

### 15.1 Required Deliverables Checklist
| Item | Status | Owner |
|------|--------|-------|
| Public GitHub repository | [ ] | Agent 0 |
| `README.md` (models declared, offline/CPU explained) | [ ] | Agent 0 |
| `raksha.toml` (exact spec) | [ ] | Agent 1 |
| `requirements.txt` (pinned) | [ ] | Agent 0 |
| Working `main.py` | [ ] | Agent 0 |
| Complete source code | [ ] | All |
| Unit + integration tests | [ ] | All |
| Architecture diagram | [ ] | Agent 0 |
| Threat model document | [ ] | Agent 0 + 7 |
| Two-page project brief PDF | [ ] | Agent 0 |
| Privacy-utility evaluation | [ ] | Agent 5 + 7 |
| Known limitations | [ ] | Agent 0 |
| Demonstration script | [ ] | Agent 0 |
| Official validator evidence | [ ] | Agent 1 |

### 15.2 README Requirements
- Project description
- **All models declared** (gazetteers, CRF if used, phonetic libs)
- Offline/CPU-only execution instructions
- `RAKSHA_SECRET` usage explanation
- How to run: `python main.py --input X --output Y`
- Resource requirements
- Known limitations (honest)

### 15.3 Two-Page Brief Content
1. **Problem & Threat Model** (1/3 page)
2. **Architecture Overview** (1/3 page)
3. **Privacy-Utility Results** (1/3 page) — Table: Before/After metrics
4. **Limitations & Residual Risk** (honest admission)

---

## 16. Demonstration and Judging Strategy

### 16.1 5-Minute Demo Script (From `context.md` §23.3)
| Minute | Content | Evidence Source |
|--------|---------|-----------------|
| 1 | Problem: Show synthetic multi-hospital records with PII | `demo/data/` |
| 2 | Identity Intelligence: One patient across scripts/formats → stable pseudonym | Linkage explorer |
| 3 | Clinical Integrity: Before/after — identity gone, medicine preserved | Diff viewer |
| 4 | Privacy Attack: Quasi-ID linkage attempt → measured failure | Privacy dashboard |
| 5 | Verification: Sanitized output, quarantine, reports, `CONTRACT OK` | Verifier panel |

### 16.2 Demo Execution Requirements
- **Live pipeline run** on demo data (not pre-recorded)
- **All components** from actual `main.py` execution
- **No frontend dependency** for CLI evaluation
- **Backup:** Pre-recorded video if live fails

### 16.3 Judging Q&A Preparation
| Likely Question | Prepared Answer |
|-----------------|-----------------|
| "How do you handle false merges?" | Cannot-link constraints + high threshold + cluster consistency; show false-merge test results |
| "What if attacker has better auxiliary data?" | Measured re-ID rate <5% on simulated voter roll; residual risk acknowledged in brief |
| "Why not use LLMs?" | Prohibited by rules; rule-based + CRF <50M params achieves >95% recall |
| "How do you ensure determinism?" | Sorted file processing, fixed seeds, HMAC with secret; demo: 3 runs = identical |
| "What about FHIR attachments?" | Base64 PDFs quarantined; text extracted and scanned; show example |

---

## 17. Completion Criteria for Every Phase

| Phase | Completion Evidence |
|-------|---------------------|
| **0** | `REPO_INVENTORY.md`, `CONTRACT_CHECKLIST.md`, `contracts.py` approved, `BACKLOG.md` |
| **1** | All 12 dataclasses + serialization tested; importable by all agents |
| **2** | Mixed-format dir → URM + quarantine; metrics per file; no crashes |
| **3** | Basic pipeline → `sanitized/`, `report.json`, `records.jsonl`; structural `CONTRACT OK` |
| **4** | Detection P/R/F1 ≥95/90/92 on labeled fixture; medical veto ≥98% precision |
| **5** | Clinical preservation 0% corruption on adversarial fixtures |
| **6** | Security gate passes clean; fails each injected violation; `validate_output.py` passes |
| **7** | Linkage precision ≥98%, recall ≥85%, false-merge <1% on labeled fixture |
| **8** | Determinism + secret rotation verified; pseudonyms in output + records.jsonl match |
| **9** | Date intervals exact; age bands correct; different secrets → different shifts |
| **10** | k≥5 for >95% records; attacker sim unique re-ID <5%; clinical utility >95% |
| **11** | Complex FHIR Bundle → valid sanitized R4; no PII in refs/ext/attachments/meta |
| **12** | All red-team tests pass; performance <12min/3.2GB; determinism; secret rotation; security review clean |
| **13** | Full 2GB input → <720s, <3.2GB RSS; profiling evidence |
| **14** | Demo runs 5-min script smoothly; all components from live pipeline |

---

## 18. Final Directive

**LOCKMATE must be engineered as a reliable privacy firewall, not a collection of impressive but disconnected features.**

The winning strategy:
1. **Establish a correct contract-compliant vertical slice first** (Phases 0-6)
2. **Add multilingual detection, conservative linkage, clinical preservation** (Phases 4, 5, 7, 8)
3. **Add attacker-aware privacy transformations** (Phases 9, 10)
4. **Harden FHIR and extended formats** (Phase 11)
5. **Validate adversarially and optimize** (Phases 12, 13)
6. **Demonstrate with evidence** (Phase 14)

**Every agent must:**
- Work from `context.md` and this plan
- Implement exactly the shared interfaces in `contracts.py`
- Support every important claim with test evidence
- Handle uncertain identity conservatively (null/quarantine)
- Quarantine every unsafe file explicitly
- Pass independent output verification before claiming completion

**LOCKMATE — Remove identities. Preserve medicine. Defeat linkage attacks.**

---

**END OF LOCKMATE-STRATEGY-AND-PLAN.MD**