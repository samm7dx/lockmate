#!/usr/bin/env python3
"""
Generate 2-page Project Brief PDF for LOCKMATE
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, HRFlowable
)
from reportlab.platypus.flowables import Flowable
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# ─── Colors ───
DARK_BLUE = HexColor("#1B2A4A")
MED_BLUE = HexColor("#2E5C8A")
LIGHT_BLUE = HexColor("#D6E8F7")
ACCENT_ORANGE = HexColor("#E87722")
ACCENT_GREEN = HexColor("#2A7F2A")
ACCENT_RED = HexColor("#C0392B")
GRAY_BG = HexColor("#F5F5F5")
DARK_GRAY = HexColor("#333333")
MED_GRAY = HexColor("#666666")
LIGHT_GRAY = HexColor("#CCCCCC")

# ─── Custom Styles ───
styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    'CustomTitle', parent=styles['Title'],
    fontSize=18, leading=22, textColor=DARK_BLUE,
    spaceAfter=2, alignment=TA_CENTER, fontName='Helvetica-Bold'
)

subtitle_style = ParagraphStyle(
    'CustomSubtitle', parent=styles['Normal'],
    fontSize=10, leading=12, textColor=MED_BLUE,
    spaceAfter=6, alignment=TA_CENTER, fontName='Helvetica-Oblique'
)

section_style = ParagraphStyle(
    'Section', parent=styles['Heading2'],
    fontSize=11, leading=14, textColor=DARK_BLUE,
    spaceBefore=10, spaceAfter=3, fontName='Helvetica-Bold',
    borderWidth=0, borderPadding=0,
)

subsection_style = ParagraphStyle(
    'SubSection', parent=styles['Heading3'],
    fontSize=9.5, leading=12, textColor=MED_BLUE,
    spaceBefore=5, spaceAfter=2, fontName='Helvetica-Bold'
)

body_style = ParagraphStyle(
    'CustomBody', parent=styles['Normal'],
    fontSize=8, leading=10.5, textColor=DARK_GRAY,
    spaceAfter=2, alignment=TA_JUSTIFY, fontName='Helvetica'
)

bullet_style = ParagraphStyle(
    'CustomBullet', parent=body_style,
    leftIndent=14, bulletIndent=5, spaceAfter=1,
    fontSize=8, leading=10.5
)

small_style = ParagraphStyle(
    'Small', parent=body_style,
    fontSize=7, leading=9, textColor=MED_GRAY
)

table_header_style = ParagraphStyle(
    'TableHeader', parent=body_style,
    fontSize=7, leading=9, textColor=white, fontName='Helvetica-Bold',
    alignment=TA_CENTER
)

table_cell_style = ParagraphStyle(
    'TableCell', parent=body_style,
    fontSize=7, leading=9, textColor=DARK_GRAY, alignment=TA_LEFT
)

table_cell_center = ParagraphStyle(
    'TableCellCenter', parent=table_cell_style,
    alignment=TA_CENTER
)


# ─── Helper: Colored Section Bar ───
class SectionBar(Flowable):
    def __init__(self, width, height=3, color=ACCENT_ORANGE):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.color = color

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.rect(0, 0, self.width, self.height, fill=1, stroke=0)


def make_table(headers, rows, col_widths=None):
    """Create a styled table."""
    header_row = [Paragraph(h, table_header_style) for h in headers]
    data = [header_row]
    for row in rows:
        data.append([Paragraph(str(c), table_cell_style) for c in row])

    if col_widths is None:
        col_widths = [None] * len(headers)

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('BACKGROUND', (0, 1), (-1, -1), white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, GRAY_BG]),
        ('GRID', (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    return t


def build_pdf(output_path):
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=12*mm, rightMargin=12*mm,
        topMargin=10*mm, bottomMargin=10*mm
    )
    story = []
    page_width = A4[0] - 24*mm

    # ═══════════════════════════════════════════════════
    # PAGE 1 — HEADER + ARCHITECTURE + USP
    # ═══════════════════════════════════════════════════

    # Title Block - more compact
    story.append(Paragraph("LOCKMATE", title_style))
    story.append(Paragraph("Offline Healthcare Privacy Firewall — Secret Wards Track 3", subtitle_style))
    story.append(SectionBar(page_width, 2, ACCENT_ORANGE))
    story.append(Spacer(1, 2))

    # ── ARCHITECTURE ───────────────────────────────────
    story.append(Paragraph("System Architecture", section_style))
    story.append(SectionBar(page_width, 1, MED_BLUE))

    arch_text = (
        "LOCKMATE is a <b>contract-first, attack-focused privacy firewall</b> ingesting "
        "heterogeneous Indian hospital records (CSV, TSV, JSON, FHIR R4, plain text), "
        "removing all PII, linking same-patient records across hospitals/scripts/formats via "
        "<b>conservative identity resolution</b>, applying deterministic pseudonymization and "
        "quasi-identifier protection, emitting de-identified outputs matching the organizer's exact contract."
    )
    story.append(Paragraph(arch_text, body_style))

    story.append(Paragraph("Pipeline Stages", subsection_style))

    stages = [
        ("1. Secure Intake", "File discovery, SHA-256, resource limits (100MB/50 nest/100:1), format classification"),
        ("2. Parsing → URM", "CSV/TSV/JSON/FHIR/text → Unified Record Model preserving structure for lossless serialization"),
        ("3. Unicode Normalization", "NFC, Devanagari digits→ASCII, ZWJ/ZWNJ, bidi checks, offset-map maintenance"),
        ("4. PII Detection Engine", "Structured fields + direct IDs (phone, Aadhaar, ABHA, PAN, UHID) + multilingual names (gazetteer + transliteration + Double Metaphone + optional CRF)"),
        ("5. Clinical Preservation", "Span-level medical veto: drugs, dosages, labs, vitals, diagnoses, procedures, doctor names in context"),
        ("6. Identity Resolution", "Blocking keys → pairwise scoring (Fellegi-Sunter) → cannot-link → greedy clustering (no transitive closure) → null for uncertain"),
        ("7. Pseudonym Service", "Canonical identity (sorted reliable IDs) → HMAC-SHA256(RAKSHA_SECRET) → PSN-XXXX; null for uncertain"),
        ("8. Privacy Transforms", "Per-patient date shift ([-365,+365]), age bands (19, round-down), location generalization (village→district→state, PIN→3-digit), rare suppression (k≥5)"),
        ("9. Serialization", "URM → original format, pseudonym injection, filename sanitization (SHA-256 prefix), atomic write"),
        ("10. Independent Security Gate", "Separate validator: residual PII, canary, clinical integrity, schema, metadata, pseudonym consistency — FAIL → quarantine"),
    ]

    for title, desc in stages:
        story.append(Paragraph(f"<b>{title}</b> — {desc}", bullet_style))

    story.append(Spacer(1, 1))

    # Key Architectural Invariants - compact
    story.append(Paragraph("Key Architectural Invariants", subsection_style))
    invariants = [
        "Unified Record Model preserves structure for lossless round-trip serialization",
        "Offset mappings enable safe in-place replacement after Unicode normalization",
        "Independent Output Security Gate — file safe only after separate validation",
        "No raw intermediates on disk; AES-GCM encrypt temp files if unavoidable",
        "Deterministic pipeline — same input + same secret = byte-identical output",
        "Conservative linkage — false merge catastrophic; missed link acceptable",
    ]
    for inv in invariants:
        story.append(Paragraph(f"• {inv}", bullet_style))

    # ── USP ────────────────────────────────────────────
    story.append(Spacer(1, 4))
    story.append(Paragraph("Unique Selling Proposition (USP)", section_style))
    story.append(SectionBar(page_width, 1, ACCENT_GREEN))

    usp_items = [
        ("Cross-Script Identity Intelligence",
         "Links same patient across English, Devanagari Hindi, Hinglish via transliteration + Double Metaphone + gazetteers — stable pseudonym across hospitals/scripts."),
        ("Contextual Clinical Integrity",
         "Span-level medical veto preserves <b>drugs, dosages, diagnoses, labs, vitals, procedures</b> adjacent to redacted names (e.g., \"Rahul 5 mg\" → \"[PSN-A1B2C3D4] 5 mg\"). Contextual, adversarially tested."),
        ("Attacker-Aware Privacy Shield",
         "Per-patient HMAC date shifts, age bands, location hierarchy, k-anonymity diagnostic with <b>synthetic voter-roll attacker simulation</b> (<5% re-ID target). Independent gate + canary testing every run."),
        ("Offline, CPU-Only, Deterministic",
         "Zero network, no GPU, no LLMs >50M params. Same input + same secret = byte-identical output. Verified by 3-run determinism + secret-rotation tests."),
        ("Contract-First Engineering",
         "Every CLI flag, output field, schema key, env var matches organizer spec exactly. `validate_output.py` → `CONTRACT OK` is acceptance gate."),
    ]

    for title, desc in usp_items:
        story.append(Paragraph(f"<b>{title}</b>", subsection_style))
        story.append(Paragraph(desc, body_style))

    # ═══════════════════════════════════════════════════
    # PAGE 2 — PRIVACY-UTILITY TRADE-OFFS + LIMITATIONS
    # ═══════════════════════════════════════════════════
    story.append(PageBreak())

    story.append(Paragraph("Privacy–Utility Trade-offs", section_style))
    story.append(SectionBar(page_width, 1, ACCENT_ORANGE))

    tradeoff_text = (
        "LOCKMATE makes explicit, measurable trade-offs between privacy and clinical utility. "
        "Each transform preserves medical signal while breaking linkage attacks — "
        "<b>configurable, auditable, validated against synthetic attacker simulation</b>."
    )
    story.append(Paragraph(tradeoff_text, body_style))

    # Trade-off Table
    tradeoff_headers = ["Transform", "Privacy Gain", "Utility Cost", "Mitigation / Validation"]
    tradeoff_rows = [
        ["Pseudonymization (HMAC-SHA256)", "Breaks direct name/ID linkage", "Loss of patient name for cohorts", "Stable pseudonym enables longitudinal analysis; cross-hospital linkage preserved"],
        ["Per-Patient Date Shift (±365d)", "Hides exact dates from quasi-ID attacks", "Absolute timeline lost; intervals exact", "Clinical intervals (LOS, drug duration, follow-up) remain accurate"],
        ["Age Generalization (19 bands)", "Reduces age granularity for k-anonymity", "Exact age unavailable; coarse at extremes", "Bands align with clinical strata; 90+ ceiling protects elderly"],
        ["Location Generalization", "Breaks village-level re-ID via voter rolls", "Fine-grained geo analysis lost", "District-level sufficient for public health; rare suppression only if k<5"],
        ["Rare-Value Suppression (k≥5)", "Eliminates unique QI combinations", "Some records lose diagnosis/geo detail", "Iterative: suppress rarest first; diagnostic k-anonymity reported per run"],
        ["Conservative Linkage (null)", "Prevents false merges (catastrophic)", "Same patient → multiple pseudonyms", "False-merge <1% target; missed links accepted; null records flagged"],
        ["Clinical Veto (span-level)", "Prevents over-redaction of medical values", "Risk: context misclassified → name kept", "Adversarial tests: \"Parkinson's\" kept, \"Patient Parkinson\" redacted; 0% corruption target"],
    ]

    col_widths = [38*mm, 36*mm, 38*mm, 58*mm]
    story.append(make_table(tradeoff_headers, tradeoff_rows, col_widths))

    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "<b>Measurement:</b> Every run reports clinical utility (>95% medical spans preserved), "
        "k-anonymity distribution, and attacker simulation unique re-ID rate (<5% target). "
        "Trade-offs are transparent and auditable.",
        body_style
    ))

    # ── LIMITATIONS ────────────────────────────────────
    story.append(Spacer(1, 6))
    story.append(Paragraph("Known Limitations & Residual Risks", section_style))
    story.append(SectionBar(page_width, 1, ACCENT_RED))

    limitations = [
        ("Multilingual Name Ambiguity", "Transliteration variants (Mohammed/मोहम्मद/Mohd.) may cause false merges/missed links. Mitigated by strict cannot-link (conflicting Aadhaar/DOB/gender) and high clustering thresholds; cross-script disambiguation remains probabilistic."),
        ("Gazetteer Coverage Gaps", "Bundled Indian name gazetteers (Census 2011, public lists) miss regional/rare names. Unseen names use honorific/relationship triggers and optional CRF. Residual leakage caught by second-pass sweep and security gate."),
        ("FHIR R4 Complexity", "References, contained resources, extensions, Base64 Binary attachments present large attack surface. Deep traversal implemented; attachments quarantined. Custom extension edge cases may leak metadata — quarantine on validation failure is backstop."),
        ("Clinical Veto Over-Preservation", "Eponymous diseases (Parkinson's, Alzheimer's, Crohn's) share surnames with patients. Context window + role markers (S/o, Dr., C/O) reduce false preservation; adversarial cases like \"Patient Parkinson admitted\" need continuous test expansion."),
        ("Date-Shift Reversibility", "HMAC-SHA256 128-bit output truncated to 32-bit offset. Attacker knowing algorithm but not secret faces 2¹²⁸ brute force — infeasible. No practical reversal without secret; secret never leaves memory."),
        ("Pseudonym Collision", "8-char base32 = 40 bits. For 10⁶ patients, collision probability ~10⁻⁶ (negligible). Canonical identity includes hard IDs (Aadhaar, phone) when available, further reducing risk."),
        ("k-Anonymity ≠ Anonymity Proof", "k-anonymity is a <b>diagnostic only</b>, not formal guarantee. Attacker simulation with synthetic voter rolls gives empirical risk (<5% unique re-ID target); real auxiliary data may differ. No differential privacy claimed."),
        ("Resource Constraints", "15 min / 4 GB RAM / 2 CPU hard limits. Streaming, blocking, profiling target 10 min / 1.5 GB peak. Large FHIR bundles or deep JSON may approach limits; quarantine on exceedance is safety valve."),
        ("No Organizer Validator Locally", "Official `validate_output.py` and `dev/input/` availability unverified. Self-validator built from contract spec; final validation depends on organizer environment."),
        ("CRF Tagger Conditional", "Rule-based name detection is baseline. CRF (sklearn-crfsuite, <50M params) added only if >5% F1 gain proven on practice data. Current status: not yet justified."),
    ]

    for title, desc in limitations:
        story.append(Paragraph(f"<b>{title}</b>", subsection_style))
        story.append(Paragraph(desc, body_style))

    # ── Footer ────────────────────────────────────────
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=0.5, color=LIGHT_GRAY))
    story.append(Spacer(1, 2))
    story.append(Paragraph(
        "LOCKMATE — Yugaantar DevForge Track 3: Secret Wards | Offline • CPU-only • Deterministic • Contract-compliant | RAKSHA_SECRET-driven HMAC pseudonymization | Independent security gate + canary testing every run",
        small_style
    ))

    # Build
    doc.build(story)
    print(f"PDF generated: {output_path}")


if __name__ == "__main__":
    build_pdf("C:\\Users\\samri\\lockmate\\LOCKMATE_Project_Brief.pdf")