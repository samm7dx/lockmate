#!/usr/bin/env python3
"""
Generate well-defined Architecture Diagram for LOCKMATE
Using graphviz for professional output
"""

from graphviz import Digraph
import os

# ─── Create Graph ───
dot = Digraph(
    'LOCKMATE_Architecture',
    filename='LOCKMATE_Architecture',
    format='png',
    engine='dot',
    graph_attr={
        'rankdir': 'TB',
        'splines': 'ortho',
        'nodesep': '0.6',
        'ranksep': '0.8',
        'fontname': 'Helvetica',
        'fontsize': '11',
        'bgcolor': 'white',
        'pad': '0.5',
        'margin': '0.2',
        'concentrate': 'true',
        'compound': 'true',
    },
    node_attr={
        'fontname': 'Helvetica',
        'fontsize': '10',
        'shape': 'box',
        'style': 'filled,rounded',
        'fillcolor': '#FFFFFF',
        'color': '#2E5C8A',
        'penwidth': '1.5',
        'margin': '0.15,0.08',
    },
    edge_attr={
        'fontname': 'Helvetica',
        'fontsize': '9',
        'color': '#2E5C8A',
        'penwidth': '1.2',
        'arrowsize': '0.8',
    }
)

# ─── Color Palette ───
COLORS = {
    'input': '#E8F4FD',           # Light blue
    'intake': '#FFF3E0',          # Light orange
    'parsing': '#FFF8E1',         # Light yellow
    'urm': '#E8F5E9',             # Light green
    'normalization': '#F3E5F5',   # Light purple
    'detection': '#FFEBEE',       # Light red
    'clinical': '#E0F2F1',        # Light teal
    'linkage': '#FCE4EC',         # Light pink
    'pseudo': '#E3F2FD',          # Light blue
    'privacy': '#FFF3E0',         # Light orange
    'serialization': '#F1F8E9',   # Light lime
    'security': '#FBE9E7',        # Light deep orange
    'output': '#E8EAF6',          # Light indigo
    'quarantine': '#FFCDD2',      # Red tint
}

# ─── Helper: Create styled node ───
def node(id, label, color_key='input', shape='box', **attrs):
    default_attrs = {
        'fillcolor': COLORS.get(color_key, '#FFFFFF'),
        'color': '#2E5C8A',
        'shape': shape,
        'style': 'filled,rounded',
        'fontname': 'Helvetica',
        'fontsize': '10',
        'penwidth': '1.5',
        'margin': '0.15,0.08',
    }
    default_attrs.update(attrs)
    dot.node(id, label, **default_attrs)


def edge(src, dst, label='', **attrs):
    default_attrs = {
        'color': '#2E5C8A',
        'penwidth': '1.2',
        'fontname': 'Helvetica',
        'fontsize': '9',
        'arrowsize': '0.8',
    }
    default_attrs.update(attrs)
    if label:
        default_attrs['label'] = label
        default_attrs['labelfontsize'] = '8'
        default_attrs['labelfontcolor'] = '#555555'
    dot.edge(src, dst, **default_attrs)


# ═══════════════════════════════════════════════════════
# NODES — Organized by Pipeline Stage
# ═══════════════════════════════════════════════════════

# Input
node('input_dir', 'INPUT DIRECTORY\n(Hospital Records)', 'input', shape='folder')
node('raksha_secret', 'RAKSHA_SECRET\n(Env Variable, ≥32 bytes)', 'input', shape='ellipse')

# Stage 1: Secure Intake
with dot.subgraph(name='cluster_intake') as c:
    c.attr(label='STAGE 1: SECURE INTAKE', style='dashed', color='#E65100', fontname='Helvetica-Bold', fontsize='10', pencolor='#E65100')
    node('discovery', 'File Discovery\n• Walk + symlink check\n• Path traversal protection', 'intake')
    node('hashing', 'SHA-256 Hashing\n(Streaming, 64-char hex)', 'intake')
    node('limits', 'Resource Limits\n• File ≤100 MB\n• Nesting ≤50\n• Decompression ≤100:1', 'intake')
    node('classifier', 'Format Classifier\n• Extension + content sniff', 'intake')

# Stage 2: Parsing → URM
with dot.subgraph(name='cluster_parsing') as c:
    c.attr(label='STAGE 2: PARSING → UNIFIED RECORD MODEL', style='dashed', color='#F9A825', fontname='Helvetica-Bold', fontsize='10', pencolor='#F9A825')
    node('csv_parser', 'CSV/TSV Parser\n• Auto-delimiter\n• Header inference\n• Quote handling', 'parsing')
    node('json_parser', 'JSON Parser\n• Schema-agnostic walk\n• Streaming (ijson)\n• JSON Pointer paths', 'parsing')
    node('fhir_parser', 'FHIR R4 Parser\n• fhir.resources validation\n• References, extensions\n• Contained, attachments', 'parsing')
    node('text_parser', 'Text Parser\n• Encoding detection\n• Line/paragraph segments', 'parsing')
    node('urm', 'UNIFIED RECORD MODEL (URM)\n• Source file hash, format, location\n• Field values, types, paths\n• Offset maps (norm ↔ orig)\n• Structural preservation', 'urm', shape='component')

# Stage 3: Unicode Normalization
with dot.subgraph(name='cluster_norm') as c:
    c.attr(label='STAGE 3: UNICODE NORMALIZATION', style='dashed', color='#6A1B9A', fontname='Helvetica-Bold', fontsize='10', pencolor='#6A1B9A')
    node('nfc', 'NFC Normalization', 'normalization')
    node('devanagari', 'Devanagari Digits → ASCII\n(०-९ → 0-9)', 'normalization')
    node('zwj', 'ZWJ/ZWNJ/BOM Handling', 'normalization')
    node('bidi', 'Bidi/Confusable Checks', 'normalization')
    node('offset_map', 'Offset Map Maintenance\n(norm_idx ↔ orig_idx)', 'normalization')

# Stage 4: PII Detection Engine
with dot.subgraph(name='cluster_detection') as c:
    c.attr(label='STAGE 4: PII DETECTION ENGINE', style='dashed', color='#C62828', fontname='Helvetica-Bold', fontsize='10', pencolor='#C62828')
    node('struct_det', 'Structured Field Scanner\n• CSV/TSV headers\n• JSON keys (JSON Pointer)\n• FHIR elements\n• Filenames', 'detection')
    node('id_det', 'Direct Identifier Detectors\n• Phone (phonenumbers + regex)\n• Aadhaar (Verhoeff)\n• ABHA (14-digit)\n• PAN (regex)\n• UHID/MRN (context)\n• Email, PIN, Dates', 'detection')
    node('name_det', 'Multilingual Name Detection\n• Honorific/Rel triggers\n• Gazetteers (Latin + Devanagari)\n• Transliteration + Double Metaphone\n• CRF tagger (conditional)\n• Role classification\n  (patient/relative/doctor)', 'detection')
    node('medical_veto', 'Medical Veto (Span-Level)\n• Drugs, dosages, frequencies\n• Labs, vitals, units\n• Diagnoses, procedures\n• Doctor names in context\n• Eponyms (Parkinson\'s)', 'clinical')
    node('residual', 'Second-Pass Residual Sweep\n• Re-scan sanitized text\n• Search known identifiers', 'detection')

# Stage 5: Identity Resolution
with dot.subgraph(name='cluster_linkage') as c:
    c.attr(label='STAGE 5: IDENTITY RESOLUTION & LINKAGE', style='dashed', color='#AD1457', fontname='Helvetica-Bold', fontsize='10', pencolor='#AD1457')
    node('blocking', 'Blocking Key Generation\n• Norm name (Latin)\n• Transliterated name\n• Double Metaphone\n• Phone, Aadhaar, ABHA, PAN\n• DOB year + gender\n• District + PIN prefix', 'linkage')
    node('candidates', 'Candidate Pair Generation\n• ≥1 shared key → pair\n• Deduplication\n• Pair count controlled', 'linkage')
    node('scoring', 'Pairwise Scoring\n(Fellegi-Sunter Inspired)\n• Exact ID match (very high)\n• Name Jaro-Winkler\n• Token overlap (Jaccard)\n• Transliterated similarity\n• Double Metaphone\n• Relative agreement\n• DOB, age, gender, geo', 'linkage')
    node('cannot_link', 'Cannot-Link Constraints\n• Conflicting Aadhaar/ABHA/PAN\n• Conflicting DOB/gender\n• Score = -∞', 'linkage')
    node('clustering', 'Conservative Clustering\n• Greedy by score desc\n• Cluster consistency check\n• NO transitive closure\n• Uncertain → null', 'linkage')
    node('canonical', 'Canonical Identity\n• Sorted reliable IDs\n• Pipe-joined key\n• Weak cluster → UUID+HMAC', 'linkage')

# Stage 6: Pseudonym Service
with dot.subgraph(name='cluster_pseudo') as c:
    c.attr(label='STAGE 6: PSEUDONYM SERVICE (CRYPTO)', style='dashed', color='#1565C0', fontname='Helvetica-Bold', fontsize='10', pencolor='#1565C0')
    node('secret_mgr', 'Secret Manager\n• Read RAKSHA_SECRET once\n• Memory only, no logging\n• HKDF domain separation', 'pseudo', shape='ellipse')
    node('hmac_pseudo', 'HMAC-SHA256 Pseudonym\n• canonical_identity + secret\n• Truncate 16B → base32\n• PSN-XXXXXXXX format\n• Null for uncertain', 'pseudo')
    node('date_shift', 'Date-Shift Derivation\n• HMAC(secret, "date_shift", pseudo)\n• Offset ∈ [-365, +365] days\n• Per-patient, deterministic', 'pseudo')
    node('rare_seed', 'Rare Suppression Seed\n• HMAC(secret, "rare_suppress")', 'pseudo')

# Stage 7: Privacy Transformations
with dot.subgraph(name='cluster_privacy') as c:
    c.attr(label='STAGE 7: PRIVACY TRANSFORMATIONS', style='dashed', color='#E65100', fontname='Helvetica-Bold', fontsize='10', pencolor='#E65100')
    node('date_transform', 'Date Shifting\n• All dates per patient\n• Intervals preserved\n• Timezone retained', 'privacy')
    node('age_bands', 'Age Generalization\n• 19 bands (0-4, 5-9, …, 90+)\n• Always round down\n• Unknown → null', 'privacy')
    node('location_gen', 'Location Generalization\n• Village → District\n• City → District\n• PIN → 3-digit prefix\n• Rare district → State', 'privacy')
    node('rare_suppress', 'Rare-Value Suppression\n• QI: {age_band, district,\n  gender, diag_cat, los_band}\n• Iterative: suppress rarest\n• Generalize age → location\n• k-anonymity diagnostic (k≥5)', 'privacy')
    node('attacker_sim', 'Attacker Simulation\n• Synthetic voter roll\n• Linkage attempt\n• Measure unique re-ID\n• Target: <5%', 'privacy')

# Stage 8: Serialization
with dot.subgraph(name='cluster_serial') as c:
    c.attr(label='STAGE 8: SERIALIZATION & OUTPUT', style='dashed', color='#33691E', fontname='Helvetica-Bold', fontsize='10', pencolor='#33691E')
    node('serializer', 'Format Serializer\n• CSV→CSV (dialect)\n• JSON→JSON (structure)\n• FHIR→valid R4\n• Text→Text', 'serialization')
    node('pseudo_inject', 'Pseudonym Injection\n• Add/replace patient ID field\n• PSN-XXXX in record', 'serialization')
    node('filename_san', 'Filename Sanitizer\n• SHA-256 prefix + ext\n• No PII in paths', 'serialization')
    node('atomic_write', 'Atomic Writer\n• Temp file → os.rename\n• Cleanup on error', 'serialization')

# Stage 9: Independent Security Gate
with dot.subgraph(name='cluster_gate') as c:
    c.attr(label='STAGE 9: INDEPENDENT OUTPUT SECURITY GATE', style='dashed', color='#BF360C', fontname='Helvetica-Bold', fontsize='10', pencolor='#BF360C')
    node('residual_scan', 'Residual PII Scan\n• Separate detector instance\n• High-confidence → FAIL', 'security')
    node('canary_check', 'Canary Check\n• LOCKMATE_CANARY_* absent\n• Output, logs, temp', 'security')
    node('clinical_check', 'Clinical Integrity\n• Medical spans pre/post\n• Corruption → FAIL', 'security')
    node('schema_check', 'Schema Validity\n• CSV/JSON parseable\n• FHIR R4 valid', 'security')
    node('meta_check', 'Filename/Metadata Safety\n• No PII in output paths\n• No PII in JSON keys', 'security')
    node('pseudo_check', 'Pseudonym Consistency\n• records.jsonl ↔ sanitized\n• Same patient = same pseudo', 'security')
    node('gate_result', 'GATE RESULT\nPASS → Publish\nFAIL → QUARANTINE', 'security', shape='diamond')

# Outputs
with dot.subgraph(name='cluster_outputs') as c:
    c.attr(label='OUTPUTS', style='dashed', color='#283593', fontname='Helvetica-Bold', fontsize='10', pencolor='#283593')
    node('sanitized', 'sanitized/\n• Preserved structure\n• Format fidelity\n• Pseudonyms injected\n• Safe filenames', 'output', shape='folder')
    node('report_json', 'report.json\n• Hash-keyed entries\n• Per-file metrics\n• Aggregate totals\n• No PII', 'output')
    node('records_jsonl', 'records.jsonl\n• file, loc, patient\n• Pseudonym consistency\n• Null for uncertain', 'output')
    node('quarantined', 'quarantined/\n• Original files copied\n• Reason codes\n• Explicit, never silent', 'quarantine', shape='folder')

# ─── EDGES — Pipeline Flow ───

# Input → Intake
edge('input_dir', 'discovery')
edge('raksha_secret', 'secret_mgr', style='dashed', color='#1565C0')

# Intake chain
edge('discovery', 'hashing')
edge('discovery', 'limits')
edge('discovery', 'classifier')
edge('classifier', 'csv_parser')
edge('classifier', 'json_parser')
edge('classifier', 'fhir_parser')
edge('classifier', 'text_parser')

# Parsing → URM
edge('csv_parser', 'urm')
edge('json_parser', 'urm')
edge('fhir_parser', 'urm')
edge('text_parser', 'urm')

# URM → Normalization
edge('urm', 'nfc')
edge('nfc', 'devanagari')
edge('devanagari', 'zwj')
edge('zwj', 'bidi')
edge('bidi', 'offset_map')

# Normalization → Detection (all parallel)
edge('offset_map', 'struct_det')
edge('offset_map', 'id_det')
edge('offset_map', 'name_det')
edge('offset_map', 'medical_veto')

# Detection internal
edge('struct_det', 'residual')
edge('id_det', 'residual')
edge('name_det', 'medical_veto', label='spans')
edge('id_det', 'medical_veto', label='spans')
edge('medical_veto', 'residual', label='filtered spans')

# Detection → Linkage
edge('name_det', 'blocking', label='PII spans + role')
edge('id_det', 'blocking', label='validated IDs')
edge('struct_det', 'blocking', label='structured IDs')

# Linkage chain
edge('blocking', 'candidates')
edge('candidates', 'scoring')
edge('scoring', 'cannot_link')
edge('cannot_link', 'clustering')
edge('clustering', 'canonical')

# Linkage → Pseudonym
edge('canonical', 'hmac_pseudo')
edge('secret_mgr', 'hmac_pseudo', style='dashed', color='#1565C0')
edge('secret_mgr', 'date_shift', style='dashed', color='#1565C0')
edge('secret_mgr', 'rare_seed', style='dashed', color='#1565C0')
edge('hmac_pseudo', 'date_shift', label='pseudo')

# Pseudonym → Privacy Transforms
edge('date_shift', 'date_transform')
edge('age_bands', 'age_bands')
edge('location_gen', 'location_gen')
edge('rare_seed', 'rare_suppress')

# Privacy → Serialization
edge('date_transform', 'serializer')
edge('age_bands', 'serializer')
edge('location_gen', 'serializer')
edge('rare_suppress', 'serializer')
edge('hmac_pseudo', 'pseudo_inject')
edge('offset_map', 'serializer', label='transformed URM')

# Serialization internal
edge('serializer', 'pseudo_inject')
edge('serializer', 'filename_san')
edge('pseudo_inject', 'atomic_write')
edge('filename_san', 'atomic_write')

# Atomic Write → Security Gate
edge('atomic_write', 'residual_scan')
edge('atomic_write', 'canary_check')
edge('atomic_write', 'clinical_check')
edge('atomic_write', 'schema_check')
edge('atomic_write', 'meta_check')
edge('atomic_write', 'pseudo_check')

# Security Gate → Result
edge('residual_scan', 'gate_result')
edge('canary_check', 'gate_result')
edge('clinical_check', 'gate_result')
edge('schema_check', 'gate_result')
edge('meta_check', 'gate_result')
edge('pseudo_check', 'gate_result')

# Gate Result → Outputs
edge('gate_result', 'sanitized', label='PASS')
edge('gate_result', 'quarantined', label='FAIL', color='#C62828', fontcolor='#C62828')
edge('gate_result', 'report_json')
edge('gate_result', 'records_jsonl')

# ─── Legend / Annotations ───
# Add invisible nodes for legend-like annotations
dot.node('legend1', '', shape='plaintext', fontsize='9')
dot.node('legend2', '', shape='plaintext', fontsize='9')

# ─── Render ───
output_path = r'C:\Users\samri\lockmate\LOCKMATE_Architecture'
dot.render(output_path, cleanup=True, view=False)
print(f"Architecture diagram generated: {output_path}.png")

# Also generate SVG for scalability
dot.format = 'svg'
dot.render(output_path, cleanup=True, view=False)
print(f"Architecture diagram generated: {output_path}.svg")

# Generate a high-DPI PNG for presentations
dot.format = 'png'
dot.graph_attr['dpi'] = '300'
dot.render(output_path + '_hd', cleanup=True, view=False)
print(f"High-DPI diagram generated: {output_path}_hd.png")