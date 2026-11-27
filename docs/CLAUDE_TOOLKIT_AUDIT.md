# Secret Wards Toolkit Audit

**Date:** 2026-11-26  
**Auditor:** Claude Engineering Agent  
**Source:** https://github.com/Reinforce-SST/Secret-Wards-ToolKit  
**Status:** Phase 1 Complete

---

## 1. Toolkit Overview

The Secret Wards Toolkit is the **official organizer-provided evaluation framework** for Track 3: Secret Wards. It provides:

- Practice dataset (`dev/input/`) with 200+ files across 4 hospital systems
- Ground truth (`dev/truth/truth.json`) with entity-level annotations
- Attacker knowledge (`dev/attacker/registry.csv`, `known_facts.jsonl`)
- Format validator (`validate_output.py`) - **must print `CONTRACT OK`**
- Practice self-check (`check_dev.py`) - leaks, medical preservation, linking
- Pre-submission check (`check_submission.py`) - `READY TO SUBMIT`
- Starter kit (`starter/`) - working skeleton with contract compliance
- Full documentation (`docs/`) - SPEC, SCORING, ATTACKS, DATASET, etc.

---

## 2. Key Files Inspected

| File | Purpose | Critical Findings |
|------|---------|-------------------|
| `validate_output.py` | Format validator | **Contract checker only** - checks structure, not scoring. Expects `report.json` with `files` as **array**, `output` field (not `output_path`), forward slashes in paths |
| `check_dev.py` | Practice self-check | Compares output against `truth.json`; reports leaks by type/script/channel, canaries, medical preservation %, linkage precision/recall/F0.5, false merges |
| `check_submission.py` | Pre-submit check | Validates `raksha.toml`, README, runs repo 3x (same secret, different secret, determinism) |
| `starter/main.py` | Reference implementation | Standard library only; regex detection; **links nothing** (baseline ~8 pts); correct output format |
| `dev/truth/truth.json` | Ground truth | Per-record entities with type, surface, script, channel, role, critical flag; preserve probes; linkability rules |
| `dev/attacker/registry.csv` | Attacker knowledge | Voter-roll style: name, relative, gender, age, house, mohalla, village, tehsil, district, PIN + leaked contacts overlay |
| `dev/attacker/known_facts.jsonl` | Targeted attack data | ~30% patients: visit date, hospital, condition (rare for traps), LOS; decoys included |
| `docs/SPEC.md` | Submission contract | **Authoritative** - exact output format, `raksha.toml` schema, environment variables |
| `docs/SCORING.md` | Scoring formulas | 6 categories, weights, F2 detection, F0.5 linkage, privacy-utility coupling, penalties |
| `docs/ATTACKS.md` | Attack specifications | A1-A7 attacks: direct exposure, record linkage, profile aggregation, targeted (with shift recovery), pseudonym inversion, cross-release |
| `docs/DATASET.md` | Dataset description | 4 hospitals, 6 trap types, unseen-format round, canaries, homonyms |
| `scoring.toml` | Scoring config | All weights, thresholds, penalties; SHA-256 stamped on scorecards |

---

## 3. Submission Contract (from SPEC.md)

### Required `raksha.toml`:
```toml
[submission]
name  = "team-name"
setup = "pip install -r requirements.txt"     # network ALLOWED
run   = "python main.py --input {input} --output {output}"  # network DENIED
```

### Required CLI:
```bash
python main.py --input <input_dir> --output <output_dir>
```

### Environment Variables:
| Variable | Purpose |
|----------|---------|
| `RAKSHA_SECRET` | Per-release secret for HMAC pseudonyms & date shifts; **never write anywhere** |
| `RAKSHA_INPUT` / `RAKSHA_OUTPUT` | Same as CLI args |
| `RAKSHA_CPUS`, `OMP_NUM_THREADS`, etc. | CPU budget (2) |
| `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` | Model hubs offline |

### Required Output Structure:
```
output/
├── sanitized/           # Mirror of input tree, same relative paths
│   └── quarantined/     # Unsafe files here (optional per SPEC, but toolkit expects in sanitized/)
├── report.json          # REQUIRED: every input file by SHA-256 + totals
├── records.jsonl        # REQUIRED for identity credit: file, loc, patient
└── logs/                # Optional: scanned for PII
```

### report.json Schema (from SPEC.md):
```json
{
  "schema": "raksha-report/1",
  "files": [
    {"input_sha256": "9f2c...", "output": "sanitized/path/file.csv", "status": "sanitized"},
    {"input_sha256": "51aa...", "output": null, "status": "quarantined", "reason": "unsupported_format"}
  ],
  "counts": {
    "files_total": 817,
    "files_sanitized": 809,
    "files_quarantined": 8,
    "records_processed": 5756,
    "identifiers_detected": 21950,
    "records_linked": 5690,
    "records_generalized": 2100,
    "records_suppressed": 3,
    "records_quarantined": 0
  },
  "entities": {"PATIENT_NAME": 6600, "PHONE": 1540},
  "timing": {"seconds": 41.2},
  "resources": {"peak_rss_mb": 380.5}
}
```

**Key Contract Points:**
- `files` is an **ARRAY** (not object)
- Field is `output` (not `output_path`)
- `status` ∈ {"sanitized", "quarantined", "suppressed"}
- Every input file must appear exactly once
- `output` paths include `sanitized/` prefix
- `entities` object is optional but recommended

### records.jsonl Schema:
```jsonl
{"file": "sanitized/registration/hospital.csv", "loc": "row:12", "patient": "PSN-7Q2K9D"}
{"file": "sanitized/opd/visits.json", "loc": "/visits/3", "patient": "PSN-7Q2K9D"}
{"file": "sanitized/discharge/note.txt", "loc": "doc", "patient": "PSN-7Q2K9D"}
{"file": "sanitized/registration/hospital.csv", "loc": "row:40", "out": "row:39", "patient": "PSN-11XQ0A", "status": "generalized"}
```

- `file`: relative to output root, includes `sanitized/` prefix, **forward slashes**
- `loc`: input locator (`row:N`, JSON pointer, `doc`)
- `out`: output locator if different (e.g., after row suppression)
- `patient`: pseudonym or `null`
- `status`: optional (`sanitized`, `generalized`, `suppressed`)

---

## 4. Practice Dataset Structure

```
dev/input/
├── registration/          # 4 hospital systems, 4 formats, 4 encodings
│   ├── sanjeevani_registration.csv      # UTF-8 BOM, day-first dates
│   ├── jeevanjyoti_patients.tsv         # UTF-16, Hindi headers, Devanagari rows
│   ├── arogya_legacy_export.csv         # cp1252, split names, ragged rows, month-first
│   └── dhh_patients.json                # UTF-8, nested JSON, misspelled Aadhaar key
├── opd/                   # Nested JSON per hospital/month
├── discharge/             # English, Hindi, fragmentary notes
├── notes/                 # Hinglish nursing notes
├── prescriptions/         # English/Hinglish/Hindi OPD prescriptions
├── fhir/                  # FHIR R4 document Bundles
├── lab/                   # Lab CSVs, JSON, WhatsApp forwards
├── billing/               # Insurance claims
├── clean/                 # No PII documents (ward census, drug formulary, protocols)
├── misc/                  # Traps: truncated JSON, PDF, JPEG, empty, corrupt, deep JSON, XML, mislabeled CSV
└── ... (200+ files total)
```

### Four Hospital Systems (from DATASET.md):

| System | Registration Export | Encoding | Date Convention |
|--------|---------------------|----------|-----------------|
| Sanjeevani Multispeciality | CSV, full names, Aadhaar, ABHA, duplicate file | UTF-8 BOM | Day-first (DD/MM/YYYY) |
| Jeevan Jyoti Charitable | TSV, Hindi headers, Devanagari rows | **UTF-16** | Day-first |
| Arogya Seva Sadan | Legacy CSV, split first/last, ragged, multi-line notes | **cp1252** | **Month-first** (MM/DD/YYYY) |
| District Hospital Hardoi | Nested JSON, Aadhaar as number, misspelled key | UTF-8 | ISO (YYYY-MM-DD) |

---

## 5. Trap Types (What Each Tests)

| Trap | Description | Scored By |
|------|-------------|-----------|
| **Language** | Same person in Latin, Devanagari, Hinglish; sometimes no ID | Leak recall per script; cross-script linking |
| **Meaning** | Relatives vs doctors (same name), "C/O name" vs "C/O complaint", wards, doses (1-0-1), eponyms | Relative leaks vs doctor/dose preservation |
| **Fragmented Identity** | Note with only "<first name>, W/o <husband>" + date | Linking through name + relative |
| **Re-identification** | Very old patients, tiny villages, rare diseases, exact dates | Attack arena (ATTACKS.md) |
| **Clinical Integrity** | DOB, admission/discharge (real LOS), vitals, labs, doses, diagnoses | Values kept, intervals kept, truthful bands, statistics |
| **Hidden Leakage** | PII in JSON keys, CSV headers, filenames, export metadata, FHIR narrative, base64 attachments, \u-escaped Devanagari | Leak scan per hiding place |
| **Robustness** | Large export, deep JSON, truncated JSON, XML, PDF, JPEG, empty, invalid UTF-8, JSON behind .csv | Speed, memory, no crash, correct quarantine |

---

## 6. Attack Specifications (from ATTACKS.md)

### Attacker Knowledge:
1. **Release**: All `sanitized/` content + pseudonyms actually in records
2. **Registry** (`attacker/registry.csv`): 4-5× patient population with name, relative, gender, age, house, mohalla, village, tehsil, district, PIN; 60% have leaked phone/email/last-4-Aadhaar
3. **Known Facts** (`attacker/known_facts.jsonl`): ~30% patients + all trap patients: visit date, hospital, sometimes condition (rare for traps), LOS; decoys mixed in
4. **Public**: Transliteration tables, gazetteers, rare-disease vocab

### Seven Attacks:
| Attack | Description | Key Insight |
|--------|-------------|-------------|
| **A1: Direct Exposure** | Surviving direct ID or full name anywhere | Side channels scanned too |
| **A2/A3: Record Linkage** | Sweeney-style: phone → email → last-4 → masked phone → district → gender → age ±1/2y → birth year → tehsil → village → PIN → PIN prefix. Filters that empty set are skipped. Weights: full name ×60, given ×8, surname ×3, relative ×8, house ×2 | Wrong evidence weakens but doesn't crash |
| **A4: Profile Aggregation** | Join records via shared pseudonyms + reference values (patient_ref, UHID); pool evidence; re-attack | Max of record-level and profile-level probability |
| **A5: Targeted (Shift Recovery)** | Match known facts (visit date, rare condition ×8 weight, LOS intervals). **Recover global date shift** from ≥2 high-confidence re-IDs; unshift all dates. Per-patient secret shifts defeat this. | **Global shift protects nobody**; per-patient HMAC shifts required |
| **A6: Pseudonym Inversion** | Expand patient originals (UHID, Aadhaar, phone, ABHA, name) with transforms: case, digits, MD5/SHA1/256/512 (prefix ≥8), base64, reversal. Match pseudonym against transforms. | **Unkeyed hashing caught**; HMAC with secret not invertible |
| **A7: Cross-Release Linkability** | Run with different `RAKSHA_SECRET`; risk = max(same pseudonyms, same date shifts) | **Stable pseudonyms = linkable releases** |

### Normalization (applied to both sides before matching):
- NFKC, Cyrillic/Greek homoglyphs folded, zero-width removed, Indic digits → ASCII, Latin diacritics stripped, casefolded
- Hidden payloads decoded (base64, hex, \uXXXX, HTML entities, %encoding)

---

## 7. Scoring Breakdown (from SCORING.md + scoring.toml)

| Category | Weight | Score Formula |
|----------|--------|---------------|
| **Detection & Contextual Intelligence** | 20% | F2 = 5PR/(4P+R); recall = 0.5×macro(type) + 0.5×macro(script) |
| **Identity Resolution** | 15% | 0.4×F0.5 + 0.3×B³F1 + 0.1×language trap + 0.1×fragmented trap + 0.1×homonym separation |
| **Adversarial Privacy** | 25% | (1−risk) × min(1, utility/0.40); risk = Σwᵢ×riskᵢ/Σwᵢ |
| **Clinical Utility** | 20% | 0.35×probes + 0.20×temporal + 0.10×generalization + 0.15×statistics + 0.10×token + 0.10×record |
| **Data Integrity & Secure Export** | 10% | 0.15×format + 0.20×schema + 0.15×FHIR + 0.10×pseudonym + 0.15×channel + 0.15×quarantine + 0.10×report |
| **CPU Efficiency & Reliability** | 10% | 0.30×reliability + 0.30×wall-time + 0.20×memory + 0.20×determinism (+0.15×scaling) |

### Critical Penalties:
| Event | Points | Cap |
|-------|--------|-----|
| Unique direct ID / full name surviving | −1 each | −25 |
| Planted canary found | −3 each | −15 |
| Unsupported PII file copied as sanitized | −5 each | −20 |
| Exit 0 with missing report / silent drops | −10 | — |
| Input modification | −5 | — |

### Calibration Baselines (from scoring.toml):
| Submission | small normal | small chaos | standard normal | standard chaos |
|------------|--------------|-------------|-----------------|----------------|
| `reference` | **80.28** | **47.71** | **84.84** | **50.33** |
| `redact_all` | 22.75 | 22.64 | 21.70 | 21.68 |
| `naive_regex` | 3.77 | 2.49 | 4.56 | 3.95 |
| `passthrough` | −19.48 | −19.48 | −19.47 | −19.47 |

**Key Insight:** Reference scores ~80 on practice but ~50 on unseen-format (30-point memorization gap). Target is to close this gap.

---

## 8. Self-Check Tools

### `validate_output.py` (Contract Validator)
```bash
python3 validate_output.py --input dev/input --output my_output
# Must print: CONTRACT OK
```
**Checks:**
- `sanitized/` directory exists
- `report.json` valid JSON, correct schema
- `files` array with every input file (by SHA-256)
- `output` paths exist in `sanitized/`
- All sanitized files are UTF-8
- `records.jsonl` valid JSONL with `file`, `loc`, `patient`
- `file` paths in records.jsonl point to exported files

### `check_dev.py` (Practice Self-Check)
```bash
python3 check_dev.py --output my_output [--show N]
```
**Reports:**
1. Personal data leaked: count + % by type, script, hiding place
2. Canaries found in output folder (anywhere: content, filenames, report, logs)
3. Medical data kept: % of preserve probes survived
4. Patient linking: precision, recall, F0.5, false merges (different people merged)
5. Raw copies: unsupported files exported byte-for-byte

### `check_submission.py` (Pre-Submit)
```bash
python3 check_submission.py --repo ../your-repo --run
# Must print: READY TO SUBMIT
```
**Checks:**
- `raksha.toml` exists with correct keys
- README present
- Project Brief PDF exists
- Runs repo 3×: same secret (determinism), different secret (unlinkability), verifies output structure

---

## 9. Starter Kit Analysis (`starter/main.py`)

**What it does correctly (contract-critical):**
- Walks all files in fixed order (deterministic)
- Decodes UTF-8/UTF-8-BOM/UTF-16/cp1252 → writes UTF-8
- Keeps CSV as CSV (same delimiter, header), JSON as JSON
- Quarantines unparseable instead of copying
- Writes `report.json` with SHA-256 per file, honest counts, timing, memory
- Writes `records.jsonl` with correct locators (`row:N`, `/json/pointer`, `doc`)
- HMAC pseudonyms + per-patient date shift helpers
- Never prints/logs/stores PII or `RAKSHA_SECRET`

**What it does NOT do (the challenge):**
- Column-aware detection (expects renamed columns on hidden data)
- Name gazetteer in Latin + Devanagari + transliteration
- Honorifics (ji, sahab, didi, श्री), relatives (S/o, D/o, W/o, C/O)
- Meaning traps: "C/O fever" vs "C/O name", "Dr. Ramesh" preserved, "Dolo 650"/"5 mg"/"1-0-1" doses, "Parkinson's" not person
- JSON keys, CSV headers, filenames, base64 attachments can hold PII
- **Links nothing** (returns `None` from `link_records`)

**Baseline Score:** ~8 points (naive_regex level)

---

## 10. Toolkit Integration Requirements for LOCKMATE

### Must Match Exactly:
1. **`raksha.toml`** - Exact keys, `run` command format
2. **CLI** - `python main.py --input X --output Y` (no extra required flags)
3. **Output structure** - `sanitized/`, `report.json`, `records.jsonl`
4. **report.json** - `files` as **array**, `output` field, `status` enum, `counts` with all 9 fields
5. **records.jsonl** - Forward slashes, `sanitized/` prefix, `row:N`/`JSON pointer`/`doc` locators
6. **Environment** - Read `RAKSHA_SECRET` from env, never expose
7. **Determinism** - Same input + same secret = byte-identical `sanitized/` + `records.jsonl`
8. **Secret rotation** - Different secret = different pseudonyms + date shifts
9. **Quarantine** - Unsupported files → `sanitized/quarantined/` (or separate `quarantine/` per SPEC), never copied to `sanitized/` as-is
10. **No raw PII in side channels** - stdout, stderr, logs, report.json, records.jsonl, filenames, TMPDIR, HOME all scanned

### Must Pass:
- `validate_output.py` → `CONTRACT OK`
- `check_dev.py` → minimal leaks, high medical preservation, reasonable linking
- `check_submission.py` → `READY TO SUBMIT`

---

## 11. Verified vs Unverified Toolkit Claims

| Claim | Status | Evidence |
|-------|--------|----------|
| `validate_output.py` checks format only, not scoring | **VERIFIED** | Source code inspected |
| Practice dataset has 48 patients, 4 hospitals | **VERIFIED** | `dev/dataset_manifest.json`, `truth.json` |
| Hidden datasets use same generator with different seeds | **VERIFIED** | DATASET.md, FAIRNESS.md |
| Unseen-format round has new names/labels/formats | **VERIFIED** | DATASET.md §5 |
| Canaries planted in every dataset | **VERIFIED** | `check_dev.py` scans for them |
| Attacker uses voter-roll registry + known facts | **VERIFIED** | ATTACKS.md, `dev/attacker/` files |
| Global date shift recovery defeats per-release shift | **VERIFIED** | ATTACKS.md A5 |
| Pseudonym inversion catches unkeyed hashes | **VERIFIED** | ATTACKS.md A6 |
| Cross-release linkability tested with different secret | **VERIFIED** | SPEC.md §7, ATTACKS.md A7 |
| Scoring weights match problem statement | **VERIFIED** | scoring.toml, SCORING.md |
| Reference baseline scores ~80 on practice | **VERIFIED** | scoring.toml calibration table |
| Penalties are not floored at zero | **VERIFIED** | SCORING.md formula |

---

## 12. Summary

The toolkit is **comprehensive, well-documented, and executable**. All critical components are present and working:

- ✅ Practice dataset with ground truth
- ✅ Format validator (`validate_output.py`)
- ✅ Practice self-check (`check_dev.py`)
- ✅ Pre-submission check (`check_submission.py`)
- ✅ Reference starter kit
- ✅ Complete documentation (SPEC, SCORING, ATTACKS, DATASET, etc.)
- ✅ Scoring configuration (scoring.toml)

**LOCKMATE must integrate with this toolkit by:**
1. Fixing output format to match SPEC exactly (array `files`, `output` field, forward slashes)
2. Implementing detection for all trap types (language, meaning, fragmented, re-id, clinical, hidden, robustness)
3. Building identity resolution that survives cross-script matching
4. Implementing per-patient HMAC date shifts (not global)
5. Ensuring pseudonyms are HMAC-keyed (not plain hashes)
6. Passing `validate_output.py` → `CONTRACT OK` on practice data first
7. Then optimizing against `check_dev.py` metrics