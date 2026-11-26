# LOCKMATE — Track 3 Compliance Matrix

**Source:** Official Yugaantar DevForge Track 3: "Secret Wards" Specification  
**Date:** 2026-11-26  
**Status:** Baseline — all requirements UNVERIFIED/MISSING

---

## Compliance Matrix Legend

| Status | Meaning |
|--------|---------|
| **ALIGNED** | Fully implemented and tested |
| **PARTIALLY ALIGNED** | Partially implemented, gaps remain |
| **MISSING** | Not implemented at all |
| **CONTRADICTORY** | Implementation conflicts with requirement |
| **UNVERIFIED** | Cannot verify (missing assets, code, or tests) |

| Priority | Meaning |
|----------|---------|
| **P0** | Mandatory for submission — blocks `CONTRACT OK` |
| **P1** | Required for competitive scoring — privacy, linkage, clinical |
| **P2** | Optional / demonstration / optimization |

---

## Section 1: Execution Environment Requirements

| # | Requirement | Category | LOCKMATE Component | Status | Required Implementation | Acceptance Test | Evidence | Priority |
|---|-------------|----------|-------------------|--------|------------------------|-----------------|----------|----------|
| 1.1 | Fully offline execution — no network access | Mandatory | All (pipeline, deps, gazetteers) | MISSING | Bundle all models/gazetteers; no network calls in code | Run in air-gapped env; verify no socket connections | — | P0 |
| 1.2 | CPU-only — no GPU/CUDA | Mandatory | All | MISSING | Use CPU-only libraries; no torch/tensorflow | `nvidia-smi` shows no process; imports succeed without CUDA | — | P0 |
| 1.3 | Maximum 2 CPUs | Mandatory | Pipeline orchestration | MISSING | `ProcessPoolExecutor(max_workers=2)` for parallel file processing | `htop` shows ≤2 CPU cores used | — | P0 |
| 1.4 | Maximum 4 GB RAM | Mandatory | All (streaming, memory mgmt) | MISSING | Streaming parsers; explicit `del`/`gc.collect()`; monitor RSS | Peak RSS < 4 GB on 2 GB input | — | P0 |
| 1.5 | Maximum 15 minutes (900s) wall-clock | Mandatory | Pipeline orchestration | MISSING | Optimized blocking, vectorized detection, streaming serialization | Full 2 GB input completes < 900s | — | P0 |
| 1.6 | Linux platform (organizer eval env) | Mandatory | All | UNVERIFIED | Code must be Linux-compatible; no Windows-only paths | Test on Linux CI | — | P0 |

---

## Section 2: AI/ML Restrictions

| # | Requirement | Category | LOCKMATE Component | Status | Required Implementation | Acceptance Test | Evidence | Priority |
|---|-------------|----------|-------------------|--------|------------------------|-----------------|----------|----------|
| 2.1 | No hosted LLMs | Prohibited | Detection, Clinical, Linkage | MISSING | Rule-based, gazetteers, classical ML only | `grep -r "openai\|anthropic\|huggingface" src/` → empty | — | P0 |
| 2.2 | No local LLMs | Prohibited | Detection, Clinical, Linkage | MISSING | No transformers, no llama.cpp, no ollama | No LLM imports in requirements.txt | — | P0 |
| 2.3 | No distilled LLMs | Prohibited | Detection, Clinical, Linkage | MISSING | No distilled models | Same as 2.2 | — | P0 |
| 2.4 | No generative models | Prohibited | Detection, Clinical, Linkage | MISSING | No GANs, VAEs, diffusion | No generative model imports | — | P0 |
| 2.5 | No pretrained transformers >50M params | Prohibited | Detection (CRF optional) | MISSING | If CRF used: `sklearn-crfsuite` (<1M params); declare in README | Model size check; README declaration | — | P0 |
| 2.6 | Permitted: rules, gazetteers, classical ML, CRF, small self-trained ≤50M params | Permitted | Detection, Clinical, Linkage | MISSING | Implement per context.md §9, §10, §11 | All detection via permitted methods | — | P0 |
| 2.7 | Every model declared in README | Mandatory | README | MISSING | Document model type, size, training source, purpose | README contains model declarations | — | P0 |

---

## Section 3: Configuration & CLI

| # | Requirement | Category | LOCKMATE Component | Status | Required Implementation | Acceptance Test | Evidence | Priority |
|---|-------------|----------|-------------------|--------|------------------------|-----------------|----------|----------|
| 3.1 | `raksha.toml` exists with exact keys | Mandatory | Root config | MISSING | Create file with `[submission] name, setup, run` | File exists; keys match spec exactly | — | P0 |
| 3.2 | `raksha.toml` `name` = team name | Mandatory | Root config | MISSING | Team provides name; placeholder documented | Non-empty string | — | P0 |
| 3.3 | `raksha.toml` `setup` = `pip install -r requirements.txt` | Mandatory | Root config | MISSING | Exact string | Diff against spec | — | P0 |
| 3.4 | `raksha.toml` `run` = `python main.py --input {input} --output {output}` | Mandatory | Root config | MISSING | Exact string with placeholders | Diff against spec | — | P0 |
| 3.5 | `RAKSHA_SECRET` env var read at runtime | Mandatory | `main.py`, `crypto/secret.py` | MISSING | `os.environ["RAKSHA_SECRET"]`; validate ≥32 bytes; never log/write | Secret read from env; not in logs/disk | — | P0 |
| 3.6 | CLI: `python main.py --input <dir> --output <dir>` | Mandatory | `main.py` | MISSING | `argparse` with two required positional args | Help shows correct usage; runs with args | — | P0 |
| 3.7 | Handle relative and absolute paths | Mandatory | `main.py`, intake | MISSING | `Path.resolve()` for both | Test with relative/absolute paths | — | P0 |
| 3.8 | No additional required flags | Mandatory | `main.py` | MISSING | Only `--input` and `--output` (or positional) | No other required args | — | P0 |

---

## Section 4: Required Output Structure

| # | Requirement | Category | LOCKMATE Component | Status | Required Implementation | Acceptance Test | Evidence | Priority |
|---|-------------|----------|-------------------|--------|------------------------|-----------------|----------|----------|
| 4.1 | Output dir contains `sanitized/`, `report.json`, `records.jsonl` | Mandatory | Output pipeline | MISSING | Atomic write of all three | `ls output/` shows all three | — | P0 |
| 4.2 | `sanitized/` preserves input folder hierarchy | Mandatory | Serializer, Namer | MISSING | Recreate relative paths under `sanitized/` | Directory structure matches input | — | P0 |
| 4.3 | `sanitized/` preserves filenames unless PII-bearing | Mandatory | Filename sanitizer | MISSING | Detect PII in filename; rename to SHA-256 prefix + ext | PII filenames renamed; others preserved | — | P0 |
| 4.4 | `sanitized/` preserves formats (CSV→CSV, TSV→TSV, JSON→JSON, FHIR→valid R4) | Mandatory | Serializer | MISSING | Format-specific serializers | Output files parse as same format | — | P0 |
| 4.5 | `sanitized/` UTF-8 encoding only | Mandatory | Serializer, Writer | MISSING | Write all outputs as UTF-8 | `file -bi` shows UTF-8 | — | P0 |
| 4.6 | Never copy raw input files to sanitized output | Mandatory | Pipeline, Quarantine | MISSING | Every file processed or quarantined | No byte-identical input/output pairs | — | P0 |
| 4.7 | Quarantine files that cannot be safely processed | Mandatory | Quarantine, Security gate | MISSING | Unsupported/corrupt/residual PII → `sanitized/quarantined/` | Quarantined files in output with reason | — | P0 |
| 4.8 | `report.json` entries keyed by SHA-256 of input file | Mandatory | Report generator | MISSING | Hash each input file; use as key | JSON keys are 64-char hex | — | P0 |
| 4.9 | `report.json` per-file fields: `output_path`, `status`, `quarantine_reason`, `processing_duration_ms`, `peak_memory_mb` | Mandatory | Report generator | MISSING | Track metrics per file during pipeline | All fields present per entry | — | P0 |
| 4.10 | `report.json` aggregate totals: `files_total`, `files_sanitized`, `files_quarantined`, `records_processed`, `identifiers_detected`, `records_linked`, `records_generalized`, `records_suppressed`, `records_quarantined` | Mandatory | Report generator | MISSING | Accumulate counts across all files | Totals match actual pipeline results | — | P0 |
| 4.11 | `report.json` timing: `seconds` (total) | Mandatory | Report generator | MISSING | Wall-clock time for full pipeline | `timing.seconds` > 0 | — | P0 |
| 4.12 | `report.json` resources: `peak_rss_mb` | Mandatory | Report generator | MISSING | Track peak RSS via `psutil` or `resource` | `resources.peak_rss_mb` > 0 | — | P0 |
| 4.13 | `records.jsonl` one line per patient record | Mandatory | Records generator | MISSING | Emit one JSONL line per sanitized record | Line count = records in sanitized output | — | P0 |
| 4.14 | `records.jsonl` fields: `file` (relative path), `loc` (location), `patient` (pseudonym or null) | Mandatory | Records generator | MISSING | Map each record to its pseudonym | All three fields present | — | P0 |
| 4.15 | `loc` conventions: CSV/TSV `row:N` (0-indexed), JSON Pointer, Text/FHIR `doc` | Mandatory | Records generator | MISSING | Format-specific location encoding | Valid per format | — | P0 |
| 4.16 | Same patient → same pseudonym across all files | Mandatory | Linkage, Pseudonym, Records | MISSING | Cluster → canonical identity → HMAC pseudonym | Pseudonym consistency check passes | — | P0 |
| 4.17 | Pseudonym appears inside sanitized record | Mandatory | Pseudonym injector, Serializer | MISSING | Inject `PSN-XXXX` into patient ID field | Grep finds pseudonym in sanitized files | — | P0 |
| 4.18 | Uncertain identity → `null` (conservative) | Mandatory | Linkage, Records | MISSING | Clusters below threshold → `patient: null` | Null pseudonyms for uncertain clusters | — | P0 |
| 4.19 | Never force match to increase linkage counts | Mandatory | Linkage | MISSING | High threshold, cannot-link, no transitive closure | False-merge rate < 1% on fixtures | — | P1 |

---

## Section 5: Validation Contract

| # | Requirement | Category | LOCKMATE Component | Status | Required Implementation | Acceptance Test | Evidence | Priority |
|---|-------------|----------|-------------------|--------|------------------------|-----------------|----------|----------|
| 5.1 | Official validator command: `python3 validate_output.py --input dev/input --output my_output/` | Mandatory | Validation | UNVERIFIED | Obtain validator from organizers; run on output | Validator runs without error | — | P0 |
| 5.2 | Success output: `CONTRACT OK` | Mandatory | Validation | UNVERIFIED | Pipeline produces valid output | Stdout contains exact string | — | P0 |
| 5.3 | Do not claim validation without running official validator | Mandatory | Documentation | MISSING | Clear labeling: internal vs official validation | No false claims in docs/README | — | P0 |

---

## Section 6: Evaluation Criteria (Scoring Dimensions)

| # | Requirement | Category | LOCKMATE Component | Status | Required Implementation | Acceptance Test | Evidence | Priority |
|---|-------------|----------|-------------------|--------|------------------------|-----------------|----------|----------|
| 6.1 | **Privacy**: Direct identifier leakage = 0 | Evaluation | Detection, Security gate | MISSING | Multi-layer detection + second-pass + independent gate | Zero PII in output/logs/temp | — | P0 |
| 6.2 | **Privacy**: Quasi-identifier uniqueness minimized | Evaluation | Privacy transforms, Attacker sim | MISSING | Date shift, age bands, location generalization, rare suppression | Attacker sim unique re-ID < 5% | — | P1 |
| 6.3 | **Privacy**: Re-identification risk measured & reported | Evaluation | Attacker simulation | MISSING | Synthetic voter roll linkage; before/after metrics | Risk reduction documented | — | P1 |
| 6.4 | **Detection**: Entity-level precision/recall | Evaluation | Detection engine | MISSING | Rule-based + gazetteer + transliteration + CRF (conditional) | P≥90%, R≥95% on labeled fixtures | — | P1 |
| 6.5 | **Detection**: Span-level precision/recall | Evaluation | Detection engine | MISSING | Offset-map aware replacement | Span F1 measured | — | P1 |
| 6.6 | **Detection**: False positives on clinical content | Evaluation | Clinical preservation, Medical veto | MISSING | Span-level medical veto (not blanket whitelist) | Clinical corruption = 0% | — | P0 |
| 6.7 | **Clinical Preservation**: Medicines, dosages, frequencies, diagnoses, vitals, labs, units, stay durations preserved | Evaluation | Clinical detectors, Medical veto | MISSING | Gazetteers (INN, LOINC, ICD-10) + regex + context | >95% clinical values preserved | — | P0 |
| 6.8 | **Identity Linkage**: Pairwise precision/recall/F1 | Evaluation | Linkage pipeline | MISSING | Conservative clustering, cannot-link, no transitive closure | Precision≥98%, Recall≥85%, F1 measured | — | P1 |
| 6.9 | **Identity Linkage**: False-merge rate | Evaluation | Linkage, Cannot-link | MISSING | High threshold, conflicting ID constraints | False-merge < 1% | — | P0 |
| 6.10 | **Identity Linkage**: Correct null assignment | Evaluation | Linkage, Conservative clustering | MISSING | Uncertain → `patient: null` | Null rate measured on ambiguous fixtures | — | P1 |
| 6.11 | **Output Quality**: Format validity (CSV/JSON/FHIR R4) | Evaluation | Serializer, Schema validator | MISSING | `fhir.resources` validation for FHIR | All output files parse/validate | — | P0 |
| 6.12 | **Output Quality**: `report.json` correctness | Evaluation | Report generator | MISSING | Exact schema, hash keys, accurate totals | Schema validation passes | — | P0 |
| 6.13 | **Output Quality**: `records.jsonl` correctness | Evaluation | Records generator | MISSING | Exact schema, location conventions, pseudonym consistency | Schema validation passes | — | P0 |
| 6.14 | **Output Quality**: Filename safety | Evaluation | Filename sanitizer, Meta scanner | MISSING | No PII in output paths | Scan output paths for PII | — | P0 |
| 6.15 | **Output Quality**: Metadata safety | Evaluation | Structured scanner, Meta scanner | MISSING | No PII in JSON keys, FHIR meta | Scan output metadata | — | P0 |
| 6.16 | **Output Quality**: Quarantine correctness | Evaluation | Quarantine, Security gate | MISSING | Unsafe files quarantined with reason | Quarantine entries in report.json | — | P0 |
| 6.17 | **Reliability**: Runtime < 15 min | Evaluation | Pipeline, Performance | MISSING | Optimized blocking, streaming, vectorization | Measured on max input | — | P0 |
| 6.18 | **Reliability**: Peak RSS < 4 GB | Evaluation | Pipeline, Memory mgmt | MISSING | Streaming parsers, explicit cleanup | Measured on max input | — | P0 |
| 6.19 | **Reliability**: Offline execution verified | Evaluation | All | MISSING | No network calls, all deps bundled | Run in air-gapped env | — | P0 |
| 6.20 | **Reliability**: Crash rate = 0 | Evaluation | Pipeline, Exception handling | MISSING | Fail-safe: quarantine on error, continue | No unhandled exceptions | — | P0 |
| 6.21 | **Reliability**: Deterministic sanitized content | Evaluation | Pipeline, Pseudonym, Date shift | MISSING | Sorted file iteration, fixed seeds, HMAC determinism | 3 runs same secret = byte-identical | — | P0 |
| 6.22 | **Reliability**: Different secret → different pseudonyms/shifts | Evaluation | Pseudonym, Date shift | MISSING | HMAC with secret, domain separation | 2 runs different secrets → different privacy | — | P0 |
| 6.23 | **Reliability**: Temporary file cleanup | Evaluation | Temp handling, Security | MISSING | `tempfile.mkstemp()`, AES-GCM encrypt, secure delete | No temp files remain after run | — | P0 |

---

## Section 7: Functional Requirements (Detailed)

### A. Ingestion

| # | Requirement | Category | Component | Status | Implementation | Test | Priority |
|---|-------------|----------|-----------|--------|----------------|------|----------|
| 7.A.1 | CSV ingestion | Mandatory | `parsers/csv_parser.py` | MISSING | Auto-delimiter, header inference, quote handling, shifted columns | Parse CSV/TSV with various delimiters | P0 |
| 7.A.2 | TSV ingestion | Mandatory | `parsers/csv_parser.py` | MISSING | Tab delimiter detection | Parse TSV files | P0 |
| 7.A.3 | JSON ingestion | Mandatory | `parsers/json_parser.py` | MISSING | Schema-agnostic walk, nested objects/arrays, streaming | Parse nested JSON, large files | P0 |
| 7.A.4 | FHIR R4 ingestion | Mandatory | `parsers/fhir_parser.py` | MISSING | `fhir.resources` validation, references, extensions, contained, attachments | Parse Bundle, Patient, Observation; invalid → quarantine | P0 |
| 7.A.5 | Plain text ingestion | Mandatory | `parsers/text_parser.py` | MISSING | Encoding detection, line/paragraph segmentation | Parse UTF-8/UTF-16/CP1252 text | P0 |
| 7.A.6 | Encoding detection | Mandatory | `intake/encoding.py` | MISSING | `charset-normalizer` primary; no Latin-1 fallback | Detect UTF-8/BOM, UTF-16, CP1252; binary → quarantine | P0 |
| 7.A.7 | Broken/truncated files | Mandatory | All parsers + quarantine | MISSING | Graceful parse error → quarantine with reason | Malformed files quarantined | P0 |
| 7.A.8 | Unsupported formats | Mandatory | Classifier + quarantine | MISSING | Extension + content sniffing; UNKNOWN → quarantine | PDF/image/binary quarantined | P0 |
| 7.A.9 | Shifted/inconsistent columns | Mandatory | CSV parser | MISSING | Content-based column matching, not position-only | Shifted columns still parsed correctly | P0 |
| 7.A.10 | Safe parsing & quarantine | Mandatory | Intake pipeline | MISSING | Resource limits, symlink check, path traversal block | Symlink/oversize/decompression bomb quarantined | P0 |

### B. Multilingual PII Detection

| # | Requirement | Category | Component | Status | Implementation | Test | Priority |
|---|-------------|----------|-----------|--------|----------------|------|----------|
| 7.B.1 | English PII detection | Mandatory | `detection/identifiers.py`, `detection/names.py` | MISSING | Regex + gazetteer + context | English fixtures | P0 |
| 7.B.2 | Devanagari Hindi PII detection | Mandatory | `detection/normalize.py`, `detection/names.py` | MISSING | NFC, Devanagari digit→ASCII, gazetteer (Devanagari) | Hindi fixtures | P0 |
| 7.B.3 | Hinglish PII detection | Mandatory | `detection/names.py`, `detection/transliterate.py` | MISSING | Transliteration + gazetteer + context | Hinglish fixtures | P0 |
| 7.B.4 | Transliteration variants | Mandatory | `detection/transliterate.py`, `detection/gazetteer.py` | MISSING | `indic-transliteration` → IAST → Latin; Double Metaphone | Mohammad/Mohammed/मोहम्मद matched | P0 |
| 7.B.5 | Indian name structures | Mandatory | `detection/names.py` | MISSING | Honorifics, patronymics, surname-first, initials | Name structure fixtures | P0 |
| 7.B.6 | Initials and surname-first names | Mandatory | `detection/names.py` | MISSING | Pattern: `R. Sharma`, `Sharma, Rahul` | Initial/surname-first fixtures | P0 |
| 7.B.7 | Honorifics: ji, sahab, didi | Mandatory | `detection/names.py` | MISSING | Hindi honorifics in trigger detector | `Rahul ji`, `Sharma sahab` detected | P0 |
| 7.B.8 | S/o, D/o, W/o | Mandatory | `detection/names.py` | MISSING | Relationship markers in trigger detector | `S/o Rahul` → relative detected | P0 |
| 7.B.9 | Aadhaar-like IDs, ABHA, UHID, MRN, PAN, insurance IDs | Mandatory | `detection/identifiers.py` | MISSING | Verhoeff (Aadhaar), format validation (PAN/ABHA), context (UHID/MRN) | All ID types detected with validation | P0 |
| 7.B.10 | Indian phone number formats | Mandatory | `detection/identifiers.py` | MISSING | `phonenumbers` + regex; +91/0 prefix; 10 digits 6-9; Devanagari digits | All Indian phone formats | P0 |
| 7.B.11 | Names in structured data and free text | Mandatory | `detection/structured.py`, `detection/names.py` | MISSING | Scan headers, JSON keys, FHIR elements, filenames + free text | PII in all locations detected | P0 |

### C. Contextual Disambiguation

| # | Requirement | Category | Component | Status | Implementation | Test | Priority |
|---|-------------|----------|-----------|--------|----------------|------|----------|
| 7.C.1 | C/O Ramesh vs C/O fever | Mandatory | `detection/names.py`, `clinical/veto.py` | MISSING | Symptom gazetteer distinguishes clinical "C/O" | `C/O fever` preserved, `C/O Ramesh` → relative | P0 |
| 7.C.2 | Dr. Ramesh vs relative Ramesh | Mandatory | `clinical/doctors.py`, `clinical/veto.py` | MISSING | `Dr.`/`Doctor` + clinical context → preserve | `Dr. Ramesh prescribed` preserved, `Ramesh` (patient) redacted | P0 |
| 7.C.3 | Medicines and dosage expressions | Mandatory | `clinical/drugs.py`, `clinical/veto.py` | MISSING | Gazetteer (INN + India brands) + regex for strengths/frequencies | `Dolo 650 BD`, `5 mg`, `TDS` preserved | P0 |
| 7.C.4 | 1-0-1 and similar dosage patterns | Mandatory | `clinical/drugs.py` | MISSING | Regex for frequency patterns | `1-0-1`, `1+0+1` preserved | P0 |
| 7.C.5 | Disease names (Parkinson's, Alzheimer's, etc.) | Mandatory | `clinical/diagnoses.py`, `clinical/veto.py` | MISSING | ICD-10 derived list + eponyms; always preserve | `Parkinson's disease` preserved | P0 |
| 7.C.6 | Clinical terminology resembling personal identifiers | Mandatory | `clinical/veto.py` | MISSING | Span-level medical veto (not blanket whitelist) | Clinical terms never redacted | P0 |

### D. Identity Resolution

| # | Requirement | Category | Component | Status | Implementation | Test | Priority |
|---|-------------|----------|-----------|--------|----------------|------|----------|
| 7.D.1 | Cross-file identity resolution | Mandatory | `linkage/pipeline.py` | MISSING | Process all records from all files together | Multi-file linkage | P0 |
| 7.D.2 | Cross-hospital identity resolution (4 hospitals) | Mandatory | `linkage/pipeline.py` | MISSING | Same pipeline handles all hospitals | 4-hospital fixture | P1 |
| 7.D.3 | Cross-script matching | Mandatory | `linkage/blocking.py`, `detection/transliterate.py` | MISSING | Transliteration + Double Metaphone blocking keys | Hindi↔Latin name matching | P1 |
| 7.D.4 | Blocking | Mandatory | `linkage/blocking.py` | MISSING | Normalized name, transliterated, Double Metaphone, phone, IDs, DOB, geography | Blocking reduces pairs effectively | P0 |
| 7.D.5 | Fuzzy and phonetic matching | Mandatory | `linkage/scoring.py`, `detection/transliterate.py` | MISSING | Jaro-Winkler, token Jaccard, Double Metaphone match | Phonetic similarity scored | P1 |
| 7.D.6 | Confidence scoring | Mandatory | `linkage/scoring.py` | MISSING | Fellegi-Sunter inspired weighted evidence | Scores computed per feature | P0 |
| 7.D.7 | Cannot-link constraints | Mandatory | `linkage/constraints.py` | MISSING | Conflicting Aadhaar/ABHA/PAN/DOB/gender → cannot_link | Conflicting IDs prevent merge | P0 |
| 7.D.8 | Conservative clustering | Mandatory | `linkage/clustering.py` | MISSING | Greedy by score; cluster consistency check; no transitive closure | Chain A-B, B-C, A-C low → no merge | P0 |
| 7.D.9 | Avoid transitive over-merging | Mandatory | `linkage/clustering.py` | MISSING | Consistency check: all cross-pairs in cluster meet threshold | Transitive chains not auto-merged | P0 |
| 7.D.10 | Uncertain identities → `patient: null` | Mandatory | `linkage/clustering.py`, `output/records.py` | MISSING | Below threshold → singleton with null pseudonym | Null pseudonyms for uncertain | P0 |

### E. Pseudonymization

| # | Requirement | Category | Component | Status | Implementation | Test | Priority |
|---|-------------|----------|-----------|--------|----------------|------|----------|
| 7.E.1 | Stable patient pseudonyms | Mandatory | `crypto/pseudonym.py` | MISSING | HMAC-SHA256 with secret; deterministic | Same patient+same secret = same pseudonym | P0 |
| 7.E.2 | Keyed HMAC, never plain hashing | Mandatory | `crypto/pseudonym.py` | MISSING | `hmac.HMAC(secret, SHA256)` | No `hashlib.sha256()` on raw identity | P0 |
| 7.E.3 | Same patient → same pseudonym across files/hospitals | Mandatory | `linkage/canonical.py`, `crypto/pseudonym.py` | MISSING | Canonical identity from cluster → HMAC | Cross-file pseudonym consistency | P0 |
| 7.E.4 | Different secret → different pseudonyms | Mandatory | `crypto/pseudonym.py` | MISSING | Secret is HMAC key | Secret rotation test passes | P0 |
| 7.E.5 | Pseudonym appears inside sanitized record | Mandatory | `crypto/injector.py`, `output/serializer.py` | MISSING | Inject into patient ID field per format | Pseudonym in sanitized output | P0 |
| 7.E.6 | `RAKSHA_SECRET` never written to disk/logs | Mandatory | `crypto/secret.py`, logging | MISSING | Read from env; store in memory only; no `__repr__` | Grep finds no secret in output | P0 |

### F. Privacy Transformation

| # | Requirement | Category | Component | Status | Implementation | Test | Priority |
|---|-------------|----------|-----------|--------|----------------|------|----------|
| 7.F.1 | Per-patient date shifting | Mandatory | `privacy/date_shift.py`, `crypto/date_shift.py` | MISSING | HMAC-derived offset [-365, +365] per patient | All dates for patient shifted consistently | P0 |
| 7.F.2 | Preserve exact length of stay | Mandatory | `privacy/date_shift.py` | MISSING | Shift admission & discharge by same offset | LOS unchanged after shift | P0 |
| 7.F.3 | Preserve date relationships | Mandatory | `privacy/date_shift.py` | MISSING | Chronological order maintained | Date order preserved | P0 |
| 7.F.4 | Age banding contains true age | Mandatory | `privacy/age_bands.py` | MISSING | Bands per context.md §13.2; always round down | True age ∈ reported band | P0 |
| 7.F.5 | Location generalization | Mandatory | `privacy/location.py`, `privacy/gazetteer.py` | MISSING | Village→district, city→district, PIN→3-digit, rare→state | Generalization hierarchy applied | P0 |
| 7.F.6 | PIN code generalization | Mandatory | `privacy/location.py` | MISSING | Truncate to 3-digit prefix | 6-digit PIN → 3-digit | P0 |
| 7.F.7 | Rare-value suppression | Mandatory | `privacy/suppression.py`, `privacy/equivalence.py` | MISSING | k-anonymity diagnostic (k=5); iterative suppression | Equivalence classes ≥5 after | P1 |
| 7.F.8 | Privacy-utility trade-off measurement | Mandatory | `redteam/attacker_sim.py`, `redteam/privacy_attack.py` | MISSING | Clinical utility >95%; attacker sim <5% re-ID | Metrics reported | P1 |
| 7.F.9 | Re-identification risk evaluation | Mandatory | `redteam/attacker_sim.py` | MISSING | Synthetic voter roll linkage simulation | Risk reduction documented | P1 |

### G. Hidden Leakage Protection

| # | Requirement | Category | Component | Status | Implementation | Test | Priority |
|---|-------------|----------|-----------|--------|----------------|------|----------|
| 7.G.1 | File contents sanitized | Mandatory | Detection, Transform, Serializer | MISSING | All PII spans replaced | No PII in output files | P0 |
| 7.G.2 | JSON keys sanitized | Mandatory | `detection/structured.py`, `output/meta_check.py` | MISSING | Scan and redact PII in JSON keys | No PII in output JSON keys | P0 |
| 7.G.3 | CSV headers sanitized | Mandatory | `detection/structured.py` | MISSING | Scan and redact PII in headers | No PII in output CSV headers | P0 |
| 7.G.4 | Filenames sanitized | Mandatory | `output/namer.py`, `output/meta_check.py` | MISSING | PII in filename → SHA-256 prefix rename | No PII in output paths | P0 |
| 7.G.5 | Metadata sanitized | Mandatory | `detection/fhir_meta.py`, `output/meta_check.py` | MISSING | Scan FHIR meta, JSON metadata | No PII in output metadata | P0 |
| 7.G.6 | Attachments handled | Mandatory | `parsers/fhir_attachments.py` | MISSING | Base64 PDF/image → quarantine; text/plain → extract+scan | Attachments safe | P0 |
| 7.G.7 | Temporary files safe | Mandatory | `intake/pipeline.py`, `crypto/secret.py` | MISSING | Minimize disk; AES-GCM encrypt if needed; secure delete | No PII in temp files | P0 |
| 7.G.8 | Logs PII-free | Mandatory | Logging, `output/canary.py` | MISSING | Structured JSON logging; redact via detector | No raw text in logs | P0 |
| 7.G.9 | Exceptions PII-free | Mandatory | Exception handling | MISSING | Catch all; log hash only; quarantine | No PII in exception traces | P0 |
| 7.G.10 | Reports PII-free | Mandatory | `output/report.py`, `output/records.py` | MISSING | No original filenames, no raw PII in fields | Scan report.json/records.jsonl | P0 |
| 7.G.11 | Unsafe files quarantined, never copied through | Mandatory | Quarantine, Security gate | MISSING | Gate FAIL → quarantine entire file | Quarantined files in output | P0 |

### H. Security

| # | Requirement | Category | Component | Status | Implementation | Test | Priority |
|---|-------------|----------|-----------|--------|----------------|------|----------|
| 7.H.1 | Encryption of raw/intermediate data at rest | Mandatory | Temp handling | MISSING | AES-GCM for temp files; key from secret + domain | Temp files encrypted | P0 |
| 7.H.2 | Keys separated from encrypted data | Mandatory | `crypto/secret.py` | MISSING | Key in memory only; never written with data | Key not in temp/output | P0 |
| 7.H.3 | PII-free logging | Mandatory | Logging, `output/canary.py` | MISSING | Structured JSON; hashes/counts only | No raw PII in logs | P0 |
| 7.H.4 | Secure temporary-file handling | Mandatory | Temp handling | MISSING | `tempfile.mkstemp()` with `O_EXCL`; cleanup in `finally` | No temp leaks | P0 |
| 7.H.5 | Canary detection | Mandatory | `output/canary.py`, `redteam/canary_test.py` | MISSING | Inject `LOCKMATE_CANARY_<UUID>`; scan output/logs/temp | Zero canary leakage | P0 |
| 7.H.6 | Fail-safe processing | Mandatory | Pipeline, Exception handling | MISSING | Uncertain → quarantine; never silent pass | All errors quarantined | P0 |
| 7.H.7 | No raw data leakage | Mandatory | All | MISSING | Comprehensive: output, logs, temp, exceptions, reports | Full leakage scan passes | P0 |

---

## Summary Statistics

| Status | Count | Percentage |
|--------|-------|------------|
| ALIGNED | 0 | 0% |
| PARTIALLY ALIGNED | 0 | 0% |
| MISSING | 180+ | ~95% |
| CONTRADICTORY | 0 | 0% |
| UNVERIFIED | 10+ | ~5% |

**Total Requirements Tracked:** ~190  
**Mandatory (P0) Requirements:** ~120  
**P1 Requirements:** ~50  
**P2 Requirements:** ~20

---

## Next Actions

1. **Immediate (P0):** Create `raksha.toml`, `main.py`, `requirements.txt`, `src/secret_wards/contracts.py`
2. **Phase 0 Deliverables:** `REPO_INVENTORY.md`, `CONTRACT_CHECKLIST.md`, `ASSET_REPORT.md`, `BACKLOG.md`
3. **Obtain Organizer Assets:** Request `validate_output.py` and `dev/input/` from organizers
4. **Begin Phase 1:** Implement all 12 dataclasses in `contracts.py`
5. **Begin Phase 2:** Implement intake and parsing modules

---

**This matrix will be updated after each implementation phase.** Status changes from MISSING → PARTIALLY ALIGNED → ALIGNED as components are built and tested.