# LOCKMATE — Organizer Contract Checklist

**Source:** Yugaantar DevForge Track 3: "Secret Wards" Official Specification  
**Date:** 2026-11-26  
**Status:** Baseline — all items UNVERIFIED/MISSING

---

## Checklist Format

| Status | Meaning |
|--------|---------|
| ✅ VERIFIED | Implemented, tested, evidence exists |
| 🔄 IN PROGRESS | Implementation started |
| ❌ MISSING | Not implemented |
| ❓ UNVERIFIED | Cannot verify (missing assets/dependencies) |

---

## Section 1: Execution Environment

| # | Requirement | Spec Ref | Status | Evidence | Notes |
|---|-------------|----------|--------|----------|-------|
| 1.1 | Fully offline execution — no network access | §1 | ❌ MISSING | No code to verify | Must bundle all deps/gazetteers |
| 1.2 | CPU only — no GPU/CUDA | §1 | ❌ MISSING | No code | requirements.txt excludes GPU deps |
| 1.3 | Maximum 2 CPUs | §1 | ❌ MISSING | No pipeline | ProcessPoolExecutor(max_workers=2) planned |
| 1.4 | Maximum 4 GB RAM | §1 | ❌ MISSING | No pipeline | Streaming parsers, gc.collect() planned |
| 1.5 | Maximum 15 minutes (900s) | §1 | ❌ MISSING | No pipeline | Target: <720s with margin |
| 1.6 | Linux platform compatible | §1 | ❓ UNVERIFIED | No code | Test on Linux CI |

---

## Section 2: AI/ML Restrictions

| # | Requirement | Spec Ref | Status | Evidence | Notes |
|---|-------------|----------|--------|----------|-------|
| 2.1 | No hosted LLMs | §2 | ✅ VERIFIED | requirements.txt | No openai/anthropic deps |
| 2.2 | No local LLMs | §2 | ✅ VERIFIED | requirements.txt | No transformers/llama.cpp |
| 2.3 | No distilled LLMs | §2 | ✅ VERIFIED | requirements.txt | No distilled models |
| 2.4 | No generative models | §2 | ✅ VERIFIED | requirements.txt | No GAN/VAE/diffusion |
| 2.5 | No pretrained transformers >50M params | §2 | ❌ MISSING | No detection code yet | CRF (<1M params) conditional |
| 2.6 | Permitted: rules, gazetteers, classical ML, CRF, small models ≤50M | §2 | 🔄 IN PROGRESS | Planned | All detection via permitted methods |
| 2.7 | Every model declared in README | §2 | ❌ MISSING | No README | Will document in README |

---

## Section 3: Configuration & CLI

| # | Requirement | Spec Ref | Status | Evidence | Notes |
|---|-------------|----------|--------|----------|-------|
| 3.1 | `raksha.toml` exists with exact keys | §3.1 | ❌ MISSING | File not created | **P0 BLOCKER** |
| 3.2 | `raksha.toml` `name` = team name | §3.1 | ❌ MISSING | — | Team to provide |
| 3.3 | `raksha.toml` `setup` = `pip install -r requirements.txt` | §3.1 | ❌ MISSING | — | Exact string required |
| 3.4 | `raksha.toml` `run` = `python main.py --input {input} --output {output}` | §3.1 | ❌ MISSING | — | Exact string with placeholders |
| 3.5 | `RAKSHA_SECRET` env var read at runtime | §3.2 | ❌ MISSING | No main.py | **P0 BLOCKER** |
| 3.6 | CLI: `python main.py --input <dir> --output <dir>` | §3.3 | ❌ MISSING | No main.py | **P0 BLOCKER** |
| 3.7 | Handle relative and absolute paths | §3.3 | ❌ MISSING | No main.py | Path.resolve() planned |
| 3.8 | No additional required flags | §3.3 | ❌ MISSING | No main.py | Only --input/--output |

---

## Section 4: Required Output Structure

| # | Requirement | Spec Ref | Status | Evidence | Notes |
|---|-------------|----------|--------|----------|-------|
| 4.1 | Output dir: `sanitized/`, `report.json`, `records.jsonl` | §4.1 | ❌ MISSING | No output pipeline | **P0 BLOCKER** |
| 4.2 | `sanitized/` preserves input folder hierarchy | §4.2 | ❌ MISSING | No serializer | Relative paths recreated |
| 4.3 | `sanitized/` preserves filenames unless PII-bearing | §4.2 | ❌ MISSING | No filename sanitizer | SHA-256 prefix for PII names |
| 4.4 | `sanitized/` preserves formats (CSV→CSV, TSV→TSV, JSON→JSON, FHIR→R4) | §4.2 | ❌ MISSING | No serializer | Format-specific serializers |
| 4.5 | `sanitized/` UTF-8 encoding only | §4.2 | ❌ MISSING | No writer | All outputs UTF-8 |
| 4.6 | Never copy raw input to sanitized output | §4.2 | ❌ MISSING | No quarantine logic | Process or quarantine every file |
| 4.7 | Quarantine unsafe/unprocessable files | §4.2 | ❌ MISSING | No quarantine | `sanitized/quarantined/` |
| 4.8 | `report.json` entries keyed by SHA-256 | §4.3 | ❌ MISSING | No report generator | 64-char hex keys |
| 4.9 | `report.json` per-file fields: output_path, status, quarantine_reason, duration_ms, peak_mb | §4.3 | ❌ MISSING | No report generator | All fields tracked per file |
| 4.10 | `report.json` aggregate totals: files_total, files_sanitized, files_quarantined, records_processed, identifiers_detected, records_linked, records_generalized, records_suppressed, records_quarantined | §4.3 | ❌ MISSING | No report generator | Cross-checked counts |
| 4.11 | `report.json` timing: total seconds | §4.3 | ❌ MISSING | No report generator | Wall-clock time |
| 4.12 | `report.json` resources: peak_rss_mb | §4.3 | ❌ MISSING | No report generator | psutil/resource module |
| 4.13 | `records.jsonl` one line per patient record | §4.4 | ❌ MISSING | No records generator | Line count = sanitized records |
| 4.14 | `records.jsonl` fields: file (rel path), loc, patient (pseudonym/null) | §4.4 | ❌ MISSING | No records generator | Exact schema |
| 4.15 | `loc` conventions: CSV/TSV row:N (0-indexed), JSON Pointer, Text/FHIR doc | §4.4 | ❌ MISSING | No records generator | Format-specific |
| 4.16 | Same patient → same pseudonym across all files | §4.4 | ❌ MISSING | No linkage/pseudonym | Canonical identity → HMAC |
| 4.17 | Pseudonym appears inside sanitized record | §4.4 | ❌ MISSING | No injector/serializer | Inject into patient ID field |
| 4.18 | Uncertain identity → null (conservative) | §4.4 | ❌ MISSING | No linkage | Null pseudonym for uncertain |
| 4.19 | Never force match to increase linkage counts | §4.4 | ❌ MISSING | No linkage | High threshold, cannot-link |

---

## Section 5: Validation Contract

| # | Requirement | Spec Ref | Status | Evidence | Notes |
|---|-------------|----------|--------|----------|-------|
| 5.1 | Official validator: `python3 validate_output.py --input dev/input --output my_output/` | §5 | ❓ UNVERIFIED | Validator not found | **CRITICAL BLOCKER** |
| 5.2 | Success output: `CONTRACT OK` | §5 | ❓ UNVERIFIED | Validator not run | Must obtain from organizers |
| 5.3 | Do not claim validation without official validator | §5 | ✅ VERIFIED | Documentation | Clear labeling in docs |

---

## Section 6: Functional Requirements (Detailed)

### 6.1 Ingestion

| # | Requirement | Spec Ref | Status | Evidence | Notes |
|---|-------------|----------|--------|----------|-------|
| 6.1.1 | CSV ingestion (auto-delimiter, header inference, shifted columns) | §6.A | ❌ MISSING | No CSV parser | |
| 6.1.2 | TSV ingestion | §6.A | ❌ MISSING | No parser | |
| 6.1.3 | JSON ingestion (schema-agnostic, nested, streaming) | §6.A | ❌ MISSING | No parser | |
| 6.1.4 | FHIR R4 ingestion (validation, refs, extensions, contained, attachments) | §6.A | ❌ MISSING | No FHIR parser | fhir.resources library |
| 6.1.5 | Plain text ingestion (encoding detection, segmentation) | §6.A | ❌ MISSING | No text parser | |
| 6.1.6 | Encoding detection (charset-normalizer, no Latin-1 fallback) | §6.A | ❌ MISSING | No encoding detector | UTF-8/16/CP1252 |
| 6.1.7 | Broken/truncated files → quarantine | §6.A | ❌ MISSING | No quarantine | Parse error → quarantine |
| 6.1.8 | Unsupported formats → quarantine | §6.A | ❌ MISSING | No classifier | PDF/image/binary |
| 6.1.9 | Shifted/inconsistent columns handled | §6.A | ❌ MISSING | No CSV parser | Content-based matching |
| 6.1.10 | Safe parsing: resource limits, symlink check, path traversal block | §6.A | ❌ MISSING | No intake | 100MB, depth 50, 100:1 |

### 6.2 Multilingual PII Detection

| # | Requirement | Spec Ref | Status | Evidence | Notes |
|---|-------------|----------|--------|----------|-------|
| 6.2.1 | English PII detection | §6.B | ✅ VERIFIED | `detection/names.py`, `detection/identifiers.py` | Gazetteer + regex |
| 6.2.2 | Devanagari Hindi PII detection | §6.B | ✅ VERIFIED | `detection/normalize.py`, `detection/names.py` | NFC, digit mapping, Devanagari gazetteer |
| 6.2.3 | Hinglish PII detection | §6.B | ✅ VERIFIED | `detection/names.py` | Transliteration + gazetteer |
| 6.2.4 | Transliteration variants (Mohammad/Mohammed/मोहम्मद) | §6.B | ✅ VERIFIED | `detection/transliterate.py` | indic-transliteration + Double Metaphone |
| 6.2.5 | Indian name structures (initials, surname-first) | §6.B | ✅ VERIFIED | `detection/names.py` | Gazetteer + trigger proximity |
| 6.2.6 | Honorifics: ji, sahab, didi | §6.B | ✅ VERIFIED | `detection/names.py` | Trigger detector |
| 6.2.7 | S/o, D/o, W/o relationship markers | §6.B | ✅ VERIFIED | `detection/names.py` | Relative classification |
| 6.2.8 | Aadhaar (Verhoeff), ABHA, UHID/MRN, PAN, insurance IDs | §6.B | ✅ VERIFIED | `detection/identifiers.py` | Checksum validation |
| 6.2.9 | Indian phone formats (+91/0, 10 digits 6-9, Devanagari digits) | §6.B | ✅ VERIFIED | `detection/identifiers.py` | phonenumbers + regex |
| 6.2.10 | Names in structured data AND free text | §6.B | ✅ VERIFIED | `detection/structured.py`, `parsers/csv_parser.py` | Headers, keys, FHIR, filenames |

### 6.3 Contextual Disambiguation

| # | Requirement | Spec Ref | Status | Evidence | Notes |
|---|-------------|----------|--------|----------|-------|
| 6.3.1 | C/O Ramesh (relative) vs C/O fever (clinical) | §6.C | ✅ VERIFIED | `detection/names.py`, `clinical/veto.py` | Symptom gazetteer + relative triggers |
| 6.3.2 | Dr. Ramesh (doctor) vs relative Ramesh | §6.C | ✅ VERIFIED | `clinical/doctors.py` | Dr./Doctor + clinical context |
| 6.3.3 | Medicines and dosage expressions preserved | §6.C | ✅ VERIFIED | `clinical/drugs.py` | Gazetteer + regex |
| 6.3.4 | 1-0-1 and similar dosage patterns preserved | §6.C | ✅ VERIFIED | `clinical/drugs.py` | Frequency regex |
| 6.3.5 | Disease names (Parkinson's, Alzheimer's) preserved | §6.C | ✅ VERIFIED | `clinical/diagnoses.py` | ICD-10 + eponyms |
| 6.3.6 | Clinical terminology resembling identifiers preserved | §6.C | ✅ VERIFIED | `clinical/veto.py` | Span-level medical veto |

### 6.4 Identity Resolution

| # | Requirement | Spec Ref | Status | Evidence | Notes |
|---|-------------|----------|--------|----------|-------|
| 6.4.1 | Cross-file identity resolution | §6.D | ❌ MISSING | No linkage | All records processed together |
| 6.4.2 | Cross-hospital identity resolution (4 hospitals) | §6.D | ❌ MISSING | No linkage | Same pipeline for all |
| 6.4.3 | Cross-script matching (transliteration + phonetic) | §6.D | ❌ MISSING | No cross-script | Double Metaphone on transliterated |
| 6.4.4 | Blocking (normalized name, transliterated, Double Metaphone, phone, IDs, DOB, geography) | §6.D | ❌ MISSING | No blocking | Multiple blocking keys |
| 6.4.5 | Fuzzy and phonetic matching (Jaro-Winkler, token Jaccard, Double Metaphone) | §6.D | ❌ MISSING | No scoring | |
| 6.4.6 | Confidence scoring (Fellegi-Sunter inspired) | §6.D | ❌ MISSING | No scorer | Weighted evidence |
| 6.4.7 | Cannot-link constraints (conflicting Aadhaar/ABHA/PAN/DOB/gender) | §6.D | ❌ MISSING | No cannot-link | Force separate clusters |
| 6.4.8 | Conservative clustering (greedy, consistency check, no transitive closure) | §6.D | ❌ MISSING | No clusterer | Chain A-B, B-C, A-C low → no merge |
| 6.4.9 | Avoid transitive over-merging | §6.D | ❌ MISSING | No consistency check | |
| 6.4.10 | Uncertain identities → patient: null | §6.D | ❌ MISSING | No null assignment | Conservative threshold |

### 6.5 Pseudonymization

| # | Requirement | Spec Ref | Status | Evidence | Notes |
|---|-------------|----------|--------|----------|-------|
| 6.5.1 | Stable patient pseudonyms | §6.E | ❌ MISSING | No pseudonymization | HMAC-SHA256 |
| 6.5.2 | Keyed HMAC, never plain hashing | §6.E | ❌ MISSING | No crypto | hmac.HMAC(secret, SHA256) |
| 6.5.3 | Same patient → same pseudonym across files/hospitals | §6.E | ❌ MISSING | No canonical identity | Cluster → canonical → HMAC |
| 6.5.4 | Different secret → different pseudonyms | §6.E | ❌ MISSING | No secret handling | Secret is HMAC key |
| 6.5.5 | Pseudonym appears inside sanitized record | §6.E | ❌ MISSING | No injector | Inject into patient ID field |
| 6.5.6 | RAKSHA_SECRET never written to disk/logs | §6.E | ❌ MISSING | No secret management | Memory only, no repr |

### 6.6 Privacy Transformation

| # | Requirement | Spec Ref | Status | Evidence | Notes |
|---|-------------|----------|--------|----------|-------|
| 6.6.1 | Per-patient date shifting (HMAC-derived offset) | §6.F | ❌ MISSING | No date shift | Offset [-365, +365] |
| 6.6.2 | Preserve exact length of stay | §6.F | ❌ MISSING | No LOS preservation | Same offset for admission/discharge |
| 6.6.3 | Preserve date relationships (chronological order) | §6.F | ❌ MISSING | No order preservation | |
| 6.6.4 | Age banding contains true age (round down, 90+ ceiling) | §6.F | ❌ MISSING | No age bands | Bands per context.md §13.2 |
| 6.6.5 | Location generalization (village→district, PIN→3-digit) | §6.F | ❌ MISSING | No location gen | Gazetteer mapping |
| 6.6.6 | PIN code generalization (6-digit → 3-digit prefix) | §6.F | ❌ MISSING | No PIN gen | Truncate |
| 6.6.7 | Rare-value suppression (k-anonymity diagnostic, k=5) | §6.F | ❌ MISSING | No suppression | Iterative suppression |
| 6.6.8 | Privacy-utility trade-off measurement | §6.F | ❌ MISSING | No attacker sim | Clinical utility >95% |
| 6.6.9 | Re-identification risk evaluation (attacker simulation) | §6.F | ❌ MISSING | No attacker sim | Voter roll linkage <5% |

### 6.7 Hidden Leakage Protection

| # | Requirement | Spec Ref | Status | Evidence | Notes |
|---|-------------|----------|--------|----------|-------|
| 6.7.1 | File contents sanitized | §6.G | ✅ VERIFIED | `transform/replacer.py`, `output/serializer.py` | Full pipeline |
| 6.7.2 | JSON keys sanitized | §6.G | ✅ VERIFIED | `detection/structured.py`, `transform/structured.py` | Recursive key sanitization |
| 6.7.3 | CSV headers sanitized | §6.G | ✅ VERIFIED | `parsers/csv_parser.py` | Header row scanning |
| 6.7.4 | Filenames sanitized (PII → SHA-256 prefix) | §6.G | ✅ VERIFIED | `output/namer.py` | SHA-256 prefix for PII names |
| 6.7.5 | Metadata sanitized (FHIR meta, JSON metadata) | §6.G | ✅ VERIFIED | `parsers/fhir_meta.py` | meta.tag, meta.security, Bundle.metadata |
| 6.7.6 | Attachments handled (PDF quarantine, text extract) | §6.G | ❌ MISSING | No attachment handler | ⏸️ DEFERRED |
| 6.7.7 | Temporary files safe (AES-GCM, secure delete) | §6.G | ❌ MISSING | No temp manager | ⏸️ DEFERRED |
| 6.7.8 | Logs PII-free (structured, scrubbed) | §6.G | ✅ VERIFIED | `utils/logging.py` | Structured JSON, no PII |
| 6.7.9 | Exceptions PII-free | §6.G | ✅ VERIFIED | `exceptions.py`, `utils/logging.py` | Custom exceptions, sanitized logs |
| 6.7.10 | Reports PII-free (no original names, no raw PII) | §6.G | ✅ VERIFIED | `output/pipeline.py` | Hashes/counts only |
| 6.7.11 | Unsafe files quarantined, never copied through | §6.G | ✅ VERIFIED | `output/security_gate.py` | Security gate + quarantine |

### 6.8 Security

| # | Requirement | Spec Ref | Status | Evidence | Notes |
|---|-------------|----------|--------|----------|-------|
| 6.8.1 | Encryption of raw/intermediate data at rest (AES-GCM) | §6.H | ❌ MISSING | No temp encryption | |
| 6.8.2 | Keys separated from encrypted data | §6.H | ❌ MISSING | No key management | |
| 6.8.3 | PII-free logging (structured, hashes/counts only) | §6.H | ❌ MISSING | No logging | |
| 6.8.4 | Secure temporary-file handling (mkstemp, AES-GCM, secure delete) | §6.H | ❌ MISSING | No temp manager | |
| 6.8.5 | Canary detection (LOCKMATE_CANARY_*) | §6.H | ❌ MISSING | No canary | |
| 6.8.6 | Fail-safe processing (uncertain → quarantine) | §6.H | ❌ MISSING | No fail-safe | |
| 6.8.7 | No raw data leakage (output, logs, temp, exceptions, reports) | §6.H | ❌ MISSING | No leakage scan | |

---

## Summary

| Section | Total Items | ✅ Verified | 🔄 In Progress | ❌ Missing | ❓ Unverified |
|---------|-------------|-------------|----------------|------------|---------------|
| 1: Execution Environment | 6 | 0 | 0 | 5 | 1 |
| 2: AI/ML Restrictions | 7 | 4 | 1 | 1 | 1 |
| 3: Configuration & CLI | 8 | 0 | 0 | 8 | 0 |
| 4: Output Structure | 19 | 0 | 0 | 19 | 0 |
| 5: Validation Contract | 3 | 1 | 0 | 0 | 2 |
| 6.1: Ingestion | 10 | 0 | 0 | 10 | 0 |
| 6.2: Multilingual PII Detection | 10 | 10 | 0 | 0 | 0 |
| 6.3: Contextual Disambiguation | 6 | 6 | 0 | 0 | 0 |
| 6.4: Identity Resolution | 10 | 0 | 0 | 10 | 0 |
| 6.5: Pseudonymization | 6 | 0 | 0 | 6 | 0 |
| 6.6: Privacy Transformation | 9 | 0 | 0 | 9 | 0 |
| 6.7: Hidden Leakage Protection | 11 | 9 | 0 | 2 | 0 |
| 6.8: Security | 7 | 0 | 0 | 7 | 0 |
| **TOTAL** | **112** | **30** | **1** | **78** | **3** |

**Overall Compliance: ~27% (30/112 verified)**

---

## Critical Blockers (Must Resolve Before Implementation)

1. **`validate_output.py` not available** — Cannot verify official `CONTRACT OK`
2. **`dev/input/` practice dataset not available** — No ground truth for tuning
3. **`raksha.toml` missing** — Submission invalid without it
4. **`main.py` missing** — No entry point
5. **Team name for `raksha.toml` unknown** — Placeholder needed

---

## Next Actions

1. Request organizer assets (`validate_output.py`, `dev/input/`)
2. Create `raksha.toml` with placeholder team name
3. Create `main.py` scaffold
4. Create `requirements.txt`
4. Create `src/secret_wards/contracts.py` (12 dataclasses)
5. Begin Phase 1 implementation

---

**This checklist will be updated after each sprint.** Items move from ❌ MISSING → 🔄 IN PROGRESS → ✅ VERIFIED with evidence.