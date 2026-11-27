# LOCKMATE Testing Plan

**Date:** 2026-11-26  
**Auditor:** Claude Engineering Agent  
**Based On:** Repository Audit, Toolkit Audit, Gap Analysis  
**Status:** Phase 1 Complete

---

## 1. Testing Strategy Overview

### Test Pyramid

```
                    ┌─────────────────┐
                    │  E2E / Contract │  ← validate_output.py, check_dev.py
                    │   (Few, Slow)   │
               ┌────┴────────┬────────┴────┐
               │  Integration Tests       │  ← Multi-format, multi-hospital, linkage
               │  (Medium, Med Speed)     │
        ┌──────┴─────┐   ┌──────┴─────┐   ┌──────┴─────┐
        │  Unit Tests         │  Red-Team Tests    │  Property Tests  │
        │  (Many, Fast)       │  (Adversarial)     │  (Determinism)   │
        └─────────────────────┴────────────────────┴──────────────────┘
```

### Test Categories

| Category | Purpose | Tools | Frequency |
|----------|---------|-------|-----------|
| **Unit** | Module correctness | pytest | Every commit |
| **Integration** | Pipeline stages | pytest + fixtures | Every PR |
| **Contract** | Organizer format compliance | `validate_output.py` | Every build |
| **Practice** | Leak/medical/linking metrics | `check_dev.py` | Daily |
| **Red-Team** | Adversarial robustness | Custom fixtures | Pre-submit |
| **Property** | Determinism, secret rotation | Custom scripts | Pre-submit |
| **Performance** | Time/memory limits | Profiling | Weekly |

---

## 2. Unit Test Coverage (Current + Required)

### Currently Covered (81 tests, 73 pass)

| Module | Tests | Status |
|--------|-------|--------|
| Contracts | 42 | ✅ All pass |
| File Validator | 10 | ✅ All pass |
| Path Guard | 8 | ✅ 7 pass, 1 skip |
| Quarantine | 7 | ✅ All pass |
| Size Limits | 6 | ✅ All pass |
| Symlink Guard | 8 | ✅ 1 pass, 7 skip (Windows) |

### Required Unit Tests (By Module)

#### Intake
| Module | Test Cases | Priority |
|--------|------------|----------|
| `discovery.py` | Symlink traversal, path traversal, oversize files, 1000 files, empty dir, permission denied | P0 |
| `classifier.py` | All extensions, content sniffing JSON/CSV/FHIR/XML, ambiguous files | P0 |
| `encoding.py` | UTF-8, UTF-8-BOM, UTF-16-LE/BE, cp1252, binary rejection, invalid UTF-8 | P0 |
| `hashing.py` | Known files, empty, 100MB streaming, incremental | P0 |
| `quarantine.py` | All reason codes, copy verification, metadata persistence | P0 |

#### Parsers
| Module | Test Cases | Priority |
|--------|------------|----------|
| `csv_parser.py` | Comma/tab/semicolon/pipe, no header, quoted commas, shifted columns, 10K rows, ragged rows, cp1252 | P0 |
| `json_parser.py` | Nested objects, arrays, 50MB streaming, malformed, deep nesting (50), FHIR Bundle | P0 |
| `text_parser.py` | Multiline, empty, Unicode, encoding variants | P0 |
| `fhir_parser.py` | Bundle, Patient, Observation, references, extensions, contained, attachments, invalid resource | P0 |

#### Detection
| Module | Test Cases | Priority |
|--------|------------|----------|
| `placeholder.py` | Each pattern (email, phone, PAN, Aadhaar, ABHA, PIN, dates, names), precision/recall on fixtures | P0 |
| `identifiers.py` | Valid/invalid Aadhaar (Verhoeff), ABHA, PAN, phone formats, embedded in text, UHID context | P0 |
| `names.py` | English/Hindi/Hinglish names, honorifics, relatives, doctors, transliteration variants, medical veto | P1 |
| `normalize.py` | NFC, Devanagari digits, ZWJ/ZWNJ removal, bidi removal, confusable normalization, offset map round-trip | P0 |
| `gazetteer.py` | Load time <1s, coverage spot-check, fallback creation, frozenset immutability | P0 |
| `transliterate.py` | मोहम्मद → mohammad, mixed script, Double Metaphone, name variants | P1 |
| `structured.py` | CSV headers, JSON keys (nested), FHIR paths, filenames, metadata | P1 |
| `merger.py` | Overlap veto, adjacency, confidence filter, span merging | P0 |
| `calibration.py` | Threshold sweep, P/R curves, optimal F2 | P1 |
| `residual.py` | Planted stragglers detected, patient's known IDs searched | P1 |

#### Clinical
| Module | Test Cases | Priority |
|--------|------------|----------|
| `drugs.py` | `Dolo 650 BD`, `5 mg`, `TDS`, `10 days`, brand/INN coverage | P0 |
| `labs.py` | `HbA1c 7.2%`, `BP 130/85`, `mg/dL`, LOINC coverage | P0 |
| `diagnoses.py` | `Diabetes`, `Parkinson's disease`, `Appendectomy`, ICD-10, eponyms | P0 |
| `doctors.py` | `Dr. Rahul prescribed` vs `Rahul is patient`, Devanagari doctor | P0 |
| `veto.py` | `Rahul 5 mg` → Rahul redacted/5mg kept, `Parkinson's` kept, adjacency | P0 |

#### Transform
| Module | Test Cases | Priority |
|--------|------------|----------|
| `replacer.py` | Replacement at boundaries, multi-byte chars, offset map round-trip, reverse-order application | P0 |
| `structured.py` | CSV cell, JSON leaf, FHIR Patient.name, nested dict/array, reference preservation | P0 |

#### Output
| Module | Test Cases | Priority |
|--------|------------|----------|
| `serializer.py` | Round-trip parse→sanitize→parse, pseudonym injection, delimiter preservation, UTF-8 | P0 |
| `namer.py` | PII in filename, Unicode, long names, collision handling, directory structure | P0 |
| `writer.py` | Atomic temp→rename, cross-device fallback, power-cut simulation (kill -9), cleanup on error | P0 |
| `security_gate.py` | Planted PII in sanitized → detected, canary check, clinical integrity, schema validity, pseudonym consistency | P0 |
| `pipeline.py` | Full output generation, report.json format, records.jsonl format, quarantine integration | P0 |

#### Crypto (New)
| Module | Test Cases | Priority |
|--------|------------|----------|
| `secret.py` | Missing env → clear error, set env → loads, length validation, base64/hex decode | P1 |
| `pseudonym.py` | Determinism, secret rotation → different, collision test (1M), format `PSN-XXXXXXXX` | P1 |
| `date_shift.py` | Same patient+secret → same offset, different secret → different, interval preservation | P1 |
| `injector.py` | FHIR Patient.identifier, CSV patient_id, JSON patient.pseudonym, null cluster → no pseudonym | P1 |

#### Linkage (New)
| Module | Test Cases | Priority |
|--------|------------|----------|
| `blocking.py` | Each key type, collision rate on synthetic data | P1 |
| `candidates.py` | 1000 records → <50K pairs (blocking effective) | P1 |
| `scoring.py` | Each feature, known match/non-match pairs | P1 |
| `constraints.py` | Conflicting IDs → cannot_link | P1 |
| `clustering.py` | Chain A-B, B-C, A-C low → no merge; singleton → null | P1 |
| `canonical.py` | Deterministic sort, weak cluster → random UUID + HMAC | P1 |

#### Privacy (New)
| Module | Test Cases | Priority |
|--------|------------|----------|
| `date_fields.py` | FHIR date elements, CSV date columns, JSON date strings | P1 |
| `date_shift.py` | Interval preservation, chronological order, timezone, leap years | P1 |
| `age_bands.py` | Boundaries (4,5,9,10...89,90), unknown, invalid, 90+ | P1 |
| `location.py` | Village→district, city→district, PIN→3-digit, rare threshold, missing | P1 |
| `equivalence.py` | Class sizes match manual calc | P1 |
| `suppression.py` | k=5, convergence, max suppression | P1 |

---

## 3. Integration Test Scenarios

| Scenario | Description | Input | Expected |
|----------|-------------|-------|----------|
| **Mixed Format** | CSV + JSON + Text + FHIR in one dir | `dev/input/` subset | All parsed, correct URM |
| **Multi-Hospital** | Same patient across 4 hospital systems | Practice data | Linked with stable pseudonym |
| **Cross-Script** | Patient in Latin + Devanagari + Hinglish | Synthetic fixture | Same pseudonym |
| **Quarantine Propagation** | Unsupported PDF + corrupt JSON + valid CSV | Mixed dir | 2 quarantined, 1 sanitized, report correct |
| **Atomic Write** | Kill during write | Large file | No partial files, no corruption |
| **FHIR Round-Trip** | Bundle → sanitize → validate | FHIR fixture | Valid R4, references resolve |
| **Large File Streaming** | 100MB CSV/JSON | Generated | <500MB RAM, no crash |
| **Deep Nesting** | 50-level JSON | Generated | Quarantined (limit 50) |

---

## 4. Contract Compliance Tests (validate_output.py)

**Must Pass Every Build:**
```bash
python3 validate_output.py --input dev/input --output my_output
# → CONTRACT OK
```

**Checklist:**
- [ ] `sanitized/` directory exists
- [ ] `report.json` valid JSON, has `schema`, `files[]`, `counts{}`, `timing{}`, `resources{}`
- [ ] `files` is **array** with every input file (by SHA-256)
- [ ] Each entry has `input_sha256`, `output`, `status` ∈ {sanitized, quarantined, suppressed}
- [ ] Sanitized entries have `output` path that exists in `sanitized/`
- [ ] All sanitized files are UTF-8
- [ ] `records.jsonl` valid JSONL, each line has `file`, `loc`, `patient`
- [ ] `file` paths in records.jsonl use forward slashes, include `sanitized/` prefix
- [ ] `loc` format: `row:N` / JSON pointer / `doc`
- [ ] `patient` is pseudonym or `null`

---

## 5. Practice Self-Check Tests (check_dev.py)

**Run Daily:**
```bash
python3 check_dev.py --output my_output --show 20
```

**Target Metrics (Practice Data):**

| Metric | Minimum Target | Stretch Target |
|--------|----------------|----------------|
| PII Leak Rate | < 10% | < 5% |
| Canary Leaks | 0 | 0 |
| Medical Preservation | > 90% | > 95% |
| Linkage Precision | > 0.90 | > 0.98 |
| Linkage Recall | > 0.70 | > 0.85 |
| Linkage F0.5 | > 0.80 | > 0.90 |
| False Merges | < 5 | 0 |
| Raw Copies | 0 | 0 |

**Leak Breakdown Targets:**
- By type: AADHAAR/PAN/PHONE/EMAIL < 5% each; NAME < 15%
- By script: latin < 10%, deva < 15%, hinglish < 20%
- By channel: content < 10%, filename < 5%, header/key < 5%, metadata < 5%

---

## 6. Red-Team / Adversarial Tests

### 6.1 Canary Leakage Test
```bash
# Inject unique canaries in input
# Run pipeline
# Scan output, logs, temp, report, records.jsonl for canaries
# Assert: ZERO matches
```
**Canary Format:** `LOCKMATE_CANARY_<UUID>` planted in:
- Patient names (Latin, Devanagari, Hinglish)
- Phone numbers
- Aadhaar/ABHA
- JSON keys
- Filenames
- FHIR extensions
- Base64 attachments

### 6.2 False Merge Test Suite
```python
# Pairs that must NEVER share pseudonym:
test_cases = [
    # Same name, different DOB
    ("Rahul Sharma", "1977-04-12"), ("Rahul Sharma", "1985-06-20"),
    # Same name, different gender
    ("Priya Patel", "F"), ("Priya Patel", "M"),
    # Same name, different Aadhaar
    ("Amit Kumar", "123456789012"), ("Amit Kumar", "234567890123"),
    # Transliteration variants, different people
    ("Mohammad Arif", ...), ("Mohd. Arif", ...), ("मोहम्मद आरफ", ...),
    # Conflicting IDs
    ("Same Name", aadhaar="111...", phone="987..."), ("Same Name", aadhaar="222...", phone="987..."),
    # Shared relative name
    ("Patient A", relative="Rahul"), ("Patient B", relative="Rahul"),
    # Transitive false-merge chain
    A~B (name), B~C (phone), A≠C (DOB conflict) → A,B,C separate
]
```

### 6.3 Medical Corruption Test
```python
# Verify NO clinical values corrupted:
clinical_types = [
    "DRUG", "DOSAGE", "FREQUENCY", "DURATION",
    "DIAGNOSIS", "PROCEDURE", "LAB", "VITAL", "UNIT"
]
# Adversarial cases:
# "Patient Parkinson admitted" → Parkinson kept, Patient redacted
# "Dr. Ramesh prescribed Dolo 650" → Dr. Ramesh kept, Dolo 650 kept
# "C/O fever" → C/O not treated as relative
# "S/o Rahul" → Rahul redacted as relative
# "Dolo 650 BD x 5 days" → all preserved
```

### 6.4 Privacy Attack Evaluation
```bash
# Generate synthetic voter roll matching release schema
# Run attacker simulation (A2/A3/A4/A5)
# Measure: unique re-identification rate
# Target: < 5% unique matches after transformations
```

### 6.5 Resource Limit Tests
| Limit | Test | Expected |
|-------|------|----------|
| File size 100MB | 101MB file | Quarantined `resource_limit_exceeded` |
| Nesting depth 50 | 51-level JSON | Quarantined |
| Decompression 100:1 | Zip bomb | Quarantined `decompression_bomb` |
| Total input 2GB | 2.1GB input | Stop with error |
| Wall time 15min | Large dataset | Complete < 900s |
| Peak memory 4GB | Stress test | < 4GB RSS |

### 6.6 Security Hardening Tests
| Check | Tool | Pass Criteria |
|-------|------|---------------|
| No raw PII in logs | Manual + grep | Structured JSON only, scrubbed |
| No secret in memory dumps | Manual | `RAKSHA_SECRET` not in heap |
| Temp files encrypted | Manual | AES-GCM, fresh nonce |
| No `eval`/`exec` | bandit | Zero high-severity |
| No shell injection | semgrep | Zero findings |
| Path traversal blocked | Custom | `PathTraversalError` raised |

---

## 7. Property-Based Tests (Determinism)

### 7.1 Same Secret Determinism
```bash
# Run 3 times with same RAKSHA_SECRET
RAKSHA_SECRET="..." python main.py --input X --output out1
RAKSHA_SECRET="..." python main.py --input X --output out2
RAKSHA_SECRET="..." python main.py --input X --output out3

# Compare:
diff -r out1/sanitized out2/sanitized      # Must be identical
diff out1/records.jsonl out2/records.jsonl # Must be identical
diff out1/report.json out2/report.json     # Totals identical (timing/memory may differ)
```

### 7.2 Different Secret Unlinkability
```bash
# Run with two different secrets
RAKSHA_SECRET="secret1" python main.py --input X --output out1
RAKSHA_SECRET="secret2" python main.py --input X --output out2

# Verify:
# - Pseudonyms differ for same patient
# - Date shifts differ
# - Clinical content IDENTICAL
# - Structure identical
```

### 7.3 Clinical Content Preservation
```python
# For each clinical probe in truth.json:
# - Extract from input
# - Extract from sanitized output
# - Assert: normalized match (allowing date shifts, age bands, location generalization)
# - Assert: intervals preserved exactly
```

---

## 8. Performance Benchmarks

| Dataset Profile | Time Limit | Memory Limit | Target |
|-----------------|------------|--------------|--------|
| `tiny` | 10s good / 120s limit | 512MB good / 4GB limit | < 10s, < 512MB |
| `small` | 15s good / 300s limit | 512MB good / 4GB limit | < 15s, < 512MB |
| `standard` | 60s good / 900s limit | 512MB good / 4GB limit | < 60s, < 512MB |
| `large` | 180s good / 1800s limit | 768MB good / 4GB limit | < 180s, < 768MB |

**Profiling Command:**
```bash
python -m cProfile -o profile.stats main.py --input large_input --output out
python -m memory_profiler main.py --input large_input --output out
```

**Per-Stage Budget (from context.md §19.2):**
| Stage | Time Budget | Memory Budget |
|-------|-------------|---------------|
| Intake + Parsing | 60s | 500 MB |
| Normalization | 30s | 200 MB |
| PII Detection | 180s | 1 GB |
| Medical Protection | 30s | 200 MB |
| Identity Resolution | 120s | 1 GB |
| Pseudonymization | 10s | 100 MB |
| Privacy Transforms | 60s | 500 MB |
| Serialization | 60s | 500 MB |
| Security Gate | 60s | 300 MB |
| Reporting | 10s | 100 MB |
| **Total** | **~620s (10.3 min)** | **Peak ~1.5 GB** |

---

## 9. Test Fixtures Required

| Fixture | Description | Location |
|---------|-------------|----------|
| `fixtures/csv/` | CSV with all delimiter types, ragged rows, shifted columns, headers with PII | `tests/fixtures/csv/` |
| `fixtures/json/` | Nested JSON, arrays, FHIR Bundles, malformed, deep nesting | `tests/fixtures/json/` |
| `fixtures/text/` | English, Hindi, Hinglish notes with PII + clinical | `tests/fixtures/text/` |
| `fixtures/fhir/` | Valid R4 Bundles, references, extensions, contained, attachments | `tests/fixtures/fhir/` |
| `fixtures/multilingual/` | Same patient in Latin/Devanagari/Hinglish with known linkage | `tests/fixtures/multilingual/` |
| `fixtures/adversarial/` | Canaries, false merge pairs, medical corruption cases | `tests/fixtures/adversarial/` |
| `fixtures/large/` | 100MB CSV, 50MB JSON, 1000 files | `tests/fixtures/large/` (generated) |

**Fixture Generator:** `tests/fixtures/generator.py` (to be created)

---

## 10. CI/CD Pipeline

```yaml
# .github/workflows/test.yml (to be created)
stages:
  - unit_tests:        pytest tests/unit/ -x
  - contract_check:    validate_output.py on practice data
  - practice_check:    check_dev.py --output --show 0
  - determinism:       3 runs same secret → byte-identical
  - secret_rotation:   2 runs different secrets → different pseudonyms
  - red_team:          pytest tests/redteam/ -x
  - performance:       Run on standard profile, assert < 60s, < 512MB
  - security:          bandit + semgrep on src/
```

---

## 11. Test Execution Commands

### Quick Smoke Test (30 sec)
```bash
RAKSHA_SECRET="..." python main.py --input test_input --output test_out
python3 validate_output.py --input test_input --output test_out
```

### Full Practice Validation (2 min)
```bash
RAKSHA_SECRET="practice" python main.py --input dev/input --output practice_out
python3 validate_output.py --input dev/input --output practice_out
python3 check_dev.py --output practice_out --show 10
```

### Determinism Check (3 min)
```bash
for i in 1 2 3; do
  RAKSHA_SECRET="test" python main.py --input dev/input --output det_out_$i
done
diff -r det_out_1/sanitized det_out_2/sanitized
diff det_out_1/records.jsonl det_out_2/records.jsonl
```

### Secret Rotation Check (2 min)
```bash
RAKSHA_SECRET="secret1" python main.py --input dev/input --output rot_out_1
RAKSHA_SECRET="secret2" python main.py --input dev/input --output rot_out_2
# Compare pseudonyms differ, clinical content same
```

### Red-Team Suite (5 min)
```bash
pytest tests/redteam/ -v
```

### Performance Benchmark (10 min)
```bash
# Requires large fixture generation
python tests/redteam/performance.py
```

---

## 12. Test Metrics Dashboard

| Metric | Current | Target | Trend |
|--------|---------|--------|-------|
| Unit Tests Passing | 73/81 | 100% | ↗️ |
| Integration Tests | 0 | >20 | — |
| Contract Compliance | ❌ FAIL | ✅ PASS | — |
| Practice Leak Rate | Unknown | <10% | — |
| Medical Preservation | Unknown | >90% | — |
| Linkage F0.5 | 0.00 | >0.80 | — |
| False Merges | N/A | 0 | — |
| Canary Leaks | N/A | 0 | — |
| Determinism | Unknown | 100% | — |
| Secret Rotation | Unknown | 100% | — |
| Peak Memory (standard) | Unknown | <512MB | — |
| Wall Time (standard) | Unknown | <60s | — |

---

## 13. Acceptance Criteria for Each Phase

### Phase 0 (Foundation) - DONE
- [x] All contracts defined and tested
- [x] Intake pipeline working
- [x] Basic parsers working
- [x] 73 unit tests pass

### Phase 3 (Basic Sanitization) - IN PROGRESS
- [ ] `validate_output.py` → `CONTRACT OK` on practice data
- [ ] `check_dev.py` → leak rate < 50%, medical > 50%
- [ ] All P0 format fixes applied

### Phase 4 (Detection) - PENDING
- [ ] Names detection working (English/Hindi/Hinglish)
- [ ] Structured field scanning (headers, keys, filenames)
- [ ] Practice leak rate < 20%
- [ ] Medical preservation > 80%

### Phase 5 (Clinical) - PENDING
- [ ] Medical preservation > 95%
- [ ] Zero clinical corruption on adversarial fixtures

### Phase 6 (Output Security) - PENDING
- [ ] Security gate catches all residual PII
- [ ] Canary test passes

### Phase 7-8 (Linkage + Pseudonyms) - PENDING
- [ ] Linkage F0.5 > 0.80 on practice
- [ ] False merges < 1%
- [ ] Pseudonyms deterministic + secret rotation works

### Phase 9-10 (Privacy) - PENDING
- [ ] Date shifts preserve intervals
- [ ] Age bands truthful
- [ ] Location generalization correct
- [ ] k-anonymity ≥5 for >95% records
- [ ] Attacker simulation < 5% unique re-ID

### Phase 11 (FHIR) - PENDING
- [ ] Complex FHIR Bundles → valid R4
- [ ] No PII in references/extensions/attachments

### Phase 12 (Red-Team) - PENDING
- [ ] All adversarial tests pass
- [ ] Performance within limits
- [ ] Determinism verified
- [ ] Security review clean

---

## 14. Test Maintenance

- **Fixture versioning:** Store fixture SHA-256 in `tests/fixtures/MANIFEST.json`
- **Test data refresh:** Regenerate synthetic fixtures monthly with fixed seed
- **Flaky test quarantine:** Mark with `@pytest.mark.flaky`, fix within 1 week
- **Coverage target:** >80% line coverage on `src/secret_wards/`
- **Mutation testing:** Run `mutmut` monthly on critical modules (detection, linkage, crypto)