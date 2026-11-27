# LOCKMATE Implementation Gap Analysis

**Date:** 2026-11-26  
**Auditor:** Claude Engineering Agent  
**Based On:** Repository Audit + Toolkit Audit  
**Status:** Phase 1 Complete

---

## 1. Gap Classification Framework

| Priority | Definition | Timeline |
|----------|------------|----------|
| **P0 - Contract Blocking** | Prevents `CONTRACT OK` or causes penalties | Immediate |
| **P1 - Competitive Differentiation** | Required for scoring >50pts on hidden data | Phase 2-3 |
| **P2 - Extended Engineering** | Nice-to-have, demo, optimization | Phase 4+ |

---

## 2. P0 Gaps - Contract Blocking (Must Fix First)

### 2.1 Output Format Mismatches

| # | Issue | Location | Toolkit Expectation | Current LOCKMATE | Fix Effort |
|---|-------|----------|---------------------|------------------|------------|
| 1 | `report.json` `files` is object | `contracts.py:633`, `output/pipeline.py:233` | **Array** of entries | Dict keyed by SHA-256 | Low |
| 2 | `FileReportEntry` field `output_path` | `contracts.py:552,567` | **`output`** | `output_path` | Low |
| 3 | `records.jsonl` backslash paths | `output/pipeline.py:270` | **Forward slashes** | Windows backslashes | Low |
| 4 | `records.jsonl` missing `sanitized/` prefix | `output/pipeline.py:270` | `sanitized/path/file.csv` | `path/file.csv` | Low |
| 5 | Exit code 1 on success | `main.py:179`, `pipeline/full.py:109` | **Exit 0** | False `QuarantineAllError` | Low |
| 6 | `identifiers_detected` always 0 | `pipeline/full.py`, `detection/placeholder.py` | Actual count | Not propagated | Medium |

**Impact:** `validate_output.py` will fail with `CONTRACT PROBLEMS FOUND` until fixed.

---

### 2.2 Detection Gaps (Direct Penalties)

| # | Gap | Trap Type | Penalty if Missed | Status |
|---|-----|-----------|-------------------|--------|
| 7 | **JSON keys as PII** | Hidden Leakage | −1 per unique ID | ❌ Missing (`detection/structured.py` stub) |
| 8 | **CSV headers as PII** | Hidden Leakage | −1 per unique ID | ❌ Partial (scans but not integrated) |
| 9 | **Filenames with PII** | Hidden Leakage | −1 per unique ID | ⚠️ Detected but not in report |
| 10 | **FHIR metadata/extensions** | Hidden Leakage | −1 per unique ID | ❌ Missing (`parsers/fhir_meta.py`, `fhir_references.py`) |
| 11 | **Base64 attachments** | Hidden Leakage | −1 per unique ID | ❌ Missing (`parsers/fhir_attachments.py`) |
| 12 | **\u-escaped Devanagari** | Hidden Leakage | −1 per unique ID | ⚠️ Normalizer handles but not scanned |
| 13 | **Export metadata PII** | Hidden Leakage | −1 per unique ID | ❌ Not scanned |

**Impact:** Each unique direct identifier surviving = −1 point (cap −25). Canaries in these channels = −3 each (cap −15).

---

### 2.3 Names Detection Broken

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| 14 | Circular import `names.py` ↔ `gazetteer.py` | `detection/names.py:18` | Module fails to load |
| 15 | `NameDetector.detect()` calls `_detect_latin_names()` which detects emails/phones/PAN - **wrong** | `detection/names.py:193-268` | Detects identifiers as names |
| 16 | `_detect_standalone_latin_names()` never called | `detection/names.py:301` | Core name detection missing |
| 17 | Devanagari/Hinglish detection uses wrong gazetteer keys | `detection/names.py:371-462` | Gazetteer lookup fails |
| 18 | Medical veto `_would_be_vetoed()` logic incomplete | `detection/names.py:464-485` | False vetoes on medical terms |

**Impact:** Language trap (Devanagari/Hinglish names) will have 0% recall → major detection score loss.

---

### 2.4 FHIR Incomplete

| # | Missing Feature | Location | Toolkit Requirement |
|---|-----------------|----------|---------------------|
| 19 | Reference traversal (`Patient.reference`, `subject.reference`) | `parsers/fhir_references.py` | FHIR validity (15% of integrity) |
| 20 | Contained resource extraction | `parsers/fhir_parser.py:151-155` | All resources must be sanitized |
| 21 | Extension handling | `parsers/fhir_parser.py:155-158` | Extensions can hold PII |
| 22 | Binary attachment quarantine | `parsers/fhir_attachments.py` | PDF/images → quarantine |
| 23 | Narrative text scanning | `parsers/fhir_parser.py` | `div` content can hold PII |
| 24 | FHIR R4 validation on output | `output/serializer.py:162-219` | Must pass `fhir.resources` validator |

**Impact:** FHIR files either quarantined (losing records) or leak PII (penalties).

---

### 2.5 Metrics Not Connected

| # | Metric | Source | Destination | Status |
|---|--------|--------|-------------|--------|
| 25 | `identifiers_detected` | Detection engines | `report.json` counts | ❌ Not tracked |
| 26 | `records_linked` | Linkage (missing) | `report.json` counts | ❌ N/A |
| 27 | `records_generalized` | Privacy (missing) | `report.json` counts | ❌ N/A |
| 28 | `records_suppressed` | Privacy (missing) | `report.json` counts | ❌ N/A |
| 29 | Per-file timing/memory | `FileMetrics` | `report.json` files[] | ⚠️ Partial |

**Impact:** Report quality score (10% of integrity) penalized for dishonest counts.

---

## 3. P1 Gaps - Competitive Differentiation

### 3.1 Identity Resolution (Entire `linkage/` Package Missing)

| Module | Purpose | Spec Reference |
|--------|---------|----------------|
| `linkage/blocking.py` | Blocking keys: normalized name, transliteration, Double Metaphone, phone, IDs, DOB year, district | SCORING.md §2, DATASET.md language/fragmented traps |
| `linkage/candidates.py` | Candidate pair generation from blocking keys | F0.5 pairwise precision/recall |
| `linkage/scoring.py` | Pairwise Fellegi-Sunter scoring with weights | SCORING.md §2 |
| `linkage/constraints.py` | Cannot-link: conflicting Aadhaar, DOB, gender | False merge prevention |
| `linkage/clustering.py` | Conservative greedy clustering, no transitive closure | SCORING.md §2 |
| `linkage/canonical.py` | Canonical identity key for pseudonym derivation | SPEC.md §6, ATTACKS.md A6 |
| `linkage/pipeline.py` | End-to-end linkage orchestration | — |

**Scoring Impact:** 15% weight. Zero pseudonyms = 0 for this category. False merges cost more than missed links (F0.5).

---

### 3.2 Pseudonymization (Entire `crypto/` Package Missing)

| Module | Purpose | Spec Reference |
|--------|---------|----------------|
| `crypto/secret.py` | Load/validate `RAKSHA_SECRET` from env | SPEC.md §4 |
| `crypto/pseudonym.py` | HMAC-SHA256 with domain separation → `PSN-XXXXXXXX` | SPEC.md §6, ATTACKS.md A6/A7 |
| `crypto/date_shift.py` | Per-patient shift from HMAC(secret, "date_shift" + pseudonym) | ATTACKS.md A5 (global shift recovery) |
| `crypto/injector.py` | Inject pseudonym into structured fields | SPEC.md §6 (pseudonym must appear in record) |

**Critical:** Must use **per-patient secret shifts** (not global) to defeat A5 targeted attack. HMAC with `RAKSHA_SECRET` required (not plain hash) to defeat A6 inversion.

---

### 3.3 Quasi-Identifier Privacy (Entire `privacy/` Package Missing)

| Module | Purpose | Spec Reference |
|--------|---------|----------------|
| `privacy/date_fields.py` | Identify all date fields (DOB, admission, discharge, visit, lab) | SCORING.md §3 temporal, §4 generalization |
| `privacy/date_shift.py` | Apply per-patient shift preserving intervals | ATTACKS.md A5 |
| `privacy/age_bands.py` | 5-year bands containing true age (truthful) | SCORING.md §4 generalization |
| `privacy/location.py` | Village→district, PIN→3-digit, rare→state | SCORING.md §4 generalization |
| `privacy/gazetteer.py` | Census 2011 village/district/state/PIN mapping | DATASET.md re-id trap |
| `privacy/equivalence.py` | Build QI equivalence classes (age_band, district, gender, diagnosis, LOS) | SCORING.md §3 privacy |
| `privacy/suppression.py` | Iterative k-anonymity (k≥5): suppress rarest → generalize age → generalize location | ATTACKS.md re-id trap |
| `privacy/pipeline.py` | End-to-end privacy transformations | — |

**Scoring Impact:** 25% privacy weight + 20% utility weight. Privacy credit coupled: `privacy = resistance × min(1, utility/0.40)`. "Delete everything" scores ~22 (redact_all baseline).

---

### 3.4 Advanced Detection (Phase 4 Upgrades)

| Upgrade | Current | Target | Effort |
|---------|---------|--------|--------|
| CRF name tagger | None | `sklearn-crfsuite` if >5% F1 gain | Medium |
| Gazetteer expansion | Minimal auto-generated | Census names, Wikipedia, public lists | Medium |
| Transliteration variants | Basic | Mohammad/Mohammed/Mohd/Md./मोहम्मद/मुहम्मद | Low |
| Contextual classification | Rule-based | Role-aware (patient/relative/doctor) | Medium |
| Second-pass residual scan | Stub | Re-scan output for patient's known IDs | Low |

---

## 4. P2 Gaps - Extended Engineering

| Area | Description | Priority |
|------|-------------|----------|
| FHIR Attachment text extraction | OCR for scanned PDFs in `Binary` resources | Low |
| Metadata/attachment handling | DICOM, HL7 CDA, images | Low |
| Advanced adversarial tests | Membership inference, attribute inference | Medium |
| Performance optimization | Parallel file processing, streaming FHIR, vectorized detection | Medium |
| Frontend demonstration | Streamlit app for judging | Low (optional) |

---

## 5. Dependency Mapping: Toolkit → LOCKMATE

| Toolkit Capability | LOCKMATE Module | Current Status | Required Action |
|-------------------|-----------------|----------------|-----------------|
| Data loading (dev/input) | `intake/pipeline.py` | ✅ Working | Fix encoding for UTF-16, cp1252 |
| Format detection | `intake/classifier.py` | ✅ Working | Add FHIR content sniffing |
| CSV/TSV parsing | `parsers/csv_parser.py` | ✅ Working | Handle ragged rows, shifted columns |
| JSON parsing | `parsers/json_parser.py` | ✅ Working | Handle deep nesting, malformed |
| Text parsing | `parsers/text_parser.py` | ✅ Working | Handle Hinglish, encoding |
| FHIR parsing | `parsers/fhir_parser.py` | ⚠️ Partial | Add references, extensions, contained, attachments |
| PII detection - identifiers | `detection/identifiers.py` | ✅ Working | Integrate with structured scanner |
| PII detection - names | `detection/names.py` | ❌ Broken | **Fix circular import, implement detection** |
| PII detection - structured | `detection/structured.py` | ❌ Missing | **Scan headers, keys, filenames, metadata** |
| Clinical preservation | `clinical/` | ✅ Working | Integrate with detection veto |
| Unicode normalization | `detection/normalize.py` | ✅ Working | Used by detection |
| Transliteration | `detection/transliterate.py` | ✅ Working | Used by names/linkage |
| Gazetteers | `detection/gazetteer.py` | ✅ Working | Expand with real data |
| Replacement | `transform/replacer.py` | ✅ Working | Offset-map aware |
| Structured sanitization | `transform/structured.py` | ✅ Working | Format-specific |
| Serialization | `output/serializer.py` | ✅ Working | Fix FHIR validation |
| Filename sanitization | `output/namer.py` | ✅ Working | SHA-256 prefix |
| Atomic writes | `output/writer.py` | ✅ Working | Temp→rename |
| Security gate | `output/security_gate.py` | ✅ Working | Residual PII scan |
| Report generation | `output/pipeline.py` | ❌ Format wrong | **Fix to match SPEC** |
| Records generation | `output/pipeline.py` | ❌ Path format wrong | **Fix forward slashes, prefix** |
| Identity linkage | `linkage/` | ❌ Missing | **Implement full package** |
| Pseudonymization | `crypto/` | ❌ Missing | **Implement full package** |
| Date shifting | `privacy/date_shift.py` | ❌ Missing | **Implement** |
| Age bands | `privacy/age_bands.py` | ❌ Missing | **Implement** |
| Location generalization | `privacy/location.py` | ❌ Missing | **Implement** |
| k-anonymity suppression | `privacy/suppression.py` | ❌ Missing | **Implement** |

---

## 6. File Ownership & Coordination

| File/Module | Current Owner | Required Changes | Coordination Needed |
|-------------|---------------|------------------|---------------------|
| `contracts.py` | Agent 0 (Orchestrator) | Fix `FileReportEntry.output_path`→`output`, `FullReport.files`→List | All agents |
| `output/pipeline.py` | Agent 6 (Output) | Fix report format, records paths | Agent 0 |
| `detection/names.py` | Agent 3 (Detection) | Fix circular import, implement detection | Agent 0 (gazetteer interface) |
| `detection/structured.py` | Agent 3 (Detection) | Implement header/key/filename scanning | Agent 2 (parser integration) |
| `parsers/fhir_*.py` | Agent 2 (Ingestion) | Implement references, extensions, attachments | Agent 3 (detection integration) |
| `linkage/` | Agent 4 (Linkage) | New package | Agent 3 (needs PII spans), Agent 0 (contracts) |
| `crypto/` | Agent 4 (Linkage) | New package | Agent 0 (secret handling) |
| `privacy/` | Agent 5 (Clinical/Privacy) | New package | Agent 4 (needs pseudonyms), Agent 0 |
| `output/report.py` | Agent 6 (Output) | **Create new file** | Agent 0 (uses contracts) |

---

## 7. Estimated Effort by Phase

| Phase | Tasks | Est. Days | Dependencies |
|-------|-------|-----------|--------------|
| **P0 Fixes** | Fix report format, records paths, exit code, metrics, names detection, structured scanning | 5-7 | None |
| **P0 FHIR** | Complete FHIR parser, serializer validation | 3-5 | P0 Fixes |
| **P1 Linkage** | Implement `linkage/` package (7 modules) | 7-10 | P0 Fixes, Detection |
| **P1 Crypto** | Implement `crypto/` package (4 modules) | 3-5 | P0 Fixes, Linkage |
| **P1 Privacy** | Implement `privacy/` package (8 modules) | 7-10 | P1 Crypto, Gazetteer |
| **P1 Integration** | Wire all packages in `pipeline/full.py` | 3-5 | All above |
| **P2 Red-team** | Implement adversarial tests, canary verification | 5-7 | P1 Integration |
| **P2 Optimization** | Performance tuning, parallelization | 3-5 | P2 Red-team |
| **P2 Demo** | Streamlit frontend (optional) | 3-5 | P1 Integration |

**Total: ~40-60 days for full competitive implementation**

---

## 8. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Toolkit validator stricter than SPEC | Medium | High | Run `validate_output.py` after every P0 fix |
| Hidden data has unseen name formats | High | High | Build context-aware rules, not string lists |
| FHIR validation fails on output | Medium | Medium | Use `fhir.resources` round-trip in serializer |
| Cross-script linkage fails on hidden data | High | High | Test with synthetic multilingual fixtures early |
| Performance exceeds 15min/4GB on large data | Medium | High | Profile early, implement streaming/parallel |
| Canary leakage in logs/temp files | Low | Critical | PII-scrubbed logging, encrypted temp, atomic writes |
| False merge rate >1% | Medium | High | Conservative clustering, cannot-link constraints |
| Secret rotation not working | Low | High | Test determinism + different secret early |

---

## 9. Immediate Next Steps (This Session)

1. **Fix `contracts.py`** - Change `FileReportEntry.output_path` to `output`, `FullReport.files` to `List[FileReportEntry]`
2. **Fix `output/pipeline.py`** - Generate report.json with array format, forward slashes in records.jsonl
3. **Fix `main.py`** - Remove false `QuarantineAllError` on success
4. **Fix `detection/names.py`** - Resolve circular import, implement proper name detection
5. **Implement `detection/structured.py`** - Scan CSV headers, JSON keys, filenames, FHIR metadata
6. **Run `validate_output.py`** - Verify `CONTRACT OK` on practice data
7. **Run `check_dev.py`** - Baseline leak/medical/linking metrics

---

## 10. Success Criteria for Phase 1 Completion

- [ ] `validate_output.py --input dev/input --output my_output` → `CONTRACT OK`
- [ ] `check_dev.py --output my_output` → 0 canaries, <10% leaks, >90% medical kept
- [ ] All existing unit tests still pass
- [ ] Deterministic: 2 runs same secret = byte-identical `sanitized/` + `records.jsonl`
- [ ] Secret rotation: 2 runs different secrets = different pseudonyms/shifts
- [ ] No raw PII in stdout/stderr/logs/report.json/records.jsonl/filenames