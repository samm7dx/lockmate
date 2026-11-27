# Phase 6-8 Integration Readiness Assessment

## Overview

This document assesses the integration readiness of Phases 6, 7, and 8 with the main LOCKMATE pipeline and Phase 5 (Identity Linkage).

**Branch**: `feature/phases-6-8-foundation`  
**Target**: Merge into `main` after Phase 5 integration  
**Status**: Foundation complete, integration adapters required

---

## Integration Interfaces

### Phase 6: Privacy Layer → Phase 5 Identity

#### Required from Phase 5
| Interface | Type | Description |
|-----------|------|-------------|
| `PatientCluster.pseudonym` | `str` | PSN-XXXXXXXX format, stable across hospitals/files |
| `PatientCluster.is_confident` | `bool` | False → pseudonym = None (no privacy transforms) |
| `PatientCluster.canonical_identity` | `str` | Internal identifier for cross-hospital linkage |

#### Phase 6 Input Contract
```python
# Called for each record after Phase 5 clustering
pseudo = cluster.pseudonym  # "PSN-abc12345" or None
if pseudo:
    shift = date_shifter.get_shift(pseudo)
    age_band = age_gen.generalize_dob(rec.dob)
    gen_addr = loc_gen.generalize(rec.address)
    # ... apply transforms
```

#### Integration Point in `pipeline/full.py`
```python
# After sanitization, before output (around line 240)
from secret_wards.privacy import DateShifter, AgeGeneralizer, LocationGeneralizer, RareValueSuppressor, PrivacyMetricsCollector

# Initialize once per pipeline run
date_shifter = DateShifter(secret)
age_gen = AgeGeneralizer.from_policy_file(config_path)
loc_gen = LocationGeneralizer(min_level="district")
suppressor = RareValueSuppressor(policy_from_config)
metrics = PrivacyMetricsCollector()

# Apply per record (using Phase 5 pseudonym)
for sr in sanitized_records:
    pseudo = sr.pseudonym  # From Phase 5
    if pseudo:
        # Date shifting
        shifted_dates = date_shifter.shift_record_dates(extract_dates(sr), pseudo)
        apply_shifted_dates(sr, shifted_dates)
        metrics.record_date_shift(...)
        
        # Age generalization
        age_band = age_gen.generalize_dob(sr.dob)
        sr.age_band = age_band
        metrics.record_age_generalization(age_band)
        
        # Location generalization
        gen_addr = loc_gen.generalize(sr.address)
        sr.address = gen_addr
        metrics.record_location_generalization('district')

# Rare value suppression (batch after all records)
suppressed_records, stats = suppressor.apply_suppression(collect_qi(sanitized_records))

# Finalize metrics for report
privacy_metrics = metrics.finalize(total_records)
```

---

### Phase 7: Security → Pipeline Wrapper

#### Required Integration
| Component | Integration Point | Purpose |
|-----------|-------------------|---------|
| `KeyManager` | Pipeline init | Derive all purpose-specific keys |
| `TempFileEncryption` | Any intermediate persistence | Encrypt sensitive temp data |
| `SafeLogger` | Replace `setup_logging` | PII-safe structured logging |
| `SafeErrorHandler` | Wrap pipeline stages | Sanitized exception handling |
| `ExportHardener` | Before pipeline exit | Final output validation |

#### Integration Pattern
```python
# In main.py or pipeline/full.py run_pipeline()
from secret_wards.security import KeyManager, TempFileEncryption, ExportHardener
from secret_wards.utils.logging import setup_logging
from secret_wards.security.safe_logging import setup_safe_logging

def run_pipeline(...):
    # 1. Initialize security
    key_manager = KeyManager(secret)
    temp_encryption = TempFileEncryption(key_manager.get_encryption_key())
    export_hardener = ExportHardener(output_dir, secret)
    
    # 2. Setup PII-safe logging
    logger = setup_safe_logging(level="INFO", format="json")
    
    # 3. Use temp_encryption for any intermediate file writes
    # temp_path = temp_encryption.write_encrypted_temp(sensitive_data)
    # data = temp_encryption.read_encrypted_temp(temp_path)
    
    # 4. Run pipeline stages with safe error handling
    try:
        # ... existing pipeline code ...
    except Exception as e:
        handler = SafeErrorHandler()
        safe_info = handler.handle(e, context={"stage": "sanitization"})
        raise
    
    # 5. Final export validation
    success, checks = export_hardener.verify_and_finalize()
    if not success:
        raise RuntimeError("Export gate failed: " + str(checks))
    
    # 6. Cleanup
    temp_encryption.cleanup_all()
```

---

### Phase 8: Evaluation → CI/CD Integration

#### Benchmark Runner Integration
```python
# scripts/run_full_evaluation.py already exists
# Add to CI/CD pipeline:

# .github/workflows/evaluation.yml
# name: Full Evaluation
# on: [push, pull_request]
# jobs:
#   evaluate:
#     runs-on: ubuntu-latest
#     steps:
#       - uses: actions/checkout@v4
#       - name: Set up Python
#         uses: actions/setup-python@v5
#         with: { python-version: '3.10' }
#       - name: Install dependencies
#         run: pip install -r requirements.txt
#       - name: Generate test secret
#         run: echo "RAKSHA_SECRET=$(openssl rand -base64 32)" >> $GITHUB_ENV
#       - name: Run evaluation
#         run: python scripts/run_full_evaluation.py --input ./data --output ./eval_output
#       - name: Upload reports
#         uses: actions/upload-artifact@v4
#         with: { name: evaluation-reports, path: ./eval_output/ }
```

#### Required Artifacts for CI/CD
| Artifact | Path | Purpose |
|----------|------|---------|
| Benchmark Summary | `eval_output/benchmark_summary.json` | Machine-readable CI status |
| Evaluation Report | `eval_output/evaluation_report.json` | Human-readable quality report |
| PII Leakage Scan | Included in evaluation report | Compliance check |
| Medical Preservation | Included in evaluation report | Clinical utility check |

---

## Configuration Updates

### `config/policy.yaml` - Phase 6 Additions
```yaml
privacy:
  date_shift_range_days: 365
  age_bands:
    - [0, 4]
    - [5, 9]
    # ... 5-year bands up to 90+
    - [90, null]
  k_anonymity_min: 5
  rare_suppression_order:
    - diagnosis_category
    - age_band
    - location
  # Location hierarchy
  location:
    min_level: "district"  # or tehsil, village, etc.
    gazetteer_path: "data/gazetteers/census2011_village_district_state.csv"
```

### `config/policy.yaml` - Phase 7 Additions
```yaml
security:
  temp_encryption: true
  canary_prefix: "LOCKMATE_CANARY_"
  log_level: "INFO"
  log_format: "json"
  export_checks:
    pii_scan: true
    report_validation: true
    records_validation: true
    filename_check: true
    quarantine_isolation: true
    canary_verification: true
    attachment_check: true
    temp_files_cleaned: true
```

---

## Integration Test Plan

### 1. Phase 5 + Phase 6 Integration Test
```python
# test_phase5_6_integration.py
def test_privacy_with_phase5_clusters():
    # 1. Create synthetic patient clusters (mock Phase 5 output)
    clusters = create_mock_clusters()
    
    # 2. Run Phase 6 transforms
    date_shifter = DateShifter(secret)
    age_gen = AgeGeneralizer.from_policy_file(config_path)
    loc_gen = LocationGeneralizer(min_level="district")
    
    # 3. Verify:
    # - Same pseudonym → same shift across clusters
    # - Intervals preserved within cluster
    # - Age bands contain true ages
    # - Location generalized to district minimum
    # - Rare combinations suppressed
```

### 2. Phase 7 Security Regression Test
```python
# test_security_regression.py
def test_export_gate_blocks_pii():
    # 1. Create output with known PII
    # 2. Run ExportHardener
    # 3. Verify FAIL result
    
def test_temp_encryption_cleanup():
    # 1. Write encrypted temp files
    # 2. Simulate crash (don't call cleanup)
    # 3. Verify atexit handler cleans up
    
def test_log_sanitization():
    # 1. Log structured data with PII
    # 2. Verify output has [REDACTED] for forbidden fields
```

### 3. Phase 8 Benchmark CI Test
```bash
# Run in CI
RAKSHA_SECRET="..." python scripts/run_full_evaluation.py \
  --input ./data \
  --output ./eval_output \
  --skip-adversarial  # Optional for faster CI
  
# Check exit code
if [ $? -ne 0 ]; then
  echo "Evaluation failed"
  exit 1
fi
```

---

## Dependencies Summary

| Phase | Depends On | Provides |
|-------|------------|----------|
| 6 (Privacy) | Phase 5 (pseudonyms) | Date shifts, age bands, location generalization, rare suppression, metrics |
| 7 (Security) | None (self-contained) | KeyManager, TempFileEncryption, SafeLogger, SafeErrorHandler, ExportHardener |
| 8 (Evaluation) | Phases 6, 7 (for integration tests) | BenchmarkRunner, AdversarialTestSuite, AttackSimulator, EvaluationReport |

---

## Known Integration Blockers

| Blocker | Phase | Resolution |
|---------|-------|------------|
| Phase 5 pseudonyms not available | 6 | Use synthetic mocks for testing; integrate after Phase 5 merge |
| Pipeline integration points not wired | 6, 7 | Add adapter code in `pipeline/full.py` |
| Gazetteer data missing | 6 | Download Census 2011 CSV; configure path in policy.yaml |
| CI/CD not configured | 8 | Add GitHub Actions workflow |
| Official validator integration | 8 | Run organizer's validator on benchmark output |

---

## Recommended Merge Strategy

### Phase 1: Phase 5 Merge (Prerequisite)
```bash
# On main branch
git merge --no-ff feature/phase-5-identity
# Verify Phase 5 tests pass
python -m pytest tests/ -k "phase5 or identity"
```

### Phase 2: Phase 6-8 Merge (After Phase 5)
```bash
# On main branch (after Phase 5)
git merge --no-ff feature/phases-6-8-foundation

# Add integration adapters to pipeline/full.py
# Add config sections to policy.yaml
# Add GitHub Actions workflow

# Run full test suite
python -m pytest tests/ -v

# Run integration tests
python test_phase5_6_integration.py
python test_security_regression.py

# Run evaluation benchmark
RAKSHA_SECRET="..." python scripts/run_full_evaluation.py --input ./data

# Run official validator
python -m secret_wards.validator --output ./eval_output/sanitized
```

### Phase 3: Post-Merge Validation
- Run official organizer scoring on practice data
- Validate report.json and records.jsonl against organizer schema
- Verify no PII leakage in sanitized output
- Confirm medical preservation metrics
- Document any gaps for next iteration

---

## Rollback Plan

If integration issues arise:

```bash
# 1. Revert merge
git revert -m 1 <merge-commit>

# 2. Or reset to pre-merge state
git reset --hard HEAD~1

# 3. Phase 6-8 remain on feature branch for fixes
git checkout feature/phases-6-8-foundation
# Fix issues, re-test, re-merge
```

---

## Status Summary

| Component | Foundation | Integration Adapters | Config | CI/CD | Tests |
|-----------|------------|---------------------|--------|-------|-------|
| Phase 6 Privacy | ✅ | ❌ | ✅ | ❌ | ✅ Unit |
| Phase 7 Security | ✅ | ❌ | ✅ | ❌ | ✅ Unit |
| Phase 8 Evaluation | ✅ | ❌ | ❌ | ❌ | ✅ Unit |

**Overall**: Foundation complete. **Integration adapters are the only remaining work** for production readiness.

**Estimated Integration Effort**: 2-3 days (adapter code + config + CI/CD + integration tests)

**Recommendation**: Proceed with Phase 5 merge first, then integrate Phases 6-8 in sequence.