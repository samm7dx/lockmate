# LOCKMATE — Organizer Asset Report

**Date:** 2026-11-26  
**Status:** Assets NOT FOUND in workspace

---

## 1. Official Assets Search Results

### 1.1 Validator Script (`validate_output.py`)

| Search Location | Found | Path | Version/Hash |
|-----------------|-------|------|--------------|
| Workspace root (`C:\Users\samri\lockmate`) | ❌ No | — | — |
| Workspace `docs/` | ❌ No | — | — |
| Parent directory (`C:\Users\samri`) | ❌ No | — | — |
| Organizer repository (if cloned) | ❓ Unknown | — | — |

**Conclusion:** Official validator **NOT FOUND** in workspace.

**Action Required:** Request `validate_output.py` from Yugaantar DevForge organizers.

---

### 1.2 Practice Dataset (`dev/input/`)

| Search Location | Found | Path | Size/Files |
|-----------------|-------|------|------------|
| Workspace root | ❌ No | — | — |
| Workspace `docs/` | ❌ No | — | — |
| Parent directory | ❌ No | — | — |
| Organizer repository | ❓ Unknown | — | — |

**Conclusion:** Practice dataset **NOT FOUND** in workspace.

**Action Required:** Request `dev/input/` dataset from Yugaantar DevForge organizers.

---

### 1.3 Official Specification Document

| Search Location | Found | Path | Version |
|-----------------|-------|------|---------|
| Workspace root | ❌ No | — | — |
| Organizer repository | ❓ Unknown | — | — |

**Conclusion:** Official spec document not in workspace. Engineering documents (`context.md`, `engineering-strategy.md`) are derived from organizer specification but may not be exhaustive.

**Action Required:** Obtain official specification PDF/Markdown from organizers.

---

## 2. Impact Assessment

| Asset | Required For | Impact if Missing | Mitigation |
|-------|--------------|-------------------|------------|
| `validate_output.py` | Official `CONTRACT OK` verification | **CRITICAL** — Cannot claim official validation | Build self-validator from contract spec (context.md §3.6, §16) |
| `dev/input/` | Detection tuning, linkage training, clinical preservation validation | **HIGH** — No ground truth for P0 components | Generate synthetic fixtures with known labels (tests/fixtures/generator.py) |
| Official spec | Requirements completeness verification | **MEDIUM** — Risk of missing requirements | Cross-reference engineering docs with organizer communications |

---

## 3. Self-Validator Specification

Since official validator is unavailable, implement internal validator matching organizer contract:

### 3.1 Validation Scope

```python
# tests/validators/contract_validator.py

def validate_output(output_dir: Path, input_dir: Path) -> ValidationResult:
    """
    Validates output against organizer specification.
    Returns ValidationResult(passed: bool, errors: List[str], warnings: List[str])
    """
    checks = [
        check_output_structure,
        check_report_json_schema,
        check_report_json_totals,
        check_records_jsonl_schema,
        check_records_jsonl_consistency,
        check_sanitized_formats,
        check_no_pii_in_output,
        check_filenames_safe,
        check_metadata_safe,
        check_quarantine_handling,
    ]
    # All checks must pass
```

### 3.2 Validation Checks

| Check | Description | Organizer Spec Ref |
|-------|-------------|-------------------|
| `check_output_structure` | `sanitized/`, `report.json`, `records.jsonl` exist | §4.1 |
| `check_report_json_schema` | Exact schema per context.md §16.2 | §4.3, §16.2 |
| `check_report_json_totals` | Counts match actual pipeline results | §4.3 |
| `check_records_jsonl_schema` | Exact schema per context.md §16.3 | §4.4, §16.3 |
| `check_records_jsonl_consistency` | Same patient = same pseudonym; pseudonym in sanitized record | §4.4 |
| `check_sanitized_formats` | CSV/JSON/FHIR parseable; FHIR R4 valid | §4.2 |
| `check_no_pii_in_output` | Scan with detection engine; zero high-confidence PII | §6.G, §6.H |
| `check_filenames_safe` | No PII in output paths | §4.2, §6.G.4 |
| `check_metadata_safe` | No PII in JSON keys, FHIR meta | §6.G.2, §6.G.5 |
| `check_quarantine_handling` | Quarantined files in output with reason | §4.2, §17 |

---

## 4. Synthetic Fixture Strategy

Since practice dataset unavailable, generate fixtures with known ground truth:

### 4.1 Fixture Requirements

| Fixture | Purpose | Records | Formats |
|---------|---------|---------|---------|
| `hospital_a/` | CSV with Latin names, Aadhaar, phone | 500 | CSV |
| `hospital_b/` | JSON with Devanagari names, ABHA, UHID | 500 | JSON |
| `hospital_c/` | FHIR R4 with Hinglish names, PAN | 300 | FHIR |
| `hospital_d/` | Text notes with transliterated names | 200 | Text |
| `adversarial/` | Ambiguous cases, edge cases | 100 | Mixed |

### 4.2 Ground Truth Labels

Each record labeled with:
- True patient ID (for linkage evaluation)
- All PII spans with types and offsets
- All clinical spans with types and offsets
- Expected pseudonym (deterministic for given secret)
- Expected age band, location generalization, date shift

### 4.3 Adversarial Cases

| Case Type | Description | Expected Behavior |
|-----------|-------------|-------------------|
| Same name, different DOB | "Rahul Sharma" DOB 1990 vs 1995 | Separate pseudonyms |
| Same name, different Aadhaar | "Rahul Sharma" Aadhaar 111... vs 222... | Separate pseudonyms |
| C/O fever vs C/O Rahul | Clinical vs relative | Fever preserved, Rahul → relative |
| Dr. Rahul vs patient Rahul | Doctor context vs patient | Doctor preserved, patient → pseudonym |
| Parkinson's disease | Disease eponym | Preserved |
| Shifted CSV columns | Headers misaligned | Content-based matching |
| Nested JSON PII | Deep nesting | Recursive scan |
| FHIR extension PII | Custom extensions | Extension scanner |

---

## 5. Asset Acquisition Plan

| Action | Owner | Deadline | Status |
|--------|-------|----------|--------|
| Request `validate_output.py` from organizers | Lead | Day 1 | ⬜ Pending |
| Request `dev/input/` dataset from organizers | Lead | Day 1 | ⬜ Pending |
| Request official spec document | Lead | Day 1 | ⬜ Pending |
| Build self-validator | QA/Red-Team | Sprint 6 | ⬜ Planned |
| Generate synthetic fixtures | Red-Team | Sprint 0-1 | ⬜ Planned |

---

## 6. Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Organizer never provides validator | Medium | Cannot claim official `CONTRACT OK` | Self-validator + clear documentation |
| Organizer provides validator late | High | Delayed validation | Self-validator ready by Sprint 6 |
| Practice dataset has different format than expected | Medium | Detection/linkage tuning off | Synthetic fixtures cover all specified formats |
| Self-validator diverges from official | Low | False confidence | Mirror spec exactly; test against official when available |

---

## 7. Recommendation

**Proceed with implementation using:**
1. Engineering documents (`context.md`, `engineering-strategy.md`) as primary spec
2. Self-validator built from contract specification
3. Synthetic fixtures for all testing

**Do not block implementation waiting for organizer assets.** Document all assumptions clearly in `CONTRACT_CHECKLIST.md` and `ASSET_REPORT.md`.

---

**END OF ASSET REPORT**