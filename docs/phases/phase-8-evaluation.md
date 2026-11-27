# Phase 8: Advanced Evaluation, Adversarial Robustness & Continuous Quality

## Overview

Phase 8 is a provisional engineering phase added to strengthen LOCKMATE beyond the basic organizer contract. Its scope is **advanced testing and continuous quality**, not a replacement for the organizer's scoring system.

Components:
1. **Synthetic Adversarial Test Generation** - Realistic but fictional test data
2. **Hidden-Format Robustness** - Tests on unseen formats and structures
3. **Privacy Attack Simulator** - Local experimental attack framework
4. **Unified Benchmark Runner** - Comprehensive evaluation orchestration
5. **Engineering Quality Report** - PII-free evaluation reporting

## Implementation Status

### ✅ Implemented Components

| Component | File | Status |
|-----------|------|--------|
| Synthetic Generator | `src/secret_wards/evaluation/synthetic_generator.py` | ✅ Complete |
| Adversarial Tests | `src/secret_wards/evaluation/adversarial_tests.py` | ✅ Complete |
| Attack Simulator | `src/secret_wards/evaluation/attack_simulator.py` | ✅ Complete |
| Benchmark Runner | `src/secret_wards/evaluation/benchmark.py` | ✅ Complete |
| Evaluation Report | `src/secret_wards/evaluation/evaluation_report.py` | ✅ Complete |
| Runner Script | `scripts/run_full_evaluation.py` | ✅ Complete |

### 🔧 Key Features Implemented

#### Synthetic Data Generator (`SyntheticDataGenerator`)
Generates fabricated records with:
- **Names**: English, Hindi (Devanagari), Hinglish, transliterated variants
- **Name orders**: First-Last, Last-First, with/without middle names
- **Similar names**: Different people with similar names (e.g., "Rajesh Sharma" vs "Rajes Sharma")
- **Identifiers**: Aadhaar, ABHA, PAN, phone, email with format variations
- **Addresses**: Multi-format (structured, free-text, Hindi, mixed-script)
- **Hierarchical locations**: House → Street → Village → Tehsil → District → State
- **Clinical data**: Diagnoses (common + rare), drugs, lab tests, doctors
- **Dates**: Multiple formats (ISO, DD/MM/YYYY, MM-DD-YYYY, etc.)
- **Attachments**: Base64-encoded synthetic binary data
- **Formats**: CSV, JSON, JSONL, FHIR Bundle
- **Controlled duplicates**: Same patient across records
- **Configurable seed** for reproducibility

#### Adversarial Test Suite (`AdversarialTestSuite`)
15 built-in test cases:
1. **CSV renamed columns** - Non-standard headers
2. **JSON deep nesting** - PII buried in nested objects
3. **JSON unusual keys** - PII in non-standard field names
4. **Mixed script** - English + Hindi + transliterated in same record
5. **Unusual dates** - 10+ date formats
6. **Pipe-separated CSV** - Non-comma delimiters
7. **Malformed JSON** - Syntax errors (should quarantine)
8. **Large records** - 100KB+ text fields
9. **Binary in text** - Embedded binary data (should quarantine)
10. **FHIR custom extensions** - PII in FHIR extensions
11. **CSV quoted newlines** - Newlines inside quoted fields
12. **Transliteration variants** - Multiple schemes for same name
13. **Empty/null values** - Sparse records
14. **Unicode edge cases** - ZWJ, RTL marks, normalization
15. **Multiple encodings** - Mixed UTF-8/Latin-1

Each test specifies expected behavior: process, quarantine, or fail gracefully.

#### Privacy Attack Simulator (`PrivacyAttackSimulator`)
Simulates 8 attack types with synthetic attacker knowledge:

| Attack | Description |
|--------|-------------|
| Direct Identifier | Match leaked Aadhaar/phone/PAN against output |
| Voter List Linkage | Name + address + age from voter rolls |
| Quasi-Identifier | Combine age_band + district + diagnosis + hospital |
| Rare Disease | Identify patients with rare diagnoses |
| Known Visit Date | Match known admission/discharge dates |
| Length of Stay | Unusual LOS + other QIs |
| Pseudonym Inversion | Reverse-engineer PSN-XXXXXXXX |
| Cross-Release | Link records across multiple releases |

**Reports**: Success rate, ambiguous matches, protected targets, limitations

**Important**: This is NOT the organizer's hidden attacker - it's a local experimental framework.

#### Benchmark Runner (`BenchmarkRunner`)
Orchestrates 7 evaluation phases:

| Phase | Description |
|-------|-------------|
| Unit | `pytest tests/unit` |
| Integration | `pytest tests/integration` |
| Adversarial | Synthetic adversarial tests |
| Validation | Output format validation |
| Practice | Self-check on organizer practice data |
| Performance | Throughput, memory, latency on 1000 records |
| Determinism | Two runs with same secret = identical output |

Generates machine-readable JSON summary for CI/CD.

#### Evaluation Report (`EvaluationReportGenerator`)
PII-free comprehensive report with:
- Build timestamp & toolkit commit
- Test counts & pass/fail status
- Contract validation results
- PII leakage metrics (scanned output)
- Medical preservation metrics
- Canary verification results
- Linkage metrics (when Phase 5 integrated)
- Privacy metrics (when Phase 6 integrated)
- Security metrics (when Phase 7 integrated)
- Runtime & peak memory
- Known limitations (15 documented)

### 📋 Usage

```bash
# Run full evaluation
RAKSHA_SECRET="..." python scripts/run_full_evaluation.py \
    --input ./data \
    --output ./evaluation_output \
    --config config/policy.yaml

# Skip slow phases
RAKSHA_SECRET="..." python scripts/run_full_evaluation.py \
    --skip-adversarial --skip-performance --skip-determinism
```

### 🧪 Tests

Evaluation framework tests:
1. Synthetic data generation (all formats)
2. Adversarial test execution
3. Attack simulation with known results
4. Benchmark phase orchestration
5. Report generation
6. Machine-readable output format
7. PII leakage detection accuracy
8. Canary verification

### 📝 Remaining Work

- [ ] Integration with main pipeline for adversarial tests
- [ ] Practice data self-check automation
- [ ] Organizer's official validator integration
- [ ] Continuous integration (GitHub Actions)
- [ ] Historical trend tracking
- [ ] Differential privacy metrics
- [ ] Formal threat model documentation
- [ ] Attack simulation calibration against organizer's ATTACKS.md
- [ ] Performance regression detection
- [ ] Automated limitation tracking

## Acceptance Criteria

- [x] Synthetic adversarial generator implemented
- [x] Hidden-format robustness tests implemented
- [x] Privacy attack simulator implemented
- [x] Unified evaluation runner implemented
- [x] Machine-readable evaluation report generated
- [x] PII-free reporting verified
- [x] Tests and limitations documented

**Phase 8 Status: FOUNDATION COMPLETE** — Evaluation framework operational. Requires integration with main pipeline and organizer's validation tools.