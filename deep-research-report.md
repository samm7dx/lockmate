# LOCKMATE (Track 3: Secret Wards) – Strategy and Plan

We are building **LockMate**, an offline healthcare privacy firewall that ingests multilingual hospital records, removes all personal identifiers, links records by patient, and outputs fully de-identified data without leaking any raw PII. The official requirements are very strict (no leaks, offline-only, stable pseudonyms, valid FHIR output, etc.), so our plan must be **contract-first** and **attack-focused**. In particular, we must defend against a motivated attacker who can combine our sanitized output with external data (e.g. public voter rolls) to re-identify patients. As HIPAA guidance reminds us, even “de-identified” data carries non-zero re-identification risk, and any identifier (name, address, date) tied to health data counts as PHI. Our priorities will be: (1) **No leaks or crashes** (fail-safe design and quarantine), (2) **Exact medical data preservation** (never redact clinical values by mistake), (3) **Maximal PII removal/obfuscation**, and (4) **Clear evidence of protection** (metrics, audit logs, test cases). 

Below is a detailed, stage-by-stage plan, combining contract compliance, best practices, and references to standards and literature.

---

## Stage 0 – Contract & Baseline  
- **Output Contract:** Begin with the exact required output format. Write a stub `main.py` and `raksha.toml` that immediately pass the validator by quarantining everything. This ensures `python3 validate_output.py --input dev/input --output out/` yields `CONTRACT OK` on an empty or dummy run, so we score non-zero and avoid disqualification.  
- **Scoring Harness:** Load the practice dataset (and ground truth, if available) into an evaluation script. Measure key metrics: PII detection recall/precision, medical-field preservation, linkage F1, and performance (time/memory). This feedback loop will guide development.  
- **Fail-safe rule:** Implement a top-level exception handler: if any file or record triggers an uncaught error, **quarantine it** (mark `"status":"quarantined"` with an explanatory reason) rather than crash or release partial data. This satisfies “never silently skip or copy raw data.”  

*Rationale:* A baseline that never leaks raw data (even if it does nothing useful) avoids catastrophic failure. From here we will progressively unlock functionality while preserving this fail-safe layer.

---

## Stage 1 – Robust Ingestion  
- **File Discovery:** Recursively walk input folders. For each file, compute its SHA-256 and record it (for `report.json` entries and deterministic processing).  
- **Encoding and Format Detection:** Use `charset-normalizer` or similar to detect encoding, default to UTF-8 with BOM, or common encodings (UTF-16, Latin-1, CP1252). If a file decodes to text, proceed; otherwise **quarantine** (e.g. PDF, image).  
- **Structured vs Text Parsing:** Classify files by extension or sniffing:
  - **CSV/TSV:** Use `csv` or Pandas with automatic delimiter detection. Tolerate extra columns (if a header is missing or columns shifted, rely on content matching rather than position).  
  - **JSON:** Load with Python’s JSON or `jsonschema`; walk nested objects/arrays. Also handle **FHIR R4** bundles (validating with `fhir.resources` library).  
  - **Plain Text:** Process as unstructured note (UTF-8 text).  
  - **Unknown Binary or Broken:** Quarantine (with reason “unsupported or corrupted file”).  
- **Key Insight:** We will build an **internal unified record model**, e.g. represent every file as a list of “records” each with named fields (for structured data) and unstructured text (notes). This lets us apply the same PII detectors to everything. Also **scan metadata and filenames** for PII: if a filename or JSON key (e.g. `"patient_name"`) looks like an identifier, handle it. (A hidden-PII trap is metadata.)  

*Rationale:* Robust parsing ensures we handle every format or safely quarantine it. Early detection of PII in filenames or keys prevents holes. (The HIPAA FAQ even notes that *names in free text* must be removed, so we must also treat JSON keys/headers as containing PHI.)

---

## Stage 2 – PII Detection and Redaction Engine  
We layer several detectors and a medical “whitelist” to avoid false positives. We will iterate on false-negative cases using the practice labels.

1. **Numeric Identifiers (High-Precision Rules):**  
   - **Phone Numbers:** Use Google’s `phonenumbers` for India (+91 formats) and regexes covering 10–12 digit variants with optional country codes. Handle spaces and Hindi digits by mapping Devanagari→ASCII. Only redact if structure matches (e.g. 10 digits starting with 6–9) or if near a phone keyword (e.g. “Mobile:”).
   - **Aadhaar-like IDs:** 12 digits with Verhoeff checksum (India’s UID), and **ABHA (Ayushman Bharat) IDs** (14 digits). **PAN numbers:** 5 letters + 4 digits + 1 letter (regex). UHID/MRN formats: patterns from practice set, plus context cues (“UHID:”, “MRN:”).  
   - **Email and Web:** Standard regex for emails; URLs/IPs (these often indicate personal accounts or locations).
   - **Spatial Identifiers:** Indian PIN codes (6 digits), postal addresses (regex for “village|district|taluk”), coarsely flag street addresses.  
   - **Dates and Numbers:** Use `dateparser` to find dates. *Safe Harbor forbids day/month of any health-related date*, so plan to **remove or shift all but the year**. Lab values (like “5 mg”, “101”) must be whitelisted to avoid mis-detection as IDs (the “Meaning Trap”).  

2. **Name and Entity Detection:** (Hardest part)  
   - **Trigger Words:** Pattern-match common relational markers: `S/o`, `D/o`, `W/o`, “C/O <Name>”, or honorifics (“Mr.“, “Ms.“, “Shri”, “ji”). If “C/O” is followed by a symptom word (from a symptom gazetteer), treat it as a complaint, not a relative. 
   - **Gazetteers:** Compile large lists of Indian first names and surnames in both Latin and Devanagari (including variants: Mohammad, Mohammed, Mohd., मोहम्मद). Also include common honorifics/surnames (“Patel”, “Rao”, etc.) from public data (e.g. Indian census names). No hardcoded patient-specific names.  
   - **CRF Tagger:** Train a small conditional-random-field model (e.g. `sklearn-crfsuite`) on the practice data: features include token shape, script (Devanagari vs Roman), gazetteer membership, and local context (e.g. words before/after). This helps catch mixed “Hinglish” like “दिल्ली में Rahul है”.  
   - **Whitelists (Medical/Other Protections):** Build lists of protected terms that should *not* be removed even if they look like names: diseases (Parkinson’s, TB, HIV, etc., including eponyms like Alzheimer), drug names and dosages (“Dolo 650”, “Paracetamol”), medical titles (“Dr. Smith”), labs (“HbA1c”). If a word is in the gazetteer *and* on the medical whitelist, treat it as medical (keep it) **unless** clear context marks it as a name (e.g. preceded by S/o or listed under “Patient Name”).  
   - **Document-level consistency:** Within one file, propagate decisions: e.g. if “Meera Kumari” at top is marked as patient name, then all later mentions “Meera” or “Ms. Kumari” are also redacted (or replaced with the same pseudonym). This prevents partial unmasked mentions.  

3. **Replacement Strategy:** For each detected PII span, replace with a token or pseudonym:
   - Direct identifiers (names, phone, Aadhaar) → `[NAME]`, `[PHONE]`, `[UID]`, etc. or better, use the patient’s pseudonymous ID (see linkage) consistently.  
   - PIN/village → generalize (see next stage).  
   - Dates → we will shift them rather than mask (below).  
   - Uncertain or rare quasi-ID values → mask (e.g. age → bracket).  
   - *Any* failed parse or detection? Quarantine.  

4. **Second-pass Sweep:** After initial redaction, re-scan the sanitized text for any remaining high-confidence PII. Also search for the patient’s own identifiers (name variants, phone, etc.) collected from step 2, to catch anything missed. Redact any stragglers. If anything obviously PII remains (e.g. name fragments), quarantine the file.  

> *“Pseudonymization is a category of de-identification that enables linking of records without revealing identities”*. We generate patient IDs with `PSN-XXXX`: compute `HMAC-SHA256(RAKSHA_SECRET, canonical_patient_key)` and encode (e.g. base32). This is a **one-way pseudonym** (like tokenization). A different secret yields different IDs. We never use hashes of plaintext names alone (no deterministic hashing without key). All replacements are deterministic given the secret, ensuring reproducibility.

---

## Stage 3 – Medical Data Protection (Category 3)  
Before or during redaction, protect medical content so our PII removal doesn’t harm it:
- **Prescription and Dosage Regex:** Identify patterns like `\d+ mg`, `\d+\s*U`, `once daily (OD)`, etc. Temporarily tag them “MED-KEEP” so our name/number detectors ignore numeric doses.  
- **Disease Names:** Compile an ICD-10-derived list of common diagnoses and body parts; preserve them verbatim (unless they also appear as a person’s name, in which case context wins).  
- **Vocabulary Cues:** If a token appears to be a measurement or lab value (e.g. “Hb”, “BP”, “mg/dL”), do not redact the surrounding number. Conversely, after initial redact, if a redacted span is adjacent to a medical term, double-check it’s real PII.  

This **medical whitelist/veto** ensures we minimize Category-3 penalties by *never* deleting or corrupting clinical facts. For example, “Parkinson’s disease” stays intact; “Dr. Ramesh” the doctor stays (“Dr.” clues doctor), but “Rahul” as patient or relative is redacted. 

*Citing guidance:* HIPAA’s Safe Harbor explicitly bans sharing detailed dates and ages beyond what is safe; we will suppress or adjust these (next stage) rather than removing necessary medical details. The goal is to **preserve clinical truthfulness** while blocking identity cues.

---

## Stage 4 – Patient Linking and Pseudonyms (Category 4)  
The system must cluster records by patient and assign one pseudonym per patient. This is very tricky, so we adopt a **high-precision, conservative linkage**:

- **Blocking:** First, only compare records that share a plausible key: e.g. the same full phone number, same ABHA, or the same Soundex/Metaphone code of their (romanized) name. Transliterate Devanagari names to Latin (e.g. using `indic-transliteration`), then apply Double Metaphone to allow matching across spelling/script. This limits comparisons and picks up “Mohammad”~“मुहम्मद”.  
- **Pairwise Scoring:** For a candidate pair, compute similarity features: Jaro–Winkler or Levenshtein on normalized names, exact match on birth year or hospital ID, exact match on phone/Aadhaar, gender match, age difference within a plausible range (e.g. <2 years), village/PIN proximity. Use Fellegi–Sunter style likelihood scoring: common attributes (like matching Aadhaar) get high weight, rare coincidences (full-name+birthday) also get weight, while common names/villages get less.  
- **Thresholding and Transitive Closure:** Only link if the weighted score exceeds a high threshold (favor precision). Impose *cannot-link* rules: e.g. if two records have conflicting fixed IDs or very different DOB/gender, force `patient: null`. If A~B and B~C with high confidence, we tentatively group them *only if* A~C also scores well; do **not** blindly merge by chaining. In practice, we can use a simple greedy clustering: sort record pairs by score, merge clusters if all linking evidence within is consistent.  
- **Null Policy:** If any record is not confidently linked to an existing cluster, we do *not* create a new cluster ID from partial evidence. Instead, we set `"patient": null` for that record (and possibly quarantine it if it still has identifiers), per rules. It is better to miss linking than to create a false match.  

Once clusters are formed, assign each cluster a pseudonymous ID: e.g. `PSN-XXXX`. We use a canonical key (e.g. sorted concatenation of all reliable identifiers for that patient) hashed with HMAC-SHA256 and truncated. This ensures the same patient ID appears everywhere they appear, but is irreversible. If a cluster has no strong identifier, we may generate a random UUID HMAC’d for consistency.

---

## Stage 5 – Quasi-Identifier Protection (Category 1)  
With direct IDs gone, attackers might use indirect clues. We apply HIPAA-style generalization and shifting:

- **Dates:** HIPAA Safe Harbor forbids revealing exact dates. We **shift all dates per patient** by a fixed offset (derived from HMAC-secret), e.g. +n days, so that *intervals* (like hospital stay length or age difference) are preserved exactly. This hides actual day/month while preserving data utility. For ages, implement 5- or 10-year age bands (always rounding *down* into the band) so the true age is contained within the bracket. Ages ≥90 become “90+” (HIPAA rule).  
- **Locations:** Generalize geo-identifiers. For example, map village or city names to district-level, and truncate PIN codes to the first 3 digits or suppress rare PINs. This ensures any remaining locality has ≥k patients.  
- **Rare Values:** Detect rare combinations of quasi-identifiers (e.g. a unique age–disease–location tuple). If any small group remains (k<5 by some quick measure), apply local suppression: e.g. replace a rare diagnosis with its parent category, or further generalize the age band. We can use a library like `pandas` or `pyanon` to measure k-anonymity after transformation and decide if another generalization step is needed.  

We will **simulate a re-identification attack** to validate this. For instance, take the sanitized output and a mock “voter list” (name, age, village) and see if any sanitized patient cluster has a unique match. We tune our generalization until the simulated attacker success rate is acceptably low. This evidence will go in our brief. (HIPAA and research on k-anonymity note that there’s always some residual risk; our goal is to show it’s minimal.) 

---

## Stage 6 – Output Generation and Audit  
- **Sanitized Files:** Write sanitized files with the same names (in UTF-8). Preserve structure/format (CSV→CSV, JSON→JSON, FHIR→FHIR). For JSON/FHIR, ensure validity (e.g. dates replaced by valid strings). For each record in each file, ensure the only identifiers left are replaced tokens or pseudonyms.  
- **Quarantine:** Any file we could not safely sanitize (unsupported format, repeated parse errors, unrecoverable PII) goes to `sanitized/quarantined/` with original name, and an entry in `report.json` with `"status":"quarantined"`. The reason (e.g. “Unsupported format”, “Binary file”, “Residual name detected”) should be logged in `report.json` for audit.  
- **Report.json:** As required, one entry per input file by hash. Include original path, output path(s), counts of sanitized/quarantined records, PII counts, and timings. Use **true measured values**. HIPAA guidance insists reports must be accurate.  
- **Records.jsonl:** For each patient cluster, one line with fields: `patient_pseudonym` (or null), and a mapping of each file record location (e.g. `fileA.csv row:3`, `fileB.json #2`) to that patient. This enables checking that all instances were linked correctly.  

*No PII in logs or reports:* Log only hashes and counts. Never echo raw text. If using a logger, scrub or mask any string that matches our detectors. Also never write the secret or keys anywhere.

---

## Stage 7 – Testing, Hardening, Performance  
- **Official Validator:** Continuously run `validate_output.py` on our output. We must ultimately get `CONTRACT OK` on all practice inputs. Use the validate script’s feedback to fix formatting issues (e.g. FHIR schema errors, missing fields, encoding).  
- **Unit and Integration Tests:** Write pytest tests for core components: detectors on sample strings, linkage logic on small tables, date shifting reproducibility, etc. Use adversarial examples (e.g. “C/O fever” vs “C/O Ramesh”).  
- **Performance:** Track CPU and memory (within 4GB, 2 CPUs). Optimize heavy loops (vectorize with pandas, avoid exponential link comparisons via blocking). The system has 15 minutes per run; aim to process in <10.  
- **Determinism:** Ensure runs are identical given same secret: e.g. sort file lists, disable nondeterministic RNG, freeze random seeds. Then re-run with a different `RAKSHA_SECRET` and confirm outputs differ (pseudonyms and date shifts must change).  
- **Canary Strings:** Insert a few fake unique identifiers into practice data (like a made-up name not in our code) and ensure our pipeline catches them. After a full run, `grep` the output files and logs for those strings; none should appear.

---

## Stage 8 – Demonstration and Documentation  
- **Demo Scenario:** Prepare a small synthetic dataset showing: (1) Input files across languages (English/Hindi) with obvious PII, (2) Running LockMate and showing files move through stages, (3) A screen showing a before/after of a sample record highlighting what was removed/preserved (e.g. name→PSN, DOB→shifted, village→district). For judges, the narrative is: “Authorized run produces sanitized outputs; then change one record’s identity slightly (like change name or unshifted date) and show it gets quarantined or denied.”  
- **Threat Model:** Outline assumptions and attacker capabilities (external lists, no insider access). Show that even with **“actual knowledge”** (HIPAA phrase) of our methods, our output resists linking back.  
- **Evaluation Checklist:** Prepare a checklist to verbally confirm during demo: (a) All file hashes are reported. (b) `report.json` shows expected counts, no unreported data. (c) The official validator passed. (d) A revocation test: modify RAKSHA_SECRET and re-run to show different pseudonyms. (e) A consistency test: two runs with same secret yield identical outputs.  
- **Metrics for Brief:** Include our measured privacy–utility trade-offs. For instance, “post-sanitization, 97% of lab values and medication names are preserved (vs 0% PII leakage), and attacker k-anonymity is k≥5 for 95% of records (vs k=1 if we only removed names)”. Show a small table of “before vs after” anonymization for key fields.  
- **Honesty:** Emphasize known limitations: e.g. “If an attacker had outside biometric or unmodeled data, re-ID risk is not zero.” But we have done expert-level de-id (both rule-based and statistical) to minimize this. The brief should admit residual risk and how our design mitigates it.

---

## Key References and Rationale

- **HIPAA & De-ID:** Personal identifiers tied to health data (names, address, exact birthdates) must be removed. Safe Harbor explicitly forbids revealing day/month of any health date. Even so-called “de-identified” data can be re-linked; our privacy engineer’s job is to make that risk “very small”.  
- **Pseudonymization:** Replace patient IDs with cryptographic pseudonyms so different records can still be linked without revealing identity. One-way HMAC (e.g. HMAC-SHA256) is industry-standard for tokens.  
- **Record Linkage:** Use probabilistic matching. The Fellegi–Sunter model is the classic foundation for such linkage. We’ll implement its spirit: combine agreement on multiple fields with thresholding. We will avoid naive closure to prevent transitive false matches.  
- **Multilingual Matching:** Since records use both English and Hindi, we transliterate Hindi names to Latin and then apply phonetic encoding. The Double Metaphone algorithm is designed to handle “a wide range of languages”, making it suitable for Indian names. We will use or adapt such phonetic codes for blocking/matching.  
- **Sequential Processing:** The official checkers run our pipeline as a single program, so we must organize this logic in modular Python functions (ingest, detect, link, generalize, emit). Each step should log timing to meet reporting.  

## What to Avoid

- **No LLM/Transformer:** The rules forbid large language models or generative AI. We will not rely on any large pretrained model. Instead, we use rule-based NLP, small CRFs, and gazetteers (all well under 50M parameters).  
- **No Experimental Crypto:** Use only standard libraries (`cryptography` for HMAC, AES-GCM). Don’t invent custom schemes.  
- **No Half-Measures:** Do *not* leave obvious PII in output. For example, don’t just blank names without also blanking IDs. Every potential identifier in content, metadata, filenames or JSON keys must be handled. Judges will check that even indirect clues (e.g. exact stay-length, or an unusual age-location combo) are addressed.  
- **No Silent Failures:** If a file can’t be processed, we must quarantine it *explicitly*, not ignore it. And we must report it in `report.json`. A silent skip is a major deduction.  

## Summary

In short, LockMate will be a carefully engineered pipeline that **never copies raw data**, **protects clinical content**, and **defends against re-identification**. By building it one verified stage at a time, and continuously testing against practice inputs (and custom adversarial cases), we ensure correctness. Our demo will highlight both *functionality* (the cleaned data still looks medically meaningful) and *security* (attacks fail and logs/audit prove it). This focused, contract-driven approach—rather than chasing flashy ML—gives us the best chance to score high on all judges’ criteria, especially privacy correctness and verifiability. 

**Sources:** Official HIPAA de-identification guidance; IHE/FHIR de-id handbook (pseudonymization); Google Cloud docs (HMAC tokens); Splink phonetic docs (Double Metaphone); Record linkage theory. These guide our design choices at each step.