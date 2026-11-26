# Merge Strategy: Reconciling `lockmate.ingestion` and `secret_wards`

## Overview

This document proposes a merge strategy to reconcile two complementary implementations:

1. **`lockmate.ingestion`** (branch `agent/satwilk`) - Complete validation, parsing, and output modules with security-first architecture
2. **`secret_wards`** (branch `origin/main`) - Contracts layer, pipeline stubs, CLI, and parser implementations

Both implementations target the same goal: secure data ingestion pipeline producing Secret-Wards-ToolKit compatible output (`sanitized/` folder, `report.json`, `records.jsonl`).

---

## Current State Analysis

### `lockmate.ingestion` (agent/satwilk) - Strengths
- ✅ Complete 5-layer security validation (path guard, symlink guard, size limits, file validator, quarantine)
- ✅ Format parsers: CSV/TSV, JSON (nested), Text, FHIR R4
- ✅ Output modules: serializer, atomic write, report generator, records generator
- ✅ 116 passing tests (7 skipped on Windows)
- ✅ Security-first architecture with comprehensive threat modeling
- ✅ Windows-compatible (libmagic fallback, charset-normalizer 3.x fix)
- ✅ Contracts adapter layer with fallback types (bridge to secret_wards.contracts)
- ✅ Produces Secret-Wards-ToolKit compatible output

### `secret_wards` (origin/main) - Strengths
- ✅ Well-defined contracts (`secret_wards.contracts`): 12 frozen dataclasses + enums
- ✅ Pipeline architecture (basic.py, full.py) with clear phase separation
- ✅ CLI entry point (`main.py`) with argument parsing
- ✅ Parser implementations with base class abstraction
- ✅ PII detection, linkage, privacy modules (Samridh's work - **do not modify**)
- ✅ Type-safe contract definitions with validation

### Gap Analysis
| Feature | lockmate.ingestion | secret_wards |
|---------|-------------------|--------------|
| Security validation | Complete (5 layers) | Not implemented |
| Format parsers | 4 parsers, production-ready | Base + implementations |
| Contracts/types | Fallback in adapter | Canonical (12 dataclasses) |
| Pipeline orchestration | SecureIngestionPipeline | BasicPipeline, FullPipeline |
| CLI | Not implemented | Implemented |
| PII detection | Not implemented | Implemented (Samridh) |
| Record linkage | Not implemented | Implemented (Samridh) |
| Privacy transforms | Not implemented | Implemented (Samridh) |
| Tests | 116 passing | Unknown |
| Windows support | Full | Unknown |

---

## Proposed Merge Strategy

### Phase 1: Align Contracts (Immediate - No Code Changes to Samridh's Modules)

**Goal**: Adopt `secret_wards.contracts` as the single source of truth for shared types.

**Actions**:
1. **Pull `secret_wards.contracts` from `origin/main`** into `agent/satwilk`
   ```bash
   git fetch origin main
   git checkout origin/main -- secret_wards/contracts.py
   # Or merge the contracts module specifically
   ```

2. **Remove fallback types** from `contracts_adapter.py` once canonical contracts are available
   - Replace local `FormatType`, `RecordStatus`, `FieldType`, etc. enums with imports from `secret_wards.contracts`
   - Keep adapter logic for conversion from parser output → contracts

3. **Update adapter imports** to use canonical contracts:
   ```python
   # In contracts_adapter.py
   from secret_wards.contracts import (
       UnifiedRecord, ParsedDocument, InputFile,
       FullReport, RecordsEntry,
       FormatType, RecordStatus, FieldType,
       PIIType, MedicalType, QuarantineReason,
       RecordLocationType, RecordLocation,
       FieldValue, FileReportEntry,
       ReportTotals, ReportTiming, ReportResources,
   )
   ```

4. **Verify all tests pass** with canonical contracts

**Risk**: Low - only affects adapter layer, no changes to Samridh's detection/linkage/privacy modules

---

### Phase 2: Unify Pipeline Orchestration (Short-term)

**Goal**: Single pipeline implementation combining security validation + contracts output + detection/linkage/privacy

**Approach**: Create unified pipeline that:
1. Uses `lockmate.ingestion` validation layers (path guard, symlink guard, size limits, file validator, quarantine)
2. Uses `lockmate.ingestion` parsers (CSV, JSON, Text, FHIR)
3. Uses `secret_wards.contracts` for all data types
4. Integrates Samridh's detection → linkage → privacy phases (from `secret_wards.pipeline`)
5. Uses `lockmate.ingestion` output modules (serializer, atomic_write) + contracts adapter for report.json/records.jsonl

**Proposed Structure**:
```
src/
├── lockmate/
│   ├── ingestion/
│   │   ├── validation/        # 5-layer security (keep)
│   │   ├── parsers/           # 4 format parsers (keep)
│   │   ├── output/            # serializer, atomic_write (keep)
│   │   ├── adapters/          # contracts_adapter (update to use canonical contracts)
│   │   ├── pipeline/
│   │   │   ├── secure_ingest.py       # Main pipeline (merge both)
│   │   │   ├── detection_phase.py     # Samridh's detection (import, don't modify)
│   │   │   ├── linkage_phase.py       # Samridh's linkage (import, don't modify)
│   │   │   ├── privacy_phase.py       # Samridh's privacy (import, don't modify)
│   │   │   └── contracts_phase.py     # Contracts output (new)
│   │   └── config.py
│   └── cli/
│       └── main.py            # Unified CLI (merge both)
└── secret_wards/
    └── contracts.py           # Canonical contracts (single source)
```

**Pipeline Flow**:
```
Input Files
    │
    ▼
┌─────────────────────────────────────┐
│ 5-Layer Security Validation         │  ← lockmate.ingestion.validation
│ (path, symlink, size, mime, quarantine)
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ Format Parsers                      │  ← lockmate.ingestion.parsers
│ (CSV, JSON, Text, FHIR)             │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ Contracts Adapter                   │  ← lockmate.ingestion.adapters
│ (parser output → UnifiedRecord)     │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ Detection Phase (PII/Medical)       │  ← secret_wards.detection (Samridh)
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ Linkage Phase (Patient Clusters)    │  ← secret_wards.linkage (Samridh)
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ Privacy Phase (Generalize/Suppress) │  ← secret_wards.privacy (Samridh)
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ Output Generation                   │  ← lockmate.ingestion.output
│ (sanitized/, report.json, records.jsonl)
└─────────────────────────────────────┘
```

---

### Phase 3: Unified CLI (Short-term)

**Goal**: Single CLI entry point combining both implementations

**Actions**:
1. Merge `secret_wards.main.py` CLI with `lockmate.ingestion` config
2. Support both pipeline modes:
   - `--mode secure` - Security validation only (lockmate)
   - `--mode full` - Full pipeline with detection/linkage/privacy (secret_wards)
3. Add config file support (YAML/JSON)

---

### Phase 4: Testing & Validation (Ongoing)

**Goal**: Unified test suite

**Actions**:
1. Merge test suites
2. Add integration tests with Secret-Wards-ToolKit synthetic data
3. Add contract compliance tests (verify output matches expected schema)
4. CI/CD pipeline for both Windows and Linux

---

## Merge Mechanics

### Option A: PR from `agent/satwilk` → `main` (Recommended)

```bash
# On agent/satwilk branch
git fetch origin
git rebase origin/main  # Resolve conflicts in contracts_adapter.py, pipeline, etc.

# Create PR from agent/satwilk → main
# Title: "feat: merge lockmate.ingestion security/parsers/output with secret_wards contracts/pipeline"
```

**Conflict Resolution Priority**:
1. **`contracts_adapter.py`** - Use canonical `secret_wards.contracts`, remove fallbacks
2. **`secure_ingest.py`** - Merge pipeline logic, keep security validation, add detection/linkage/privacy phases
3. **`config.py`** - Merge configuration models
4. **Tests** - Combine both test suites

### Option B: New Unified Package Structure

Create a new package layout that cleanly separates concerns:

```
lockmate/                    # Root package
├── contracts/               # Canonical contracts (from secret_wards)
│   └── __init__.py         # Re-exports from secret_wards.contracts
├── validation/              # 5-layer security (from lockmate.ingestion.validation)
├── parsers/                 # Format parsers (from lockmate.ingestion.parsers)
├── output/                  # Output generation (from lockmate.ingestion.output)
├── pipeline/                # Unified pipeline
│   ├── phases/
│   │   ├── validation.py   # Security validation phase
│   │   ├── parsing.py      # Format parsing phase
│   │   ├── detection.py    # Samridh's detection (import)
│   │   ├── linkage.py      # Samridh's linkage (import)
│   │   ├── privacy.py      # Samridh's privacy (import)
│   │   └── contracts.py    # Contracts output phase
│   └── orchestrator.py     # Pipeline orchestration
├── adapters/                # Parser → contracts adapter
├── config.py                # Unified config
└── cli/
    └── main.py              # Unified CLI
```

---

## Coordination Points with Samridh

### Required from Samridh (`origin/main`):
1. **Export `secret_wards.contracts`** as installable package or copy to `lockmate/contracts/`
2. **Document detection/linkage/privacy interfaces** - What inputs/outputs each phase expects
3. **Confirm CLI argument structure** for unified entry point
4. **Review contract schema** - Ensure `UnifiedRecord`, `ParsedDocument`, `FullReport`, `RecordsEntry` match Secret-Wards-ToolKit expectations

### Provided by this branch (`agent/satwilk`):
1. **Complete security validation** - Ready to integrate as pipeline phase
2. **Production-ready parsers** - CSV, JSON, Text, FHIR with tests
3. **Output generation** - Atomic writes, serializer, report/records generators
4. **Contracts adapter** - Bridge from parser output → contracts types
5. **116 passing tests** - Validation, parsers, output, integration
6. **Windows compatibility** - libmagic fallback, charset-normalizer 3.x fix

---

## Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Align Contracts | 1-2 days | Samridh pushes contracts to main |
| Phase 2: Unify Pipeline | 3-5 days | Phase 1 complete, Samridh documents phase interfaces |
| Phase 3: Unified CLI | 1-2 days | Phase 2 complete |
| Phase 4: Testing | 2-3 days | Parallel with Phase 2-3 |
| **Total** | **1-2 weeks** | |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Contract schema mismatch | Phase 1 validates early; adapter tests verify compatibility |
| Breaking Samridh's modules | **Do not modify** detection/linkage/privacy - import as-is |
| Windows vs Linux differences | CI on both; lockmate already Windows-tested |
| Test coverage gaps | Merge test suites; add Secret-Wards-ToolKit synthetic data tests |
| Merge conflicts | Rebase frequently; isolate changes to adapter/pipeline layers |

---

## Success Criteria

1. ✅ Single `lockmate` package with unified pipeline
2. ✅ Canonical contracts from `secret_wards.contracts`
3. ✅ 5-layer security validation integrated
4. ✅ All 4 format parsers working
5. ✅ Detection → Linkage → Privacy phases integrated (Samridh's code, unmodified)
6. ✅ Output: `sanitized/` folder, `report.json`, `records.jsonl` matching Secret-Wards-ToolKit
7. ✅ All tests passing on Windows and Linux
8. ✅ Single CLI entry point

---

## Next Steps

1. **Samridh**: Push `secret_wards.contracts` to `origin/main` (or share directly)
2. **Both**: Review contract schema alignment (this document + Samridh's contracts)
3. **Satwilk**: Rebase `agent/satwilk` onto updated `origin/main`
4. **Satwilk**: Implement Phase 1 (align contracts in adapter)
5. **Both**: Pair on Phase 2 pipeline integration
6. **Create PR** from `agent/satwilk` → `main` for review

---

## Appendix: Key Files to Merge

### From `agent/satwilk` (keep/adapt):
- `src/lockmate/ingestion/validation/` - All 5 layers
- `src/lockmate/ingestion/parsers/` - All 4 parsers
- `src/lockmate/ingestion/output/` - Serializer, atomic_write
- `src/lockmate/ingestion/adapters/contracts_adapter.py` - Update to use canonical contracts
- `src/lockmate/ingestion/secure_ingest.py` - Merge into unified pipeline
- `src/lockmate/ingestion/config.py` - Merge configs
- `src/lockmate/ingestion/tests/` - All tests

### From `origin/main` (keep/adapt):
- `secret_wards/contracts.py` - Canonical contracts (single source)
- `secret_wards/pipeline/basic.py` - Pipeline structure reference
- `secret_wards/pipeline/full.py` - Full pipeline reference
- `secret_wards/main.py` - CLI reference
- `secret_wards/intake/pipeline.py` - Intake pipeline reference
- `secret_wards/parsers/` - Parser base class reference
- Samridh's detection/linkage/privacy modules - **Import only, do not modify**

---

*Document version: 1.0*  
*Author: Satwilk (agent/satwilk branch)*  
*Date: 2026-11-26*