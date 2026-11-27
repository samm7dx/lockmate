# Phase 4 Evaluation: Multilingual Identity Intelligence & Residual PII Protection

## Overview

Phase 4 implements the core multilingual PII detection, contextual clinical disambiguation, structured field sanitization, and residual PII security gate for the LOCKMATE privacy firewall.

## Completed Components

### 1. Unicode Normalization Pipeline (`detection/normalize.py`)
- **NFC normalization** with full Unicode support
- **Devanagari digit conversion** (०-९ → 0-9)
- **Zero-width character removal** (ZWSP, ZWNJ, ZWJ, BOM)
- **Bidi control character removal** (LRM, RLM, LRE, RLE, PDF, LRO, RLO)
- **Confusable/homograph normalization** (Cyrillic, Greek, full-width Latin)
- **Character-level offset map** for precise span mapping between original and normalized text

### 2. Gazetteer-based Name Detection (`detection/gazetteer.py`, `detection/names.py`)
- **English names**: Gazetteer of Indian given names + surname patterns
- **Devanagari names**: Gazetteer with Devanagari script names
- **Hinglish names**: Mixed-script name detection with transliteration support
- **Transliteration**: Devanagari → Latin via `indic-transliteration` + Double Metaphone phonetic matching
- **Name patterns**: Honorifics (ji, sahab, didi), patronymics (S/o, D/o, W/o), initials, reversed order

### 3. Identifier Detection (`detection/identifiers.py`)
- **Aadhaar**: 12-digit with Verhoeff checksum validation
- **ABHA**: 14-digit with Verhoeff checksum validation
- **PAN**: 10-char alphanumeric (5 letters + 4 digits + 1 letter)
- **UHID/MRN**: Hospital-specific patterns
- **Insurance IDs**: Generic pattern detection
- **Phone**: Indian format (+91/0 prefix, 10 digits starting 6-9)
- **Email, URL, PIN codes, dates**: Standard patterns

### 4. Clinical Context Modules (`clinical/`)
- **Drugs** (`drugs.py`): Gazetteer-based drug names + dosage/frequency/duration regex
- **Labs/Vitals** (`labs.py`): LOINC-derived lab names + vital patterns (BP, HR, SpO2, etc.)
- **Diagnoses** (`diagnoses.py`): ICD-10 derived + eponymous diseases (Parkinson's, Alzheimer's, etc.)
- **Doctors** (`doctors.py`): Clinical context detection (Dr./Doctor + name + clinical verb)
- **Veto Logic** (`veto.py`): Medical spans veto overlapping PII spans

### 5. Contextual Clinical Disambiguation
- **"C/O Ramesh" vs "C/O fever"**: Relative name detection with "care of" patterns
- **"Dr. Ramesh" vs patient "Ramesh"**: Doctor prefix + clinical verb context
- **Devanagari doctor names**: डॉ./डॉक्टर + Devanagari name + Hindi clinical verbs
- **Medical veto**: Overlapping medical spans suppress PII spans

### 6. Structured Field Sanitization (`detection/structured.py`, `transform/structured.py`)
- **JSON keys**: Recursive key sanitization, not just values
- **CSV headers**: Header row scanning with PII detection
- **FHIR metadata**: `Resource.meta.tag`, `meta.security`, `Bundle.metadata` scanning
- **Filename sanitization**: PII detection in file names
- **Format-preserving output**: CSV/TSV/JSON/FHIR structure maintained

### 7. Residual PII Security Gate (`output/security_gate.py`)
- **Pre-write validation**: Scans all sanitized records before output
- **Post-write validation**: Scans entire output directory after write
- **Forbidden patterns**: 12+ regex patterns for Aadhaar, ABHA, PAN, phone, email, etc.
- **Replacement token allowlist**: [NAME], [PHONE], [UID], etc. not flagged
- **Checksum validation**: Verhoeff for Aadhaar/ABHA to reduce false positives
- **Quarantine on failure**: Files with residual PII are quarantined, not written

### 8. Confidence Calibration (`detection/calibration.py`)
- **Isotonic regression** calibrator for detector scores
- **Multi-detector manager** for per-detector calibration
- **Default conservative calibration**: Slightly reduces overconfident scores
- **Metrics**: ECE, MCE, Brier score computation
- **Persistence**: Pickle-based save/load for trained calibrators

## Test Results

```
73 passed, 9 skipped (Windows symlink tests)
```

## End-to-End Pipeline Test

```bash
$ RAKSHA_SECRET="practicesecretkeyfordevelopmenttestingonly123456" python main.py --input test_input --output test_output
```

**Input** (`test_input/patients.csv`):
```csv
patient_name,age,phone,aadhaar,diagnosis
Rahul Sharma,35,9876543210,123456789012,Diabetes
Priya Patel,28,9876543211,234567890123,Hypertension
Amit Kumar,42,9876543212,345678901234,Cardiology
```

**Output** (`test_output/sanitized/<sha256>.csv`):
```csv
patient_name,age,phone,aadhaar,diagnosis
[NAME],35,[PHONE],[UID],Diabetes
[NAME],28,[PHONE],[UID],Hypertension
[NAME],42,[PHONE],[UID],Cardiology
```

**Security Gate**: ✅ Passed (no residual PII in output)

## Known Limitations

1. **Gazetteer coverage**: Minimal built-in datasets; production needs comprehensive Indian name gazetteers
2. **Hinglish detection**: Rule-based only; could benefit from CRF/ML model
3. **Clinical disambiguation**: Limited to explicit "Dr." prefix + verb patterns
4. **FHIR metadata**: Only scans meta.tag, meta.security, Bundle.metadata
5. **Calibration**: Default conservative only; needs labeled data for proper training
6. **Performance**: Offset map composition could be optimized for large texts

## Next Steps (Phase 5+)

- [ ] Record linkage & pseudonymization (HMAC-SHA256 with RAKSHA_SECRET)
- [ ] Quasi-identifier generalization (date shifting, age banding, location generalization)
- [ ] k-anonymity / l-diversity measurement
- [ ] Full FHIR R4 validation and serialization
- [ ] CRF name tagger (conditional on >5% F1 gain)
- [ ] Performance optimization and memory profiling