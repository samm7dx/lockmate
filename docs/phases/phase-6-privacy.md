# Phase 6: Quasi-Identifier Privacy & Re-identification Protection

## Overview

Phase 6 implements the first working privacy layer that reduces patient re-identification risk while retaining medically useful information. It implements four primary mechanisms:

1. **Per-patient date shifting** - Deterministic date shifting using RAKSHA_SECRET
2. **Age generalization** - Configurable age bands (5-year default)
3. **Location generalization** - Hierarchical location generalization (House → State)
4. **Rare-value suppression** - k-anonymity based suppression of rare combinations

## Implementation Status

### ✅ Implemented Components

| Component | File | Status |
|-----------|------|--------|
| Date Shifter | `src/secret_wards/privacy/date_shift.py` | ✅ Complete |
| Age Generalizer | `src/secret_wards/privacy/age_generalizer.py` | ✅ Complete |
| Location Generalizer | `src/secret_wards/privacy/location_generalizer.py` | ✅ Complete |
| Rare Value Suppressor | `src/secret_wards/privacy/rare_value_suppressor.py` | ✅ Complete |
| Privacy Metrics | `src/secret_wards/privacy/privacy_metrics.py` | ✅ Complete |

### 🔧 Key Features Implemented

#### Date Shifting (`DateShifter` class)
- Uses HMAC-SHA256 with domain separation (`lockmate.date_shift.v1`)
- Same patient + same secret = same shift (deterministic)
- Different secrets produce different shifts
- Preserves intervals between dates for same patient
- Preserves length of stay
- Handles FHIR date formats
- Configurable shift range (±365 days default)

#### Age Generalization (`AgeGeneralizer` class)
- Configurable age bands via `config/policy.yaml`
- Default: 5-year bands (0-4, 5-9, ..., 85-89, 90+)
- Supports wider bands for higher privacy
- Ensures true age always falls within published band
- Handles infant and elderly ranges
- Loadable from policy configuration

#### Location Generalization (`LocationGeneralizer` class)
- Hierarchical levels: House → Street → Locality → Village → Tehsil → District → State
- Configurable minimum retention level (default: district)
- Gazetteer support for Census 2011 data
- Handles English, Hindi, and transliterated addresses
- Regex-based component detection
- Structured field generalization

#### Rare Value Suppression (`RareValueSuppressor` class)
- k-anonymity threshold (default: 5)
- Configurable quasi-identifiers
- Generalization order for progressive suppression
- Protected clinical fields never suppressed
- Auditable suppression decisions

#### Privacy Metrics (`PrivacyMetricsCollector` class)
- Records generalized/suppressed counts
- Age band distribution
- Location generalization level distribution
- Date shift distribution
- Interval preservation verification
- Length-of-stay preservation verification
- Clinical utility preservation rate
- Determinism verification

### 📋 Configuration

Policy configuration in `config/policy.yaml`:

```yaml
privacy:
  date_shift_range_days: 365
  age_bands:
    - [0, 4]
    - [5, 9]
    # ... 5-year bands up to 90+
    - [90, null]  # 90+
  k_anonymity_min: 5
  rare_suppression_order:
    - diagnosis_category
    - age_band
    - location
```

### 🧪 Tests

Unit tests cover:
1. Same patient, same secret → same shift
2. Same patient, different secret → different shift
3. Different patients → independently derived shifts
4. Same-patient dates retain consistent offsets
5. Length of stay remains unchanged
6. Inter-event intervals remain unchanged
7. Age band contains true age
8. Location generalization follows policy
9. Rare combinations are detected
10. Suppression does not destroy medical values
11. FHIR dates remain valid
12. Output remains deterministic
13. Missing patient identity handled safely
14. Different configurations produce expected transformations

### ⚠️ Integration Dependencies

**Requires Phase 5 (Identity Linkage)** for:
- Stable patient pseudonyms (PSN-XXXXXXXX) to derive date shifts
- Cross-hospital identity for consistent shifts across files
- Patient clusters for record-level generalization

**Current State**: Phase 6 components are implemented and independently testable with synthetic mock identities. Integration with Phase 5 is pending.

**Interface**: `DateShifter.get_shift(patient_pseudonym: str) -> int` expects a Phase 5 pseudonym.

### 📝 Remaining Work

- [ ] Integration with Phase 5 pseudonyms
- [ ] Pipeline integration in `pipeline/full.py`
- [ ] Gazetteer data loading from Census 2011 CSV
- [ ] Rare disease ontology integration (ICD-10 based)
- [ ] Per-field age band configuration
- [ ] Clinical utility preservation validation on practice data
- [ ] Performance optimization for large datasets

## Acceptance Criteria

- [x] Date shifting implemented
- [x] Age generalization implemented
- [x] Location generalization implemented
- [x] Rare-value suppression implemented
- [x] Medical preservation tested (unit tests)
- [x] Determinism tested (unit tests)
- [x] Synthetic privacy tests passed
- [x] Phase 5 integration interface documented
- [ ] Remaining integration dependencies documented

**Phase 6 Status: FOUNDATION COMPLETE** — Independent components work, but full integration pending Phase 5.