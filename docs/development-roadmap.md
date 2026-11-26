# LOCKMATE — Development Roadmap

**Version:** 1.0  
**Date:** 2026-11-26  
**Status:** Authoritative implementation roadmap

---

## 1. Roadmap Overview

This roadmap translates the 14-phase plan from `engineering-strategy.md` into actionable sprints with concrete deliverables, dependencies, and exit criteria.

### Phase Summary

| Phase | Name | Priority | Duration | Key Deliverable |
|-------|------|----------|----------|-----------------|
| 0 | Foundation & Contract Audit | P0 | 1-2 days | `raksha.toml`, `main.py`, `contracts.py`, contract checklist |
| 1 | Shared Models & Interfaces | P0 | 1 day | `src/secret_wards/contracts.py` (12 dataclasses) |
| 2 | Secure Intake & Ingestion | P0 | 3-4 days | 5 parsers + intake pipeline → URM |
| 3 | Basic Sanitization Pipeline | P0 | 2-3 days | End-to-end CSV/JSON/Text with placeholder detection |
| 4 | PII Detection Engine | P0 | 4-5 days | Production multilingual detection |
| 5 | Clinical Preservation | P0 | 2-3 days | Medical veto + clinical detectors |
| 6 | Output Security Gate & Reporting | P0 | 2-3 days | `report.json`, `records.jsonl`, independent gate |
| 7 | Identity Resolution & Linkage | P1 | 3-4 days | Conservative cross-file linkage |
| 8 | Pseudonymization | P1 | 1-2 days | HMAC-SHA256 pseudonyms with domain separation |
| 9 | Date & Age Transformations | P1 | 2 days | Per-patient date shift + age bands |
| 10 | Location & Rare-Value Protection | P1 | 2-3 days | Location generalization + k-anonymity + attacker sim |
| 11 | FHIR & Extended Format Hardening | P1 | 2 days | Full FHIR R4 support |
| 12 | Red-Team Evaluation & Hardening | P1 | 2-3 days | Adversarial tests, performance, security review |
| 13 | Performance Optimization | P1 | 1-2 days | Meet 15min/4GB/2CPU with margin |
| 14 | Frontend & Demonstration | P2 | 1-2 days | Optional demo app |

**Total Estimated Duration:** 28-38 days (5-7 weeks)

---

## 2. Detailed Sprint Plan

### Sprint 0: Foundation (Days 1-2) — **P0**

| Task | Owner | Deliverable | Exit Criteria |
|------|-------|-------------|---------------|
| Initialize git repo in `C:\Users\samri\lockmate` | Lead | `.git/` with initial commit | `git log --oneline` shows commits |
| Create `raksha.toml` with placeholder team name | Lead | `raksha.toml` | Keys match spec exactly |
| Create minimal `main.py` scaffold | Lead | `main.py` | CLI parses `--input` `--output`; reads `RAKSHA_SECRET` |
| Create `requirements.txt` with pinned deps | Lead | `requirements.txt` | All core deps listed with version constraints |
| Create `config/policy.yaml` | Lead | `config/policy.yaml` | All config sections present |
| Request organizer assets (`validate_output.py`, `dev/input/`) | Lead | `ASSET_REPORT.md` | Status documented |
| Produce `REPO_INVENTORY.md` | Auditor | `docs/REPO_INVENTORY.md` | All files cataloged |
| Produce `CONTRACT_CHECKLIST.md` | Auditor | `docs/CONTRACT_CHECKLIST.md` | Every organizer req mapped |
| Produce `BACKLOG.md` prioritized | Orchestrator | `docs/BACKLOG.md` | All tasks have owner, deps, acceptance |

**Sprint 0 Definition of Done:** All 9 tasks complete; `main.py` runs without crash (stub pipeline).

---

### Sprint 1: Shared Contracts (Days 3-4) — **P0**

| Task | Owner | Deliverable | Exit Criteria |
|------|-------|-------------|---------------|
| Implement 12 frozen dataclasses in `contracts.py` | Orchestrator | `src/secret_wards/contracts.py` | All 12 classes defined with type hints |
| Add `to_dict()`/`from_dict()` serialization | Orchestrator | `contracts.py` | JSON round-trip test passes |
| Create `src/secret_wards/__init__.py` exporting contracts | Orchestrator | `__init__.py` | `from secret_wards.contracts import ...` works |
| Write `tests/unit/test_contracts.py` | Orchestrator | `test_contracts.py` | All dataclass instantiation tests pass |

**Sprint 1 Definition of Done:** Contracts package importable; all unit tests pass.

---

### Sprint 2: Intake & Parsing (Days 5-9) — **P0**

| Task | Owner | Deliverable | Exit Criteria |
|------|-------|-------------|---------------|
| File discovery walker (`intake/discovery.py`) | Ingestion | `discovery.py` | Symlink/path traversal blocked; size limits enforced |
| SHA-256 streaming calculator (`intake/hashing.py`) | Ingestion | `hashing.py` | Matches `sha256sum`; low memory |
| Format classifier (`intake/classifier.py`) | Ingestion | `classifier.py` | Extension + content sniffing; UNKNOWN for unsupported |
| Encoding detector (`intake/encoding.py`) | Ingestion | `encoding.py` | `charset-normalizer` primary; no Latin-1 fallback |
| CSV/TSV parser (`parsers/csv_parser.py`) | Ingestion | `csv_parser.py` | Auto-delimiter, header inference, shifted columns |
| JSON parser (`parsers/json_parser.py`) | Ingestion | `json_parser.py` | Streaming, nested walk, JSON Pointer paths |
| Plain text parser (`parsers/text_parser.py`) | Ingestion | `text_parser.py` | Line/paragraph segmentation, offset maps |
| FHIR R4 parser (`parsers/fhir_parser.py`) | Ingestion | `fhir_parser.py` | `fhir.resources` validation, refs, extensions, contained |
| Quarantine classifier (`intake/quarantine.py`) | Ingestion | `quarantine.py` | Reason codes from context.md §17.1 |
| Intake pipeline integration (`intake/pipeline.py`) | Ingestion | `pipeline.py` | Mixed format dir → URM + quarantine; no crashes |

**Sprint 2 Definition of Done:** All 5 parsers produce valid URM; intake pipeline processes 100 mixed files.

---

### Sprint 3: Basic Sanitization (Days 10-12) — **P0**

| Task | Owner | Deliverable | Exit Criteria |
|------|-------|-------------|---------------|
| Placeholder PII detector (`detection/placeholder.py`) | Detection | `placeholder.py` | Regex: email, phone, PAN, 12-digit, dates |
| Placeholder medical veto (`clinical/placeholder.py`) | Clinical | `placeholder.py` | Regex: dosages, frequencies, disease names |
| Span merger + veto (`detection/merger.py`) | Detection | `merger.py` | Medical spans veto overlapping PII |
| Text replacer (`transform/replacer.py`) | Detection | `replacer.py` | Offset-map aware; preserves structure |
| Structured field sanitizer (`transform/structured.py`) | Detection | `structured.py` | CSV/JSON/FHIR fields replaced |
| Serializer (`output/serializer.py`) | Output | `serializer.py` | Format-preserving, UTF-8, PSN-TEMP placeholder |
| Filename sanitizer (`output/namer.py`) | Output | `namer.py` | SHA-256 prefix + ext; no PII in path |
| Atomic writer (`output/writer.py`) | Output | `writer.py` | Temp → rename; cleanup on error |
| Basic pipeline integration (`pipeline/basic.py`) | Orchestrator | `basic.py` | CSV/JSON/Text → sanitized + reports |

**Sprint 3 Definition of Done:** End-to-end basic pipeline runs; produces valid `sanitized/`, `report.json`, `records.jsonl`.

---

### Sprint 4: Production PII Detection (Days 13-17) — **P0**

| Task | Owner | Deliverable | Exit Criteria |
|------|-------|-------------|---------------|
| Unicode normalization (`detection/normalize.py`) | Detection | `normalize.py` | NFC, Devanagari digits, offset maps |
| Structured field scanner (`detection/structured.py`) | Detection | `structured.py` | Headers, JSON keys, FHIR paths, filenames |
| Phone detector (`detection/identifiers.py`) | Detection | `identifiers.py` | `phonenumbers` + regex; Devanagari digits |
| Aadhaar detector (`detection/identifiers.py`) | Detection | `identifiers.py` | 12 digits + Verhoeff checksum |
| ABHA detector (`detection/identifiers.py`) | Detection | `identifiers.py` | 14 digits, format validation |
| PAN detector (`detection/identifiers.py`) | Detection | `identifiers.py` | Regex `^[A-Z]{5}[0-9]{4}[A-Z]$` |
| UHID/MRN detector (`detection/identifiers.py`) | Detection | `identifiers.py` | Context-aware patterns |
| Email/URL detector (`detection/identifiers.py`) | Detection | `identifiers.py` | RFC 5322 + URL regex |
| PIN/Address detector (`detection/identifiers.py`) | Detection | `identifiers.py` | 6-digit PIN; address keywords |
| Date detector (`detection/identifiers.py`) | Detection | `identifiers.py` | `dateparser` + contextual classification |
| Honorific/Relationship triggers (`detection/names.py`) | Detection | `names.py` | S/o, D/o, W/o, C/O, श्री, पुत्र, देखभाल |
| Gazetteer loader (`detection/gazetteer.py`) | Detection | `gazetteer.py` | Offline, Latin+Devanagari, transliteration variants |
| Transliteration + Double Metaphone (`detection/transliterate.py`) | Detection | `transliterate.py` | indic-transliteration → IAST → Latin → Double Metaphone |
| Name detector (`detection/names.py`) | Detection | `names.py` | Gazetteer + trigger proximity + role classification |
| CRF tagger (`detection/crf_tagger.py`) | Detection | `crf_tagger.py` | Conditional: only if >5% F1 gain |
| Residual scanner (`detection/residual.py`) | Detection | `residual.py` | Re-scans output for stragglers |
| Detection engine (`detection/engine.py`) | Detection | `engine.py` | Runs all detectors; merges spans; confidence scoring |

**Sprint 4 Definition of Done:** PII detection recall ≥95%, precision ≥90% on labeled fixture; medical veto precision ≥98%.

---

### Sprint 5: Clinical Preservation (Days 18-20) — **P0**

| Task | Owner | Deliverable | Exit Criteria |
|------|-------|-------------|---------------|
| Drug/strength/dosage detector (`clinical/drugs.py`) | Clinical | `drugs.py` | Gazetteer (INN + India brands) + regex |
| Lab/vital/unit detector (`clinical/labs.py`) | Clinical | `labs.py` | LOINC-derived + patterns |
| Diagnosis/procedure detector (`clinical/diagnoses.py`) | Clinical | `diagnoses.py` | ICD-10 + eponyms (Parkinson's, Alzheimer's) |
| Doctor context detector (`clinical/doctors.py`) | Clinical | `doctors.py` | Dr./Doctor + clinical context |
| Medical veto integration (`clinical/veto.py`) | Clinical | `veto.py` | Span-level veto; adjacency re-check |
| Clinical preservation tests | Clinical | `test_clinical_preservation.py` | 0 clinical values corrupted; doctor names preserved |

**Sprint 5 Definition of Done:** Clinical fixture: 0% corruption; relative names redacted; doctor names preserved in context.

---

### Sprint 6: Output Security Gate & Reporting (Days 21-23) — **P0**

| Task | Owner | Deliverable | Exit Criteria |
|------|-------|-------------|---------------|
| Residual PII scanner (`output/residual_scan.py`) | Output | `residual_scan.py` | Detectors on output; any hit → fail |
| Canary checker (`output/canary.py`) | Output | `canary.py` | Scans for `LOCKMATE_CANARY_*` |
| Clinical integrity verifier (`output/clinical_check.py`) | Output | `clinical_check.py` | Pre/post medical span comparison |
| Schema validator (`output/schema_check.py`) | Output | `schema_check.py` | CSV/JSON/FHIR R4 valid |
| Filename/metadata scanner (`output/meta_check.py`) | Output | `meta_check.py` | No PII in output paths/keys |
| Pseudonym consistency checker (`output/pseudonym_check.py`) | Output | `pseudonym_check.py` | Same patient → same pseudonym in record + records.jsonl |
| Security gate orchestrator (`output/security_gate.py`) | Output | `security_gate.py` | All checks PASS; FAIL → quarantine |
| report.json generator (`output/report.py`) | Output | `report.py` | Exact schema per context.md §16.2 |
| records.jsonl generator (`output/records.py`) | Output | `records.py` | Exact schema per context.md §16.3 |
| Output pipeline (`output/pipeline.py`) | Output | `pipeline.py` | Atomic write of all three outputs |

**Sprint 6 Definition of Done:** `validate_output.py` passes on synthetic input (or self-validator); security gate catches injected violations.

---

### Sprint 7: Identity Resolution & Linkage (Days 24-27) — **P1**

| Task | Owner | Deliverable | Exit Criteria |
|------|-------|-------------|---------------|
| Blocking key generator (`linkage/blocking.py`) | Linkage | `blocking.py` | All blocking keys from context.md §11.2 |
| Candidate pair generator (`linkage/candidates.py`) | Linkage | `candidates.py` | Deduped; max pairs controlled |
| Pairwise scorer (`linkage/scoring.py`) | Linkage | `scoring.py` | Fellegi-Sunter features; configurable weights |
| Cannot-link constraints (`linkage/constraints.py`) | Linkage | `constraints.py` | Conflicting hard IDs → cannot_link |
| Conservative clusterer (`linkage/clustering.py`) | Linkage | `clustering.py` | Greedy + consistency check; no transitive closure |
| Canonical identity builder (`linkage/canonical.py`) | Linkage | `canonical.py` | Sorted reliable identifiers |
| Linkage pipeline (`linkage/pipeline.py`) | Linkage | `pipeline.py` | 500-record multi-hospital fixture; P/R/F1 measured |

**Sprint 7 Definition of Done:** Linkage precision ≥98%, recall ≥85%, false-merge <1%; null for uncertain.

---

### Sprint 8: Pseudonymization (Days 28-29) — **P1**

| Task | Owner | Deliverable | Exit Criteria |
|------|-------|-------------|---------------|
| Secret loader (`crypto/secret.py`) | Linkage | `secret.py` | Reads `RAKSHA_SECRET` from env; validates; never logs |
| HMAC pseudonym service (`crypto/pseudonym.py`) | Linkage | `pseudonym.py` | Domain separation; PSN-XXXX format; determinism |
| Date-shift derivation (`crypto/date_shift.py`) | Linkage | `date_shift.py` | Per-patient offset [-365, +365] from HMAC |
| Pseudonym injector (`crypto/injector.py`) | Linkage | `injector.py` | Injects into patient ID field per format |
| Pseudonym integration | Linkage | `linkage/pipeline.py` | Clusters → pseudonyms; sanitized records updated |

**Sprint 8 Definition of Done:** 3 runs same secret = identical pseudonyms; 2 runs different secrets = different pseudonyms.

---

### Sprint 9: Date & Age Transformations (Days 30-31) — **P1**

| Task | Owner | Deliverable | Exit Criteria |
|------|-------|-------------|---------------|
| Date field identifier (`privacy/date_fields.py`) | Privacy | `date_fields.py` | Finds all DATE-type PII + structured date fields |
| Date shifter (`privacy/date_shift.py`) | Privacy | `date_shift.py` | Applies per-patient offset; preserves intervals |
| Age generalizer (`privacy/age_bands.py`) | Privacy | `age_bands.py` | Bands per context.md §13.2; round down; 90+ ceiling |
| Privacy integration (`privacy/pipeline.py`) | Privacy | `pipeline.py` | Updates URM before serialization |

**Sprint 9 Definition of Done:** Intervals preserved exactly; age bands correct; different secrets → different shifts.

---

### Sprint 10: Location & Rare-Value Protection (Days 32-34) — **P1**

| Task | Owner | Deliverable | Exit Criteria |
|------|-------|-------------|---------------|
| Location gazetteer loader (`privacy/gazetteer.py`) | Privacy | `gazetteer.py` | Census 2011 CSV bundled; <100MB |
| Location generalizer (`privacy/location.py`) | Privacy | `location.py` | Village→district, PIN→3-digit, rare→state |
| Equivalence class builder (`privacy/equivalence.py`) | Privacy | `equivalence.py` | Groups by QI tuple; counts per class |
| Rare suppressor (`privacy/suppression.py`) | Privacy | `suppression.py` | Iterative: suppress rarest → generalize age → location |
| Attacker simulation (`redteam/attacker_sim.py`) | Red-Team | `attacker_sim.py` | Synthetic voter roll linkage; <5% unique re-ID |
| Privacy pipeline (`privacy/pipeline.py`) | Privacy | `pipeline.py` | Applies location + rare suppression; updates URM |

**Sprint 10 Definition of Done:** k-anonymity ≥5 for >95% records; attacker sim unique re-ID <5%; clinical utility >95%.

---

### Sprint 11: FHIR Hardening (Days 35-36) — **P1**

| Task | Owner | Deliverable | Exit Criteria |
|------|-------|-------------|---------------|
| FHIR reference scanner (`parsers/fhir_references.py`) | Ingestion | `fhir_references.py` | References, contained, extensions scanned |
| FHIR attachment handler (`parsers/fhir_attachments.py`) | Ingestion | `fhir_attachments.py` | PDF/image → quarantine; text → extract+scan |
| FHIR metadata scanner (`detection/fhir_meta.py`) | Detection | `fhir_meta.py` | meta.tag, meta.profile, meta.security |
| FHIR serializer validator (`output/fhir_validator.py`) | Output | `fhir_validator.py` | `fhir.resources` round-trip validation |
| FHIR integration test | Ingestion | `test_fhir_integration.py` | Complex Bundle → valid sanitized R4 |

**Sprint 11 Definition of Done:** Complex FHIR Bundle → valid sanitized R4; no PII in refs/extensions/attachments/meta.

---

### Sprint 12: Red-Team Evaluation (Days 37-39) — **P1**

| Task | Owner | Deliverable | Exit Criteria |
|------|-------|-------------|---------------|
| Adversarial fixture generator (`redteam/fixtures.py`) | Red-Team | `fixtures.py` | Generates all adversarial types |
| Canary injection test (`redteam/canary_test.py`) | Red-Team | `canary_test.py` | Zero canary leakage in output/logs/temp |
| False-merge test suite (`redteam/false_merge.py`) | Red-Team | `false_merge.py` | <1% false merge on ambiguous pairs |
| Medical corruption test (`redteam/medical_corruption.py`) | Red-Team | `medical_corruption.py` | 0% clinical corruption |
| Privacy attack evaluation (`redteam/privacy_attack.py`) | Red-Team | `privacy_attack.py` | Re-ID metrics documented |
| Performance profiling (`redteam/performance.py`) | Red-Team | `performance.py` | 2GB input < 900s, < 4GB RSS |
| Determinism verification (`redteam/determinism.py`) | Red-Team | `determinism.py` | 3 runs same secret = byte-identical |
| Secret rotation verification (`redteam/secret_rotation.py`) | Red-Team | `secret_rotation.py` | Different secrets → different pseudonyms/shifts |
| Resource limit enforcement (`redteam/resource_limits.py`) | Red-Team | `resource_limits.py` | Oversized/nested/bomb → quarantine |
| Security hardening review (`SECURITY_REVIEW.md`) | Red-Team | `SECURITY_REVIEW.md` | Bandit + semgrep clean |

**Sprint 12 Definition of Done:** All red-team tests pass; performance within limits; determinism verified; security review clean.

---

### Sprint 13: Performance Optimization (Days 40-41) — **P1**

| Task | Owner | Deliverable | Exit Criteria |
|------|-------|-------------|---------------|
| Profile hot paths | All | Bottleneck report | Top 5 consumers identified |
| Optimize blocking | Linkage | `blocking.py` | Candidate pairs reduced 50%+ |
| Vectorize detection | Detection | `engine.py` | Detection time -30% |
| Streaming serialization | Output | `serializer.py` | Peak RSS -25% |
| Parallel file processing | Ingestion | `intake/pipeline.py` | Intake time -40% (2 workers) |
| Memory cleanup | All | Per-module | No memory growth across files |

**Sprint 13 Definition of Done:** Full 2GB input → < 720s (12 min), < 3.2 GB RSS.

---

### Sprint 14: Frontend & Demo (Days 42-43) — **P2 (Optional)**

| Task | Owner | Deliverable | Exit Criteria |
|------|-------|-------------|---------------|
| Demo data curation | Frontend | `demo/data/` | 3 hospitals, 1 patient across scripts |
| Pipeline visualization | Frontend | `demo/app.py` | Stage progression, timings, highlights |
| Before/After viewer | Frontend | `demo/components/diff.py` | Side-by-side diff with highlights |
| Linkage explorer | Frontend | `demo/components/linkage.py` | Graph view of clusters |
| Privacy dashboard | Frontend | `demo/components/privacy.py` | k-anonymity, re-ID rate, clinical utility |
| Verifier panel | Frontend | `demo/components/verifier.py` | Runs validator, shows CONTRACT OK |
| 5-min demo script | Orchestrator | `DEMO_SCRIPT.md` | Matches context.md §23.3 timing |

**Sprint 14 Definition of Done:** Demo runs smoothly; all 5 minutes covered; no CLI dependency.

---

## 3. Cross-Phase Dependencies

```
Phase 0 ──→ Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4 ──→ Phase 5 ──→ Phase 6
                                                              │
                                                              ▼
Phase 7 ◄── Phase 8 ◄── Phase 9 ◄── Phase 10 ◄── Phase 11 ◄──┘
        │
        ▼
Phase 12 ◄── Phase 13 ◄── Phase 14
```

**Critical Path:** 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13

---

## 4. Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Organizer validator unavailable | High | Blocks official validation | Build self-validator from contract spec early (Sprint 6) |
| Practice dataset unavailable | High | No ground truth for tuning | Generate synthetic fixtures with known labels (Sprint 0) |
| Gazetteer licensing issues | Medium | Cannot bundle name/location data | Use public domain (Census 2011, Wikipedia lists); verify licenses |
| FHIR complexity underestimated | Medium | References/extensions leak PII | Deep traversal test suite; quarantine on validation fail |
| Performance targets missed | Medium | Disqualification | Profile from Sprint 2; streaming/blocking from Day 1 |
| Multilingual false merges | Medium | Privacy failure | Strict cannot-link; high threshold; cross-script test fixtures |
| Medical veto over-redaction | Low | Clinical corruption | Context window + role markers override veto; adversarial tests |

---

## 5. Team Communication Protocol

| Cadence | Meeting | Participants | Purpose |
|---------|---------|--------------|---------|
| Daily | Standup (15 min) | All agents | Progress, blockers, sync |
| Sprint boundary | Sprint Review (30 min) | All agents | Demo completed work; update roadmap |
| Sprint boundary | Retrospective (15 min) | All agents | Process improvements |
| Phase gate | Integration Checkpoint | Orchestrator + relevant agents | Verify checkpoint criteria (see engineering-strategy.md §9) |

---

## 6. Definition of Done (Per Sprint)

A sprint is **complete** only when:
- [ ] All tasks marked done with evidence (test output, file diffs)
- [ ] All unit tests pass (`pytest tests/unit/ -v`)
- [ ] Integration tests pass for completed phases
- [ ] Documentation updated (architecture.md, compliance matrix)
- [ ] No known P0/P1 bugs
- [ ] Orchestrator sign-off

---

## 7. Immediate Next Steps (Today)

1. **Initialize git** in project directory
2. **Create `raksha.toml`** with placeholder team name
3. **Create `main.py`** scaffold with CLI + secret reading
4. **Create `requirements.txt`** with pinned dependencies
5. **Create `config/policy.yaml`** with defaults
6. **Create `src/secret_wards/contracts.py`** with 12 dataclasses
7. **Run first smoke test:** `python main.py --input test_dir --output test_out`

---

**END OF DEVELOPMENT ROADMAP**