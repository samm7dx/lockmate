# LOCKMATE — Testing Strategy

**Version:** 1.0  
**Date:** 2026-11-26  
**Status:** Authoritative testing specification

---

## 1. Testing Philosophy

- **Contract-first:** Every test validates a requirement from the organizer specification
- **Synthetic only:** No real patient data ever used in tests
- **Adversarial by default:** Tests designed to find failures, not confirm success
- **Evidence-based:** Every test produces verifiable output (logs, metrics, assertions)
- **Continuous:** Tests run on every build; CI/CD enforced

---

## 2. Test Pyramid

```
                    ┌─────────────┐
                    │   E2E /     │  ← 5-10 tests
                    │ Integration │     Full pipeline, multi-hospital
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Adversar-│ │  Contract│ │Perform-  │  ← 15-20 tests
        │   ial    │ │Validation│ │  ance    │     Canary, false-merge,
        └────┬─────┘ └────┬─────┘ └────┬─────┘     medical corruption,
             │            │            │           privacy attack, determinism,
             ▼            ▼            ▼           secret rotation, resources
        ┌─────────────────────────────────────┐
        │         Unit Tests (200+)           │  ← Per-module, fast, isolated
        │  Intake | Parsers | Detection | ... │     Mock-free where possible
        └─────────────────────────────────────┘
```

---

## 3. Unit Tests (Per Module)

### 3.1 Intake Module (`tests/unit/intake/`)

| Test File | Focus | Key Assertions |
|-----------|-------|----------------|
| `test_discovery.py` | File walker | Symlinks resolved; path traversal blocked; size/nesting limits; 1000 files |
| `test_hashing.py` | SHA-256 | Streaming hash matches `sha256sum`; empty file; 100MB file |
| `test_classifier.py` | Format classification | CSV/TSV/JSON/Text/FHIR/binary/PDF correctly classified |
| `test_encoding.py` | Encoding detection | UTF-8/BOM, UTF-16LE/BE, CP1252 detected; binary → quarantine |
| `test_quarantine.py` | Quarantine classifier | All reason codes from context.md §17.1 work |

### 3.2 Parsers (`tests/unit/parsers/`)

| Test File | Focus | Key Assertions |
|-----------|-------|----------------|
| `test_csv_parser.py` | CSV/TSV parsing | Comma/tab/semicolon; no header; quoted commas; 10k rows; shifted columns |
| `test_json_parser.py` | JSON parsing | Nested objects, arrays, 50MB stream, malformed → quarantine |
| `test_text_parser.py` | Text parsing | Multiline, empty, Unicode, offset map correctness |
| `test_fhir_parser.py` | FHIR R4 parsing | Bundle, Patient, Observation; invalid resource → quarantine |

### 3.3 Detection (`tests/unit/detection/`)

| Test File | Focus | Key Assertions |
|-----------|-------|----------------|
| `test_normalize.py` | Unicode normalization | NFC, Devanagari digits, ZWJ/ZWNJ, bidi, offset map round-trip |
| `test_structured.py` | Structured scanner | CSV header, JSON nested key, FHIR Patient.telecom, filename |
| `test_identifiers.py` | Direct identifiers | Each ID type: valid/invalid formats; checksum validation; context required |
| `test_names.py` | Name detection | English/Hindi/Hinglish; doctor vs patient vs relative; triggers |
| `test_gazetteer.py` | Gazetteer loading | Load time <1s; coverage spot-check; frozen sets |
| `test_transliterate.py` | Transliteration | मोहम्मद → mohammad → MMT; round-trip consistency |
| `test_crf_tagger.py` | CRF (conditional) | Model loads; inference <10ms/record; comparison vs rule baseline |
| `test_residual.py` | Residual scanner | Planted stragglers detected |
| `test_merger.py` | Span merger + veto | Overlap, adjacency, containment; medical veto wins |
| `test_engine.py` | Detection integration | Full detection on 100-record fixture; P/R/F1 measured |

### 3.4 Clinical (`tests/unit/clinical/`)

| Test File | Focus | Key Assertions |
|-----------|-------|----------------|
| `test_drugs.py` | Drug/dosage/frequency | `Dolo 650 BD`, `5 mg`, `TDS`, `10 days` detected |
| `test_labs.py` | Lab/vital/unit | `HbA1c 7.2%`, `BP 130/85`, `mg/dL` detected |
| `test_diagnoses.py` | Diagnosis/procedure | `Diabetes`, `Parkinson's disease`, `Appendectomy` detected |
| `test_doctors.py` | Doctor context | `Dr. Rahul prescribed` preserved vs `Rahul is patient` redacted |
| `test_veto.py` | Medical veto | `Rahul 5 mg` → Rahul redacted, `5 mg` kept; `Parkinson's` kept |

### 3.5 Linkage (`tests/unit/linkage/`)

| Test File | Focus | Key Assertions |
|-----------|-------|----------------|
| `test_blocking.py` | Blocking keys | Each key type; collision rate on synthetic data |
| `test_candidates.py` | Candidate pairs | 1000 records → <50k pairs; deduped |
| `test_scoring.py` | Pairwise scoring | Each feature; known match/non-match pairs |
| `test_constraints.py` | Cannot-link | Conflicting IDs → cannot_link=True |
| `test_clustering.py` | Conservative clustering | Chain A-B, B-C, A-C low → no merge; singleton → null |
| `test_canonical.py` | Canonical identity | Deterministic sort; weak cluster → random UUID + HMAC |

### 3.6 Crypto (`tests/unit/crypto/`)

| Test File | Focus | Key Assertions |
|-----------|-------|----------------|
| `test_secret.py` | Secret loader | Missing env → clear error; set env → loads; validates length |
| `test_pseudonym.py` | HMAC pseudonym | Determinism; secret rotation → different; collision test (1M) |
| `test_date_shift.py` | Date shift derivation | Same patient+secret → same offset; different secret → different |

### 3.7 Privacy (`tests/unit/privacy/`)

| Test File | Focus | Key Assertions |
|-----------|-------|----------------|
| `test_gazetteer.py` | Location gazetteer | Lookup accuracy; missing → next level |
| `test_location.py` | Location generalization | Each level; rare threshold; missing data |
| `test_equivalence.py` | Equivalence classes | Class sizes match manual calculation |
| `test_suppression.py` | Rare suppression | k=5; convergence; max suppression |
| `test_date_shift.py` | Date shifting | Interval preservation; chronological order; timezone |
| `test_age_bands.py` | Age bands | Boundaries (4,5,9,10...89,90); unknown; invalid |

### 3.8 Output (`tests/unit/output/`)

| Test File | Focus | Key Assertions |
|-----------|-------|----------------|
| `test_serializer.py` | Serialization | Round-trip parse → sanitize → parse; format preserved |
| `test_namer.py` | Filename sanitizer | PII in filename → SHA-256 prefix; Unicode; long names |
| `test_writer.py` | Atomic writer | Power-cut simulation (kill -9); no partial files |
| `test_security_gate.py` | Security gate | Passes clean; fails each injected violation type |
| `test_report.py` | report.json generator | Schema validation; totals match actual counts |
| `test_records.py` | records.jsonl generator | Location formats; pseudonym consistency |

---

## 4. Integration Tests (`tests/integration/`)

| Test File | Scenario | Key Assertions |
|-----------|----------|----------------|
| `test_basic_pipeline.py` | CSV/JSON/Text → sanitized + reports | Structural CONTRACT OK; no raw PII |
| `test_full_pipeline.py` | All formats + linkage + privacy | End-to-end on 500-record fixture |
| `test_multi_hospital.py` | 4 hospitals, different schemas | Cross-hospital linkage; same patient = same pseudonym |
| `test_fhir_integration.py` | Complex FHIR Bundle | Valid sanitized R4; refs/extensions/attachments clean |
| `test_quarantine_propagation.py` | Quarantine flow | Quarantined files in report.json with reason |
| `test_atomic_write.py` | Atomic output | Kill during write → no partial output |

---

## 5. Adversarial / Red-Team Tests (`tests/adversarial/`)

| Test File | Attack Vector | Success Criteria |
|-----------|---------------|------------------|
| `test_canary_leakage.py` | Canary injection | `LOCKMATE_CANARY_<UUID>` in input → **zero** in output/logs/temp |
| `test_false_merge.py` | False merge | Same name, different DOB/Aadhaar/gender → separate pseudonyms (<1%) |
| `test_medical_corruption.py` | Medical corruption | Clinical values adjacent to names → **0% corruption** |
| `test_privacy_attack.py` | Re-identification | Synthetic voter roll → **<5% unique re-ID** after transforms |
| `test_performance.py` | Resource limits | 2GB input → **<900s, <4GB RSS, 2 CPUs** |
| `test_determinism.py` | Determinism | 3 runs same secret → **byte-identical** sanitized/ + records.jsonl |
| `test_secret_rotation.py` | Secret rotation | 2 runs different secrets → different pseudonyms/shifts; clinical same |
| `test_resource_limits.py` | Resource exhaustion | 101MB file → quarantine; 51 nesting → quarantine; 101:1 zip → quarantine |

---

## 6. Test Fixtures

### 6.1 Fixture Principles
- **Synthetic only** — generated programmatically, no real data
- **Four hospital systems** — different schemas, formats, conventions:
  - Hospital A: CSV with Indian names (Latin), Aadhaar, phone
  - Hospital B: JSON with Devanagari names, ABHA, UHID
  - Hospital C: FHIR R4 with Hinglish names, PAN, mixed scripts
  - Hospital D: Text notes with transliterated names, relative identifiers
- **Known ground truth** — every record labeled with:
  - True patient identity (for linkage evaluation)
  - All PII spans with types
  - All clinical spans with types
  - Expected pseudonym (for deterministic verification)
- **Adversarial cases** — deliberately ambiguous:
  - Same name, different DOB/Aadhaar → must NOT link
  - `C/O fever` vs `C/O Rahul` → clinical vs relative
  - `Parkinson's disease` vs patient named `Parkinson`
  - Shifted CSV columns, nested JSON, FHIR extensions

### 6.2 Fixture Generator (`tests/fixtures/generator.py`)

```python
# Generates deterministic fixtures with fixed seed
# Output: tests/fixtures/hospital_a/, hospital_b/, hospital_c/, hospital_d/
# Plus adversarial/ subdirectory
```

---

## 7. Contract Validation Tests

### 7.1 Self-Validator (Internal)

Since official `validate_output.py` may not be available, implement internal validator matching organizer spec:

```python
# tests/validators/contract_validator.py
# Validates:
# - Output directory structure
# - report.json schema + totals accuracy
# - records.jsonl schema + pseudonym consistency
# - Sanitized file format validity
# - No PII in output (scan with detection engine)
# - Filename/metadata safety
# - Quarantine handling
```

### 7.2 Official Validator (When Available)

```bash
# Run on every build
python3 validate_output.py --input dev/input --output test_output/
# Must output: CONTRACT OK
```

---

## 8. Performance Benchmarks

| Benchmark | Target | Measurement |
|-----------|--------|-------------|
| Full pipeline (2GB, 1000 files) | < 900s | Wall-clock |
| Peak RSS | < 4 GB | `psutil.Process().memory_info().rss` |
| CPU utilization | ≤ 2 cores | `psutil.cpu_percent(interval=1)` |
| Intake (1000 files) | < 60s | Stage timing |
| Detection (100k records) | < 180s | Stage timing |
| Linkage (10k records) | < 120s | Stage timing |
| Serialization (100k records) | < 60s | Stage timing |

---

## 9. Test Execution

### 9.1 Commands

```bash
# Unit tests (fast, < 30s)
pytest tests/unit/ -v --tb=short

# Integration tests (medium, < 2min)
pytest tests/integration/ -v --tb=short

# Adversarial tests (slow, < 10min)
pytest tests/adversarial/ -v --tb=short

# All tests
pytest tests/ -v --tb=short

# Specific module
pytest tests/unit/detection/ -v

# With coverage
pytest tests/ --cov=src/secret_wards --cov-report=term-missing
```

### 9.2 CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/test.yml
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - run: pytest tests/unit/ -v
      - run: pytest tests/integration/ -v
      - run: pytest tests/adversarial/ -v
      - run: python main.py --input test_fixtures/ --output test_out/
      - run: python tests/validators/contract_validator.py test_output/
```

---

## 10. Test Metrics & Reporting

### 10.1 Required Metrics Per Test Run

| Metric | Target |
|--------|--------|
| Unit test pass rate | 100% |
| Integration test pass rate | 100% |
| Adversarial test pass rate | 100% |
| Code coverage (unit) | ≥ 90% |
| Code coverage (integration) | ≥ 70% |
| Contract validation | PASS |
| Performance benchmarks | Within limits |

### 10.2 Test Report Artifacts

| Artifact | Location | Purpose |
|----------|----------|---------|
| JUnit XML | `test-results/junit.xml` | CI parsing |
| Coverage HTML | `test-results/coverage/` | Coverage analysis |
| Adversarial metrics | `test-results/adversarial_metrics.json` | Privacy/utility tracking |
| Performance profile | `test-results/profile.prof` | Bottleneck analysis |

---

## 11. Test Data Management

- **Fixtures committed to repo** — small synthetic datasets (< 10 MB total)
- **Large fixtures generated** — `tests/fixtures/generator.py` creates on-demand
- **No real data** — ever
- **Deterministic generation** — fixed seed for reproducibility

---

## 12. Regression Prevention

| Mechanism | Implementation |
|-----------|----------------|
| Pre-commit hooks | `pytest tests/unit/ -x` on commit |
| CI gate | All tests must pass on PR |
| Adversarial tests | Run on every build; fail build on any regression |
| Determinism check | 3-run comparison on every build |
| Secret rotation check | 2-run comparison on every build |

---

## 13. Test Documentation

Each test file must include:
```python
"""
Test: <component>.<functionality>
Requirement: <organizer spec section or context.md section>
Fixture: <fixture name or generator function>
Assertions: <what is verified>
"""
```

---

**END OF TESTING STRATEGY**