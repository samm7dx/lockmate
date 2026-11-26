# LOCKMATE — Project Context (Single Source of Truth)

**Document Status:** Authoritative reference for all AI coding agents  
**Track:** Yugaantar DevForge — Track 3: Secret Wards  
**Product:** LOCKMATE — Offline Healthcare Privacy Firewall  
**Last Updated:** 2026-11-26

---

## 1. Project Identity and Objective

LOCKMATE is an offline, CPU-only privacy firewall that ingests fragmented, multilingual Indian hospital records (CSV, TSV, JSON, plain text, FHIR R4), removes all personal identifiers, links records belonging to the same patient across hospitals/scripts/formats using conservative identity resolution, applies deterministic pseudonymization and quasi-identifier protection, and emits fully de-identified outputs that satisfy the organizer's exact contract.

**Core Objective:** Remove identities. Preserve medicine. Defeat linkage attacks.

**Success Definition:** The pipeline executes offline within 15 minutes / 4 GB RAM / 2 CPUs, produces `output/sanitized/`, `output/report.json`, `output/records.jsonl` that pass `python3 validate_output.py --input dev/input --output my_output/` with `CONTRACT OK`, and demonstrates measurable privacy improvement without clinical data corruption.

---

## 2. Product Vision and Problem Statement

Indian healthcare data exists in fragmented, multilingual records across hospitals. Direct identifiers (names, phones, Aadhaar, ABHA, PAN, UHID/MRN) and quasi-identifiers (dates, ages, locations, rare diagnoses) enable re-identification when combined with external datasets (voter rolls, public records). Simple name masking fails because:
- Names appear in multiple scripts (Devanagari, Latin, Hinglish)
- Relatives' names (`S/o`, `D/o`, `W/o`, `C/O`) are often recorded
- Doctors' names must be preserved where clinically relevant
- Medication names (Dolo 650, Parkinson's) resemble person names
- Identifiers span structured fields, unstructured notes, filenames, and metadata

LOCKMATE solves this through layered detection, contextual medical preservation, cross-script identity resolution, cryptographic pseudonymization, and attacker-aware quasi-identifier generalization — all verifiable through independent output validation.

---

## 3. Hackathon Track and Official Requirements

### 3.1 Track
**Yugaantar DevForge — Track 3: Secret Wards**

### 3.2 Execution Environment (Mandatory)
| Constraint | Requirement |
|------------|-------------|
| Network | **None** — fully offline execution |
| Compute | **CPU only** — no GPU |
| CPU Limit | **2 CPUs** maximum |
| Memory Limit | **4 GB RAM** maximum |
| Time Limit | **15 minutes** maximum wall-clock |
| Platform | Linux (organizer evaluation environment) |

### 3.3 AI/ML Restrictions (Mandatory)
**Prohibited:**
- Hosted LLMs
- Local LLMs
- Distilled LLMs
- Generative models
- Pretrained transformers **> 50 million parameters**

**Permitted:**
- Rule-based NLP
- Gazetteers and dictionaries
- Classical ML (CRF, SVM, logistic regression, decision trees)
- Small self-trained models **≤ 50M parameters** (must be declared in README)
- Phonetic algorithms (Double Metaphone, Soundex)
- Transliteration libraries

### 3.4 Required Configuration
**File:** `raksha.toml` (exact name, do not rename for branding)
```toml
[submission]
name = "your-team-name"
setup = "pip install -r requirements.txt"
run = "python main.py --input {input} --output {output}"
```

**Environment Variable:** `RAKSHA_SECRET`
- Must be read at runtime
- **Never** hardcode, print, log, write to disk, or expose in any output
- Used as HMAC key for pseudonymization and date-shift derivation

### 3.5 Required CLI Interface
```bash
python main.py --input <input_directory> --output <output_directory>
```
- Single entry point
- No additional required flags
- Must handle relative and absolute paths

### 3.6 Required Output Structure
```
output/
├── sanitized/
│   ├── <preserved directory structure>
│   └── quarantined/           # Unsafe files go here
├── report.json                # One entry per input file (by SHA-256)
└── records.jsonl              # One line per patient record
```

#### 3.6.1 Sanitized Files
- Preserve original directory structure where appropriate
- Preserve supported formats: CSV→CSV, TSV→TSV, JSON→JSON, FHIR→valid FHIR R4
- UTF-8 encoding only
- Rename PII-bearing filenames
- **Never** copy raw input files to sanitized output
- Quarantine files that cannot be safely processed

#### 3.6.2 report.json
Each entry keyed by **SHA-256 of input file** (not filename).

Required fields per entry:
- `output_path` (string or null)
- `status`: `"sanitized"` or `"quarantined"`
- `quarantine_reason` (string, when applicable)
- `processing_duration_ms` (integer)
- `peak_memory_mb` (integer)

Required aggregate totals (top-level):
| Field | Description |
|-------|-------------|
| `files_total` | Total input files discovered |
| `files_sanitized` | Files successfully sanitized |
| `files_quarantined` | Files quarantined |
| `records_processed` | Total records processed |
| `identifiers_detected` | Total PII spans detected |
| `records_linked` | Records assigned a non-null pseudonym |
| `records_generalized` | Records with quasi-identifier transformations |
| `records_suppressed` | Records with rare-value suppression applied |
| `records_quarantined` | Records quarantined |

**Forbidden:** Invented metrics, original filenames in output, raw PII in any field.

#### 3.6.3 records.jsonl
One JSON line per patient record in sanitized output.

Required fields per line:
- `file`: Relative path to sanitized file (from `output/sanitized/`)
- `loc`: Record location
  - CSV/TSV: `row:N` (first data row = `row:0`)
  - JSON: JSON Pointer (RFC 6901)
  - Text/FHIR: `doc`
- `patient`: Pseudonym string (e.g., `PSN-A1B2C3D4`) or `null`

**Constraints:**
- Same patient → same pseudonym across all files
- Pseudonym must also appear inside the corresponding sanitized record
- Uncertain identity → `null` (conservative)

### 3.7 Validation Contract
**Organizer Command:**
```bash
python3 validate_output.py --input dev/input --output my_output/
```

**Success Output:**
```
CONTRACT OK
```

**Critical:** Do not claim validation success until the actual organizer validator has been obtained and executed against real output.

---

## 4. Explicit Constraints and Prohibited Approaches

| Prohibited | Required Alternative |
|------------|---------------------|
| Network access during execution | All models, gazetteers, code bundled offline |
| GPU / CUDA dependencies | CPU-only libraries |
| LLMs / Generative AI / Transformers >50M params | Rules, gazetteers, CRF, classical ML |
| Hardcoding `RAKSHA_SECRET` | Read from environment only |
| Renaming `raksha.toml` or changing keys | Use exact organizer identifiers |
| Silent skip of unprocessable files | Explicit quarantine with reason in `report.json` |
| Raw PII in logs, temp files, reports | Scrub all logging; no raw text echoes |
| Transitive linkage closure | Conservative pairwise + cannot-link |
| Unconditional medical whitelist | Contextual, span-level medical protection |
| Latin-1 as universal fallback | Validate file type/structure independently |
| k-anonymity as proof of anonymity | Diagnostic measure + attacker simulation |
| Custom cryptography | `cryptography` library HMAC-SHA256, AES-GCM |
| Flattening all records to unstructured text | Unified model preserving structural serialization |

---

## 5. Threat Model and Attacker Capabilities

### 5.1 Attacker Profile
- **Motivated external adversary** with access to sanitized output
- **Auxiliary data:** Public voter rolls, census data, social media, hospital directories, leaked databases
- **Knowledge:** Full knowledge of LOCKMATE's algorithms (Kerckhoffs's principle)
- **Capabilities:** Record linkage, quasi-identifier join, statistical inference, script/transliteration matching
- **No insider access:** No access to `RAKSHA_SECRET`, raw inputs, or internal processing state

### 5.2 Attack Vectors to Defend
1. **Direct identifier leakage:** Names, phones, IDs in output
2. **Quasi-identifier linkage:** (Age band + District + Diagnosis + Stay length) → unique patient
3. **Residual name fragments:** Partial redaction, missed mentions
4. **Metadata/filename leakage:** PII in JSON keys, filenames, FHIR extensions
5. **Date/shift reversibility:** Deterministic shift without secret → recoverable dates
6. **Pseudonym collision/linkage:** Weak canonicalization → cross-patient correlation
7. **Format-specific leaks:** FHIR references, contained resources, attachments

### 5.3 Defense Posture
- **Fail-safe:** Uncertain → quarantine, never silent pass
- **Conservative linkage:** False merge worse than missed link
- **Independent verification:** Output security gate separate from detection engine
- **Canary testing:** Synthetic unique identifiers must never appear in output
- **Secret-dependent transformations:** Different `RAKSHA_SECRET` → different pseudonyms/shifts

---

## 6. System Architecture and Component Responsibilities

```
INPUT DIRECTORY
      │
      ▼
SECURE INTAKE
      │  ├── Safe discovery (walk, symlink check, path traversal protection)
      │  ├── SHA-256 per file
      │  ├── Resource limits (file size, nesting depth, decompression)
      │  └── File-type classification
      ▼
FORMAT DETECTION & PARSING
      │  ├── CSV/TSV (delimiter detection, header inference)
      │  ├── JSON (schema-agnostic walk, nested objects/arrays)
      │  ├── FHIR R4 (fhir.resources validation, references, extensions, contained)
      │  ├── Plain Text (UTF-8, encoding detection via charset-normalizer)
      │  └── Unsupported/Corrupted → QUARANTINE
      ▼
UNIFIED RECORD MODEL (URM)
      │  ├── Source file hash, format, record location
      │  ├── Field values, types, original/normalized text
      │  ├── Span-offset mappings (normalized ↔ original)
      │  ├── Structural preservation for serialization
      │  └── Processing status flags
      ▼
UNICODE NORMALIZATION
      │  ├── NFC normalization
      │  ├── Devanagari digit → ASCII
      │  ├── Zero-width char handling
      │  ├── Bidi/confusable checks
      │  └── Offset mapping maintenance
      ▼
PII DETECTION ENGINE
      │  ├── Structured fields (headers, JSON keys, FHIR elements, filenames)
      │  ├── Direct identifiers (phone, email, Aadhaar, ABHA, PAN, UHID/MRN, PIN)
      │  ├── Multilingual name detection (honorifics, relationships, gazetteers, transliteration, CRF-optional)
      │  ├── Contextual classification (patient vs relative vs doctor vs clinical)
      │  └── Medical preservation veto (span-level, not sentence-level)
      ▼
IDENTITY RESOLUTION
      │  ├── Blocking (normalized name, transliteration, Double Metaphone, shared IDs)
      │  ├── Pairwise scoring (Jaro-Winkler, token overlap, ID match, age/geo consistency)
      │  ├── Cannot-link constraints (conflicting IDs, DOB, gender)
      │  ├── Conservative clustering (greedy, cluster consistency check, no transitive closure)
      │  └── Null assignment for uncertain
      ▼
PSEUDONYM SERVICE
      │  ├── Canonical patient identity (sorted reliable identifiers)
      │  ├── HMAC-SHA256(RAKSHA_SECRET, canonical_identity)
      │  ├── Truncation/encoding → `PSN-XXXX` format
      │  ├── Null for uncertain clusters
      │  └── Deterministic per secret
      ▼
PRIVACY TRANSFORMATIONS
      │  ├── Date shifting (patient-specific offset from HMAC-secret)
      │  ├── Age generalization (configurable bands, 90+ ceiling)
      │  ├── Location generalization (village→district, PIN→prefix, rare suppression)
      │  └── Rare-value suppression (k-anonymity diagnostic, local suppression)
      ▼
SERIALIZATION
      │  ├── URM → original format (CSV/TSV/JSON/FHIR/text)
      │  ├── Pseudonym injection into records
      │  ├── Filename sanitization
      │  └── Atomic write (temp → rename)
      ▼
INDEPENDENT OUTPUT SECURITY GATE (separate from detection)
      │  ├── Residual high-confidence PII scan
      │  ├── Canary string check
      │  ├── Clinical integrity verification
      │  ├── Schema/format validity (FHIR R4)
      │  ├── Filename/metadata safety
      │  ├── Pseudonym consistency
      │  └── FAIL → QUARANTINE output
      ▼
+-------------------+------------------+------------------+
│                   │                  │                  │
▼                   ▼                  ▼                  ▼
SANITIZED        REPORT.JSON       RECORDS.JSONL      QUARANTINE
```

**Key Architectural Invariants:**
1. **Unified Record Model** preserves structure for lossless round-trip serialization
2. **Offset mappings** enable safe in-place replacement after normalization
3. **Independent Output Security Gate** — a file is not safe because the detector says so; it must pass a separate validator
4. **No raw intermediates on disk** — minimize temporary files; encrypt if unavoidable
5. **Deterministic pipeline** — same input + same secret = byte-identical sanitized content

---

## 7. Complete End-to-End Data Flow

1. **Discovery:** `main.py` walks `--input`, computes SHA-256 for each file, builds processing queue
2. **Classification:** Each file → format parser or quarantine (unsupported/corrupt)
3. **Parsing:** Parser emits URM records with field values, types, locations, structural context
4. **Normalization:** Unicode NFC, digit mapping, offset maps stored per record
5. **Detection:** PII engine scans all fields + filenames + metadata → PII spans + medical spans
6. **Medical Protection:** Medical spans veto overlapping PII spans (contextual, not blanket)
7. **Identity Resolution:** Candidate generation → pairwise scoring → cannot-link → conservative clusters
8. **Pseudonymization:** Canonical key per cluster → HMAC-SHA256 → `PSN-XXXX` (or `null`)
9. **Privacy Transforms:** Date shift, age bands, location generalization, rare suppression
10. **Serialization:** URM → sanitized files with pseudonyms injected, safe filenames
11. **Security Gate:** Independent scan of sanitized output → pass or quarantine
12. **Reporting:** `report.json` (hash-keyed, measured totals), `records.jsonl` (file, loc, patient)
13. **Atomic Publication:** Write to temp, verify, rename into `--output`

---

## 8. File Ingestion and Format Handling

### 8.1 Supported Formats (Must Work)
| Format | Parser | Key Requirements |
|--------|--------|------------------|
| CSV | `csv` module or `pandas` | Auto-delimiter, header inference, quote handling, shifted columns |
| TSV | Same as CSV | Tab delimiter detection |
| JSON | `json` module | Schema-agnostic walk, nested objects/arrays, large file streaming |
| Plain Text | Direct read | Encoding detection, line/paragraph segmentation |
| FHIR R4 | `fhir.resources` | Bundle/Resource validation, references, extensions, contained, attachments |

### 8.2 Unsupported → Quarantine
- PDF, images, binary blobs, encrypted archives, decompression bombs
- Corrupted/malformed files of supported types
- Files exceeding size/nesting limits

### 8.3 Encoding Handling
- Primary: `charset-normalizer` for detection
- Supported: UTF-8 (with/without BOM), UTF-16 LE/BE, CP1252
- **Never** use Latin-1 as catch-all for arbitrary binary
- Failed decode → quarantine with reason `"encoding_detection_failed"`

### 8.4 Metadata and Filename Scanning
- Filenames parsed for PII (e.g., `patient_rahul_sharma.csv`)
- JSON keys scanned (e.g., `"patient_name"`, `"mobile_number"`)
- FHIR metadata/extensions scanned
- All treated as unstructured text for detection

### 8.5 Resource Limits (Enforced at Intake)
| Limit | Value | Action on Exceed |
|-------|-------|------------------|
| Max file size | 100 MB | Quarantine |
| Max nesting depth (JSON/FHIR) | 50 | Quarantine |
| Max decompression ratio | 100:1 | Quarantine |
| Max total input size | 2 GB | Stop with error |

---

## 9. Multilingual PII Detection Strategy

### 9.1 Unicode Normalization (Pre-Detection)
- **NFC** normalization for all text
- **Devanagari digits** (०-९) → ASCII (0-9)
- **Zero-width** (ZWJ, ZWNJ, BOM) removed or normalized
- **Whitespace** normalized (NBSP → space, tabs → space)
- **Bidi/confusable** characters flagged (potential evasion)
- **Offset maps** maintained: normalized_index ↔ original_index per record

### 9.2 Structured Field Detection
| Source | Examples |
|--------|----------|
| CSV/TSV Headers | `patient_name`, `mobile`, `aadhaar_no`, `uhid` |
| JSON Keys | `"patientName"`, `"contact.phone"`, `"identifier[0].value"` |
| FHIR Elements | `Patient.name`, `Patient.telecom`, `Patient.identifier` |
| Filenames | `rahul_sharma_lab_report.pdf` |
| Nested Paths | `entry[0].resource.subject.reference` |

**Rule:** Do not trust headers/keys alone — always validate content.

### 9.3 Direct Identifier Detection (High Precision)

| Identifier | Specification | Validation |
|------------|---------------|------------|
| **Phone (India)** | +91/0 prefix, 10 digits starting 6-9 | `phonenumbers` library + regex |
| **Aadhaar** | 12 digits, Verhoeff checksum | Implement Verhoeff algorithm |
| **ABHA (Ayushman Bharat)** | 14 digits | Format + checksum if specified |
| **PAN** | 5 letters + 4 digits + 1 letter | Regex `^[A-Z]{5}[0-9]{4}[A-Z]$` |
| **UHID/MRN** | Hospital-specific patterns | Learn from practice data; context keywords |
| **Email** | Standard RFC 5322 | Regex + `email-validator` |
| **PIN Code** | 6 digits | Regex + India Post validation (optional) |
| **Dates** | Multiple formats | `dateparser` + contextual classification |

**Critical:** Numeric pattern alone ≠ identifier. Require structural validation + contextual cues.

### 9.4 Multilingual Name Detection

**Layered Approach:**

1. **Honorifics/Relationship Markers (High Precision Triggers)**
   - English: `Mr.`, `Mrs.`, `Ms.`, `Dr.`, `Prof.`, `S/o`, `D/o`, `W/o`, `C/O`, `Son of`, `Daughter of`, `Wife of`
   - Hindi/Devanagari: `श्री`, `श्रीमती`, `कुमार`, `कुमारी`, `पुत्र`, `पुत्री`, `पत्नी`, `के/की देखभाल में`
   - Hinglish: `S/o Rahul`, `C/O Dr. Sharma`

2. **Gazetteers (Offline, Bundled)**
   - Indian first names (Latin + Devanagari) from census/public data
   - Surnames (Patel, Rao, Sharma, Singh, Kumar, etc. + Devanagari variants)
   - Transliteration variants (Mohammad, Mohammed, Mohd., मुहम्मद, मोहम्मद)
   - **No patient-specific names** — only public frequency lists

3. **Transliteration + Phonetic Blocking**
   - `indic-transliteration` or custom Devanagari→IAST→Latin
   - Double Metaphone on transliterated names (handles cross-script matching)
   - Soundex as fallback

4. **Contextual Classification (Role-Aware)**
   | Context | Classification | Action |
   |---------|----------------|--------|
   | `Patient Name: Rahul` | Patient | Redact → pseudonym |
   | `S/o Rahul` | Relative | Redact → `[RELATIVE]` or link to patient |
   | `Dr. Rahul` | Doctor | Preserve (if clinical context) |
   | `C/O fever` | Clinical | Preserve (not a name) |
   | `Parkinson's disease` | Clinical | Preserve (medical veto) |
   | `Rahul` (isolated, no context) | Ambiguous | Quarantine or conservative redact |

5. **Optional CRF (Only If Justified)**
   - `sklearn-crfsuite` with features: token shape, script, gazetteer membership, context window
   - Train on practice data only
   - **Must** demonstrate measurable improvement over rule baseline
   - Model size **< 50M params** (trivially satisfied)

6. **Document-Level Consistency**
   - Within a file/record: same entity → same replacement
   - Cross-file: handled by identity resolution (Stage 11)

### 9.5 Replacement Strategy
| PII Type | Replacement |
|----------|-------------|
| Patient name | Pseudonym (`PSN-XXXX`) |
| Relative name | `[RELATIVE]` or linked pseudonym |
| Doctor name (clinical) | Preserve or `[DOCTOR]` |
| Phone/Aadhaar/PAN/ABHA | `[PHONE]`, `[UID]`, `[PAN]`, `[ABHA]` |
| Email | `[EMAIL]` |
| PIN/Address | Generalized (Stage 13) |
| Dates | Shifted (Stage 13) |
| Uncertain/Ambiguous | Quarantine file |

### 9.6 Second-Pass Sweep
- Re-scan sanitized text for residual high-confidence PII
- Search for patient's known identifiers (name variants, phones, IDs) collected during detection
- Any straggler → quarantine

---

## 10. Medical Entity Preservation Strategy

**Principle:** Contextual, span-level protection — **not** an unconditional whitelist.

### 10.1 Protected Categories (Must Survive)
| Category | Examples | Detection Method |
|----------|----------|------------------|
| Drug names | Paracetamol, Dolo, Metformin, Aspirin | Gazetteer (INN + brand names) |
| Strengths/Dosages | `650 mg`, `500mg`, `10 mg/mL`, `5 mL` | Regex: `\d+(\.\d+)?\s*(mg|g|mL|mcg|IU|U)\b` |
| Frequencies | `OD`, `BD`, `TDS`, `QID`, `SOS`, `once daily` | Gazetteer + regex |
| Durations | `5 days`, `2 weeks`, `1 month` | Regex + context |
| Lab names | `HbA1c`, `CBC`, `LFT`, `KFT`, `TSH`, `Hb`, `WBC` | Gazetteer (LOINC-derived) |
| Units | `mg/dL`, `mmol/L`, `U/L`, `ng/mL`, `°C`, `bpm` | Gazetteer |
| Vitals | `BP 120/80`, `HR 72`, `Temp 98.6`, `SpO2 98%` | Pattern + context |
| Diagnoses | `Diabetes`, `Hypertension`, `TB`, `HIV`, `Parkinson's`, `Alzheimer's` | ICD-10 derived list + eponyms |
| Procedures | `Angiography`, `Dialysis`, `Appendectomy` | Gazetteer |
| Stay durations | `Admitted 3 days`, `LOS: 5` | Pattern + context |

### 10.2 Medical Veto Logic
- When PII span **overlaps** medical span → **medical wins** (preserve)
- When PII span **adjacent** to medical span → re-evaluate (e.g., "Rahul 5 mg" → "Rahul" may be patient, "5 mg" preserved)
- Doctor names: Preserve **only** when preceded by `Dr.`/`Doctor` and in clinical context (prescription, referral)
- Disease eponyms (Parkinson's, Alzheimer's, Crohn's): Always preserve

### 10.3 Implementation
- **Tagging pass before detection:** Mark medical spans as `PROTECTED`
- **Detection pass:** Skip/veto PII tags inside `PROTECTED` spans
- **Post-detection verification:** Confirm no clinical value corrupted

---

## 11. Identity Resolution and Record Linkage

### 11.1 Conservative Design Principles
- **Precision > Recall:** False merge (two patients → one pseudonym) is catastrophic; missed link (one patient → two pseudonyms) is acceptable
- **No transitive closure:** A~B and B~C does not imply A~C without direct evidence
- **Cannot-link constraints:** Conflicting hard identifiers (different Aadhaar, DOB, gender) → force separate
- **Null for uncertain:** If evidence < threshold → `patient: null`

### 11.2 Candidate Generation (Blocking)
Reduce pairwise comparisons using blocking keys:
| Blocking Key | Derivation |
|--------------|------------|
| Normalized name (Latin) | Lowercase, remove honorifics, ASCII-fold |
| Transliterated name | Devanagari → IAST → Latin → normalize |
| Double Metaphone | Primary + alternate codes on transliterated name |
| Phone (exact) | Digits only, last 10 |
| Aadhaar/ABHA/PAN (exact) | Full validated identifier |
| DOB Year + Gender | If available |
| District + PIN prefix | Geographic |

Records sharing ≥1 blocking key → candidate pair.

### 11.3 Pairwise Scoring (Fellegi-Sunter Inspired)
For each candidate pair, compute weighted evidence:

| Feature | Weight Logic |
|---------|--------------|
| Exact Aadhaar/ABHA/PAN match | Very high (near-deterministic) |
| Exact phone match | High |
| Name Jaro-Winkler (Latin) | Scaled 0-1 |
| Name token overlap (Jaccard) | Scaled 0-1 |
| Transliterated name similarity | Scaled 0-1 |
| Double Metaphone match | Binary |
| Relative name agreement | Moderate |
| DOB year exact | High |
| Age difference ≤2 years | Moderate |
| Gender match | Low |
| District match | Low |
| PIN prefix match | Low |

**Score = Σ (weight × agreement) — Σ (weight × disagreement)**

### 11.4 Thresholding and Clustering
1. **Pairwise threshold:** Only pairs with score ≥ `τ_high` (e.g., 0.85) are links
2. **Cannot-link:** If pair has conflicting hard ID (different Aadhaar, DOB, gender) → score = -∞
3. **Greedy clustering:** Sort linked pairs by score descending; merge clusters if **all** cross-pairs within merged cluster satisfy threshold and no cannot-link violations
4. **Consistency check:** After clustering, verify every pair in cluster meets threshold; if not, split
5. **Null assignment:** Records in no cluster → `patient: null`

### 11.5 Output
- Each cluster → canonical identity key (sorted concatenation of reliable identifiers)
- Canonical key → pseudonym via HMAC (Section 12)
- Singleton clusters with no strong ID → `null`

---

## 12. Pseudonymization and Cryptographic Design

### 12.1 Requirements
- Same patient + same `RAKSHA_SECRET` → same pseudonym
- Different `RAKSHA_SECRET` → different pseudonym (verifiable)
- Irreversible (one-way)
- Stable across hospitals/files
- `null` for uncertain identity
- No custom crypto

### 12.2 Algorithm
```python
from cryptography.hazmat.primitives import hmac, hashes

def derive_pseudonym(canonical_identity: str, secret: bytes) -> str:
    # canonical_identity: sorted, pipe-joined reliable identifiers
    # e.g., "aadhaar:123456789012|phone:9876543210|name_latin:rahul_sharma"
    h = hmac.HMAC(secret, hashes.SHA256())
    h.update(canonical_identity.encode('utf-8'))
    digest = h.finalize()
    # Truncate to 16 bytes (128 bits), base32 encode, prefix
    truncated = digest[:16]
    b32 = base64.b32encode(truncated).decode('ascii').rstrip('=').lower()
    return f"PSN-{b32[:8]}"  # PSN-XXXXXXXX format
```

### 12.3 Canonical Identity Construction
- Collect **reliable** identifiers from cluster: validated Aadhaar, ABHA, PAN, phone, DOB, normalized name
- Sort lexicographically by type:name
- Join with `|`
- If cluster has **no** reliable identifiers → generate random UUID, HMAC it (ensures consistency within run), but mark as weak

### 12.4 Secret Handling
- Read `RAKSHA_SECRET` from `os.environ` at startup
- Store in memory only (bytes)
- Never log, print, write to disk, include in reports
- Use for **all** HMAC operations (pseudonyms, date shifts, rare suppression seeds)

### 12.5 Key Separation (If Needed)
If multiple HMAC uses require domain separation:
```python
def hmac_with_domain(secret: bytes, domain: str, message: bytes) -> bytes:
    h = hmac.HMAC(secret, hashes.SHA256())
    h.update(domain.encode('utf-8'))
    h.update(message)
    return h.finalize()
```
Domains: `"pseudonym"`, `"date_shift"`, `"rare_suppression"`

---

## 13. Quasi-Identifier Generalization

### 13.1 Date Shifting (Patient-Consistent)
- **Goal:** Preserve intervals, hide exact day/month
- **Method:** Per-patient deterministic offset from HMAC
```python
def patient_date_shift(secret: bytes, patient_pseudonym: str) -> int:
    # Returns offset in days [-365, +365]
    h = hmac.HMAC(secret, hashes.SHA256())
    h.update(b"date_shift")
    h.update(patient_pseudonym.encode('utf-8'))
    digest = h.finalize()
    # Map to [-365, 365]
    offset = int.from_bytes(digest[:4], 'big') % 731 - 365
    return offset
```
- Apply to **all** dates for that patient (admission, discharge, DOB, visit, lab)
- Preserve timezone info if present
- **Do not shift:** Medication durations, dosage intervals, clinical measurements

### 13.2 Age Generalization
- Input: Age (integer) or DOB (→ age at reference date)
- Bands: `[0-4, 5-9, 10-14, 15-19, 20-24, 25-29, 30-34, 35-39, 40-44, 45-49, 50-54, 55-59, 60-64, 65-69, 70-74, 75-79, 80-84, 85-89, 90+]`
- **Always round down** into band (e.g., 27 → `25-29`)
- Unknown/invalid age → `null` (do not invent)
- Output: Band string (e.g., `"25-29"`) or structured `{"age_band": "25-29"}`

### 13.3 Location Generalization
| Input Granularity | Output Granularity | Method |
|-------------------|-------------------|--------|
| Village | District | Gazetteer mapping (Census 2011) |
| City/Town | District | Gazetteer mapping |
| District | State | Gazetteer mapping |
| PIN Code (6-digit) | 3-digit prefix | Truncate |
| Rare District (<k patients) | State | Suppress upward |
| Lat/Long | District centroid | Reverse geocode (offline) |

**Rare Location Suppression:** If (age_band + district + diagnosis) group size < 5 → generalize district to state.

### 13.4 Rare-Value Suppression (k-Anonymity Diagnostic)
- Compute equivalence classes on quasi-identifiers: `{age_band, district, gender, diagnosis_category, los_band}`
- If class size < `k_min` (default 5):
  1. Suppress rarest attribute (diagnosis → parent category)
  2. Generalize age band (widen)
  3. Generalize location (district → state)
  4. Repeat until ≥k or fully suppressed
- **Measure:** Report k-anonymity distribution (diagnostic only, not proof)

### 13.5 Attacker Simulation (Validation)
- Generate synthetic "voter roll" with name, age, village, gender
- Attempt linkage: sanitized quasi-IDs + pseudonym → voter roll
- Measure: % of patients uniquely re-identified
- Target: < 5% unique matches after transformations

---

## 14. Privacy and Re-identification Risk Controls

| Control | Implementation |
|---------|----------------|
| **Direct ID Removal** | Multi-layer detection + second-pass sweep |
| **Quasi-ID Generalization** | Date shift, age bands, location hierarchy, rare suppression |
| **Conservative Linkage** | High threshold, cannot-link, no transitive closure |
| **Cryptographic Pseudonyms** | HMAC-SHA256 with secret, domain separation |
| **Independent Output Gate** | Separate validator scans sanitized output |
| **Canary Testing** | Unique synthetic IDs injected → must not appear in output |
| **Secret Rotation Test** | Different `RAKSHA_SECRET` → different pseudonyms/shifts |
| **Determinism Test** | Same input + same secret → byte-identical sanitized content |
| **No Raw Leakage** | Scrubbed logging, no temp files with PII, atomic writes |
| **Quarantine Default** | Uncertain → quarantine, never silent pass |

---

## 15. Security, Encryption, Temporary Storage, and Logging

### 15.1 Temporary Storage
- **Minimize disk intermediates** — process in memory where possible
- If temp files required (large FHIR bundles):
  - Use `tempfile.mkstemp()` with `O_EXCL`
  - Encrypt with AES-GCM (key derived from `RAKSHA_SECRET` + domain `"temp"`)
  - Secure delete on cleanup (`os.remove` after overwrite)
  - Track all temp paths; cleanup in `finally` block

### 15.2 Logging
- **Structured logging only** (JSON lines)
- **Never** log raw text, field values, filenames with PII
- Log: hashes, counts, timing, memory, status codes
- If debug logging needed: redact via detection engine before emit

### 15.3 Encryption
- **Only** `cryptography` library (FIPS-capable)
- AES-GCM for temp files (fresh nonce per file)
- HMAC-SHA256 for pseudonyms/date-shifts
- No custom schemes

### 15.4 Memory Safety
- Process large files in chunks (streaming JSON, CSV)
- Explicit `del` of large intermediates
- `gc.collect()` at stage boundaries
- Monitor RSS; abort if > 3.5 GB

---

## 16. Output Generation and Exact Organizer Schemas

### 16.1 Sanitized Files
- **Format preservation:** CSV→CSV (same delimiter), JSON→JSON (same structure), FHIR→valid R4
- **Pseudonym injection:** Add/replace patient identifier field with `PSN-XXXX`
- **Filename sanitization:** Hash-based names for PII-bearing originals (e.g., `sha256[:16].csv`)
- **Encoding:** UTF-8 only (with BOM for CSV if original had it)

### 16.2 report.json Schema
```json
{
  "files": {
    "<sha256_hex>": {
      "output_path": "sanitized/subdir/file.csv",
      "status": "sanitized",
      "quarantine_reason": null,
      "processing_duration_ms": 123,
      "peak_memory_mb": 45,
      "records_processed": 100,
      "identifiers_detected": 250,
      "records_linked": 95,
      "records_generalized": 100,
      "records_suppressed": 3,
      "records_quarantined": 0
    },
    "<sha256_hex>": {
      "output_path": null,
      "status": "quarantined",
      "quarantine_reason": "unsupported_format",
      "processing_duration_ms": 5,
      "peak_memory_mb": 2,
      "records_processed": 0,
      "identifiers_detected": 0,
      "records_linked": 0,
      "records_generalized": 0,
      "records_suppressed": 0,
      "records_quarantined": 0
    }
  },
  "totals": {
    "files_total": 2,
    "files_sanitized": 1,
    "files_quarantined": 1,
    "records_processed": 100,
    "identifiers_detected": 250,
    "records_linked": 95,
    "records_generalized": 100,
    "records_suppressed": 3,
    "records_quarantined": 0,
    "total_processing_duration_ms": 128,
    "peak_memory_mb": 47
  }
}
```

### 16.3 records.jsonl Schema
```jsonl
{"file": "sanitized/hospital_a/patients.csv", "loc": "row:0", "patient": "PSN-a1b2c3d4"}
{"file": "sanitized/hospital_a/patients.csv", "loc": "row:1", "patient": "PSN-a1b2c3d4"}
{"file": "sanitized/hospital_b/encounters.json", "loc": "/entry/0/resource/subject/reference", "patient": "PSN-a1b2c3d4"}
{"file": "sanitized/hospital_c/notes.txt", "loc": "doc", "patient": null}
```

---

## 17. Error Handling and Quarantine Behavior

### 17.1 Quarantine Triggers
| Trigger | Reason Code |
|---------|-------------|
| Unsupported file format | `unsupported_format` |
| Encoding detection failed | `encoding_detection_failed` |
| Parser error (malformed CSV/JSON/FHIR) | `parse_error` |
| File exceeds size/nesting limits | `resource_limit_exceeded` |
| Residual high-confidence PII after second pass | `residual_pii` |
| Output security gate failure | `output_gate_failed` |
| Identity resolution uncertainty (optional) | `uncertain_identity` |
| Symlink/path traversal attempt | `path_traversal` |
| Decompression bomb detected | `decompression_bomb` |

### 17.2 Quarantine Procedure
1. Copy original file to `output/sanitized/quarantined/<sha256><original_ext>`
2. Write `report.json` entry with `status: "quarantined"`, `output_path` = quarantine path, `quarantine_reason` = code
3. **Do not** process further
4. Continue with other files (fail-safe, not fail-stop)

### 17.3 Top-Level Exception Handler
```python
def main():
    try:
        run_pipeline()
    except Exception as e:
        # Log error (hash only), quarantine all unprocessed files
        # Write partial report.json with what completed
        # Exit non-zero
```

---

## 18. Determinism and Reproducibility

### 18.1 Deterministic Requirements
- Same input directory + same `RAKSHA_SECRET` → **byte-identical** `sanitized/` content, `records.jsonl`
- `report.json` **totals** must be identical; `processing_duration_ms` and `peak_memory_mb` may differ (telemetry)
- File iteration order: **sort by SHA-256** (not filesystem order)
- Random seeds: Fixed (`random.seed(0)`, `numpy.random.seed(0)`) if any stochastic component
- No `datetime.now()` in content; use fixed reference if needed

### 18.2 Secret Rotation Verification
- Run pipeline with `SECRET_A` → output `OUT_A`
- Run pipeline with `SECRET_B` → output `OUT_B`
- **Verify:** Pseudonyms differ, date shifts differ, rare suppression patterns differ
- **Verify:** Clinical content identical, structure identical

### 18.3 Canary Testing
- Inject unique strings into test input: `LOCKMATE_CANARY_<UUID>`
- After full run: `grep -r "LOCKMATE_CANARY" output/` → **zero matches**
- Also check logs, temp directories, memory dumps

---

## 19. Performance and Resource Constraints

### 19.1 Limits (Organizer)
- **Time:** 15 minutes (900 seconds) wall-clock
- **Memory:** 4 GB RSS peak
- **CPU:** 2 cores

### 19.2 Target Budgets (Internal)
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

### 19.3 Optimization Strategies
- **Blocking** reduces linkage from O(N²) to O(N·k)
- Streaming parsers for large files
- Vectorized pandas/numpy where applicable
- Pre-compiled regexes, cached gazetteer lookups (frozenset/dict)
- Parallelize file-level parsing (2 processes max)
- **No** model inference loops on CPU-heavy transformers

---

## 20. Technology Stack and Dependency Decisions

### 20.1 Core Dependencies (Pinned)
| Package | Purpose | Version Constraint |
|---------|---------|-------------------|
| `cryptography` | HMAC, AES-GCM | ≥41.0, <45 |
| `charset-normalizer` | Encoding detection | ≥3.3, <4 |
| `phonenumbers` | Phone validation | ≥8.13, <9 |
| `dateparser` | Date parsing | ≥1.2, <2 |
| `indic-transliteration` | Devanagari→Latin | ≥1.1, <2 |
| `fhir.resources` | FHIR R4 validation | ≥7.0, <8 |
| `jsonschema` | JSON schema validation | ≥4.20, <5 |
| `regex` | Enhanced regex (Unicode) | ≥2023.0, <2025 |
| `pandas` | CSV/TSV, vectorized ops | ≥2.1, <3 |
| `pyyaml` | Config parsing | ≥6.0, <7 |

### 20.2 Optional / Conditional
| Package | Purpose | Condition |
|---------|---------|-----------|
| `sklearn-crfsuite` | CRF name tagger | Only if measurable gain > rule baseline |
| `scikit-learn` | Classical ML utilities | If CRF used |
| `rapidfuzz` | Fast string similarity | If Jaro-Winkler bottleneck |

### 20.3 Excluded
- `torch`, `tensorflow`, `transformers`, `sentence-transformers`, `spacy` (large models)
- Any package pulling >50M param models
- Network-dependent packages

### 20.4 Runtime
- Python 3.11+ (organizer environment)
- `requirements.txt` with pinned versions
- `raksha.toml` setup: `pip install -r requirements.txt`

---

## 21. Internal Interfaces and Shared Data Contracts

*All agents must implement these interfaces exactly. Defined by Orchestrator (Agent 0) before parallel work begins.*

### 21.1 InputFile
```python
@dataclass(frozen=True)
class InputFile:
    path: Path                    # Absolute path
    sha256: str                   # 64-char hex
    size_bytes: int
    format: FormatType            # CSV, TSV, JSON, TEXT, FHIR, UNKNOWN
    encoding: str                 # Detected encoding
```

### 21.2 ParsedDocument
```python
@dataclass
class ParsedDocument:
    source_file: InputFile
    records: List[UnifiedRecord]  # One per logical record
    format_specific: Dict         # For serialization (e.g., CSV dialect, FHIR bundle type)
```

### 21.3 UnifiedRecord (URM)
```python
@dataclass
class UnifiedRecord:
    record_id: str                # Stable: f"{file_sha256}:{loc}"
    location: RecordLocation      # row:N, JSON pointer, "doc"
    fields: Dict[str, FieldValue] # Field name → value + metadata
    raw_text: str                 # Full text for unstructured/content search
    normalized_text: str          # Post-normalization
    offset_map: List[Tuple[int, int]]  # (norm_start, norm_end) → (orig_start, orig_end)
    status: RecordStatus          # PENDING, PROCESSED, QUARANTINED
```

### 21.4 FieldValue
```python
@dataclass
class FieldValue:
    value: Any                    # Original value
    field_type: FieldType         # STRING, NUMBER, DATE, BOOLEAN, OBJECT, ARRAY
    path: str                     # Structural path (e.g., "patient.name[0].given[0]")
    is_identifier_field: bool     # Header/key suggests ID
```

### 21.5 PIISpan
```python
@dataclass
class PIISpan:
    start: int                    # Offset in normalized_text
    end: int                      # Offset in normalized_text
    pii_type: PIIType             # NAME, PHONE, AADHAAR, ABHA, PAN, EMAIL, ADDRESS, DATE, UHID, RELATIVE, DOCTOR
    confidence: float             # 0.0-1.0
    original_text: str            # For reporting
    context: str                  # Surrounding 50 chars
    detector: str                 # Which detector fired
```

### 21.6 MedicalSpan
```python
@dataclass
class MedicalSpan:
    start: int
    end: int
    medical_type: MedicalType     # DRUG, DOSAGE, FREQUENCY, DIAGNOSIS, LAB, VITAL, UNIT, PROCEDURE, DURATION
    confidence: float
    original_text: str
```

### 21.7 IdentityCandidate
```python
@dataclass
class IdentityCandidate:
    record_a: UnifiedRecord
    record_b: UnifiedRecord
    blocking_keys: List[str]
    scores: Dict[str, float]      # Feature → score
    total_score: float
    cannot_link: bool
```

### 21.8 PatientCluster
```python
@dataclass
class PatientCluster:
    cluster_id: str               # Internal, deterministic
    records: List[UnifiedRecord]
    canonical_identity: str       # For pseudonym derivation
    pseudonym: Optional[str]      # PSN-XXXX or None
    is_confident: bool            # False → pseudonym = None
```

### 21.9 PrivacyTransformation
```python
@dataclass
class PrivacyTransformation:
    record: UnifiedRecord
    date_shifts: Dict[str, int]   # field_path → days_offset
    age_band: Optional[str]
    location_generalization: Dict[str, str]  # field_path → generalized_value
    suppressions: List[str]       # field_paths suppressed
```

### 21.10 SanitizedRecord
```python
@dataclass
class SanitizedRecord:
    record: UnifiedRecord
    transformed_text: str         # After all replacements
    transformed_fields: Dict[str, Any]  # For structured serialization
    pseudonym: Optional[str]
```

### 21.11 QuarantineResult
```python
@dataclass
class QuarantineResult:
    input_file: InputFile
    reason: QuarantineReason
    output_path: Path             # In sanitized/quarantined/
    records_affected: int
```

### 21.12 ProcessingMetrics
```python
@dataclass
class ProcessingMetrics:
    file_sha256: str
    duration_ms: int
    peak_memory_mb: int
    records_processed: int
    identifiers_detected: int
    records_linked: int
    records_generalized: int
    records_suppressed: int
    records_quarantined: int
```

---

## 22. Testing and Validation Requirements

### 22.1 Unit Tests (Per Module)
| Module | Test Focus |
|--------|------------|
| Intake | Symlink handling, path traversal, size limits, SHA-256 |
| Parsing | CSV delimiter detection, JSON streaming, FHIR validation |
| Normalization | Devanagari digits, NFC, offset map correctness |
| Detection | Each identifier type, name gazetteer, medical veto, context rules |
| Medical | Drug/dosage preservation, diagnosis preservation, doctor context |
| Linkage | Blocking keys, pairwise scoring, cannot-link, clustering, null assignment |
| Pseudonym | HMAC determinism, secret rotation, canonical identity stability |
| Privacy | Date shift interval preservation, age bands, location hierarchy |
| Serialization | Round-trip CSV/JSON/FHIR, pseudonym injection, filename safety |
| Security Gate | Residual PII detection, canary check, schema validation |

### 22.2 Integration Tests
- Full pipeline on synthetic multi-format dataset
- Multi-hospital, multi-script patient linkage
- Quarantine propagation to report.json
- Atomic write verification (power-cut simulation)

### 22.3 Adversarial / Red-Team Tests
| Test | Description |
|------|-------------|
| **Canary Leakage** | Unique synthetic IDs in input → absent in output/logs/temp |
| **False Merge** | Two similar patients (same name, different DOB) → separate pseudonyms |
| **False Negative** | Known PII variants (Hinglish, transliterated, misspelled) → detected |
| **Medical Corruption** | Clinical values adjacent to names → preserved |
| **Filename Leakage** | PII in filename → not in sanitized output path |
| **Metadata Leakage** | PII in JSON keys/FHIR extensions → redacted |
| **Date Reversibility** | Known shift + output → cannot recover original without secret |
| **Pseudonym Collision** | Two patients → different pseudonyms (birthday paradox check) |
| **k-Anonymity** | Quasi-ID groups → size ≥5 after generalization |
| **Attacker Simulation** | Synthetic voter roll linkage → <5% unique re-ID |

### 22.4 Organizer Contract Validation
- Run `validate_output.py` on every build
- `CONTRACT OK` required before any submission claim
- Test with organizer practice dataset (when available)

### 22.5 Performance Tests
- Max input (2 GB, 1000+ files) → < 900s, < 4 GB RSS
- Stress: Deeply nested JSON, wide CSV, large FHIR bundles
- Determinism: 3 runs same secret → identical sanitized content
- Secret rotation: 2 runs different secrets → different pseudonyms/shifts

---

## 23. Frontend and Demonstration Requirements

### 23.1 Frontend Status: **Optional**
- Not required for CLI evaluation
- Must not be a dependency of `main.py`
- Separate process, optional `streamlit`/`gradio` app

### 23.2 Demo Requirements (If Built)
- **Pipeline Visualization:** Stage-by-stage flow with sample record
- **Before/After Viewer:** Original vs sanitized with highlights
- **Identity Linkage Explorer:** Cross-hospital patient clusters
- **Privacy Attack Dashboard:** Attacker simulation results
- **Metrics Panel:** Detection P/R, linkage F1, k-anonymity, runtime
- **Verifier:** Run `validate_output.py` and show `CONTRACT OK`

### 23.3 Five-Minute Judging Demo Script
1. **Problem (1 min):** Show synthetic multi-hospital records with PII
2. **Identity Intelligence (1 min):** One patient across scripts/formats → stable pseudonym
3. **Clinical Integrity (1 min):** Before/after — identity gone, medicine preserved
4. **Privacy Attack (1 min):** Quasi-ID linkage attempt → measured failure
5. **Verification (1 min):** Sanitized output, quarantine, report.json, records.jsonl, validator result

---

## 24. Known Risks, Unresolved Decisions, and Assumptions

### 24.1 Critical Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| **Organizer validator not available** | Cannot verify `CONTRACT OK` | Build self-validator from contract spec; test locally |
| **Practice dataset not available** | No ground truth for detection/linkage | Generate synthetic fixtures with known labels |
| **FHIR R4 complexity** | References, extensions, contained resources leak PII | Deep traversal test suite; quarantine on validation fail |
| **Multilingual name false merges** | "Rahul Sharma" (Hindi) ≠ "Rahul Sharma" (different person) | Strict cannot-link (DOB, gender, hard IDs); high threshold |
| **Medical veto over-redaction** | Real patient name "Parkinson" preserved as disease | Context window + role markers (S/o, Dr., C/O) override veto |
| **Date shift reversibility** | Attacker knows shift algorithm → brute force secret | 128-bit HMAC output; secret never exposed |
| **Performance on 2GB input** | 15 min / 4 GB hard limit | Streaming, blocking, profiling at each stage |

### 24.2 Unresolved Decisions (Require Orchestrator Resolution)
1. **CRF Inclusion:** Rule baseline first; add CRF only if >5% F1 gain on practice data
2. **Gazetteer Source:** Which public Indian name datasets? (Census 2011, voter rolls, Wikipedia)
3. **Location Gazetteer:** District/village mapping source (Census 2011 CSV bundled?)
4. **FHIR Attachments:** Base64-encoded PDFs in `Binary` resources — quarantine or extract text?
5. **Age Reference Date:** For DOB→age calculation — use earliest date in record? Fixed reference?
6. **Rare Diagnosis Threshold:** What count triggers suppression? (Default k=5)
7. **Output Filename Scheme:** SHA-256 prefix + original extension? UUID?

### 24.3 Assumptions (Labelled)
| Assumption | Status | Verification Needed |
|------------|--------|---------------------|
| Organizer provides `validate_output.py` | **Unverified** | Check workspace / organizer repo |
| Organizer provides practice dataset (`dev/input/`) | **Unverified** | Check workspace / organizer repo |
| FHIR R4 validation via `fhir.resources` matches organizer | **Assumed** | Test against organizer validator |
| `RAKSHA_SECRET` is 32+ bytes, base64 or hex | **Assumed** | Read organizer spec |
| Input directory structure is flat or shallow | **Assumed** | Handle arbitrary depth anyway |
| No real-time / streaming requirement | **Confirmed** | Batch CLI only |

---

## 25. Definition of Done (Project Level)

The project is **complete** when **all** of the following are verified with evidence:

- [ ] **Repository audited** — all official assets identified, `raksha.toml` and `main.py` present
- [ ] **Exact contract implemented** — CLI, output structure, schemas, `raksha.toml`, `RAKSHA_SECRET` handling
- [ ] **CLI works** — `python main.py --input X --output Y` runs without error
- [ ] **Environment secret handling verified** — secret read from env, never logged/written
- [ ] **CSV parsing verified** — delimiters, headers, shifted columns, quotes
- [ ] **TSV parsing verified** — tab delimiter, same as CSV
- [ ] **JSON parsing verified** — nested, arrays, streaming, large files
- [ ] **Text parsing verified** — encoding, line/paragraph segmentation
- [ ] **FHIR R4 handling verified** — Bundle/Resource, references, extensions, contained, attachments
- [ ] **Multilingual PII detection tested** — English, Hindi, Hinglish, transliterated names
- [ ] **Medical preservation tested** — Drugs, dosages, diagnoses, labs, vitals preserved
- [ ] **Identity linkage tested** — Precision/recall/F1 on labeled fixtures; false-merge rate < 1%
- [ ] **False-merge safeguards tested** — Cannot-link, cluster consistency, null assignment
- [ ] **HMAC pseudonymization tested** — Determinism, secret rotation, collision resistance
- [ ] **Date transformations tested** — Interval preservation, chronological ordering, timezone
- [ ] **Age generalization tested** — Bands, boundaries, unknown, invalid, 90+
- [ ] **Location generalization tested** — Village→district, PIN prefix, rare suppression
- [ ] **Metadata/filename leakage tested** — JSON keys, FHIR extensions, filenames clean
- [ ] **Attachments handled safely** — Binary/Base64 quarantined or processed
- [ ] **Unsupported formats quarantined** — PDF, images, corrupt, oversized
- [ ] **Output security gate implemented** — Independent scan, canary check, schema validation
- [ ] **report.json validated** — All required fields, hash keys, accurate totals, no PII
- [ ] **records.jsonl validated** — File/loc/patient, pseudonym consistency, null for uncertain
- [ ] **Offline execution verified** — No network calls, all deps bundled
- [ ] **Resource limits measured** — < 15 min, < 4 GB RSS, 2 CPUs
- [ ] **Deterministic content tested** — 3 runs same secret = byte-identical sanitized/
- [ ] **Different-secret behavior tested** — Pseudonyms/shifts differ, clinical content same
- [ ] **Privacy attack measured** — Attacker simulation < 5% unique re-ID
- [ ] **Clinical utility measured** — > 95% clinical values preserved
- [ ] **README completed** — Models declared, offline/CPU approach explained
- [ ] **Two-page brief completed** — Privacy-utility tradeoffs, threat model, limitations
- [ ] **Demonstration completed** — 5-min script executed with real pipeline output
- [ ] **Official validator executed** — `CONTRACT OK` on practice input (if available)

---

**END OF CONTEXT.MD**  
*This document is the single source of truth. All agents must read it before beginning work.*