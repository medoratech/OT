"""
OPD Clinical Summary Report PDF generator.
Produces a professionally formatted 3-page OPD summary matching the
'AI-Assisted Documentation | Voice-Based OPD Engine' format.
"""
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

# ── Colour palette ────────────────────────────────────────────────────────────
NAVY   = colors.HexColor("#1a3a5c")
ACCENT = colors.HexColor("#0ea5e9")
LIGHT  = colors.HexColor("#f0f7ff")
BORDER = colors.HexColor("#cbd5e1")
GREEN  = colors.HexColor("#059669")
AMBER  = colors.HexColor("#d97706")
RED    = colors.HexColor("#dc2626")
WHITE  = colors.white
BLACK  = colors.black
GREY   = colors.HexColor("#6b7280")


def _safe(val, fallback="Not specified"):
    if val and str(val).strip() not in ("", "null", "None", "not_mentioned", "[]"):
        return str(val).strip()
    return fallback


def _date(val):
    if not val:
        return datetime.now().strftime("%d %B %Y")
    try:
        dt = datetime.fromisoformat(str(val).replace("Z", "+00:00"))
        return dt.strftime("%d %B %Y")
    except Exception:
        return str(val)


def _time(val):
    if not val:
        return datetime.now().strftime("%I:%M %p")
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00")).strftime("%I:%M %p")
    except Exception:
        return str(val)


# ── Style factory ─────────────────────────────────────────────────────────────

def _styles():
    s = {}

    s["title"] = ParagraphStyle(
        "title", fontSize=15, fontName="Helvetica-Bold",
        textColor=NAVY, alignment=TA_CENTER, spaceAfter=2,
    )
    s["subtitle"] = ParagraphStyle(
        "subtitle", fontSize=8.5, fontName="Helvetica",
        textColor=GREY, alignment=TA_CENTER, spaceAfter=6,
    )
    s["section_hdr"] = ParagraphStyle(
        "section_hdr", fontSize=9.5, fontName="Helvetica-Bold",
        textColor=WHITE, leftIndent=6, spaceBefore=10, spaceAfter=4,
        backColor=NAVY,
    )
    s["field_key"] = ParagraphStyle(
        "field_key", fontSize=8.5, fontName="Helvetica-Bold", textColor=NAVY,
    )
    s["field_val"] = ParagraphStyle(
        "field_val", fontSize=8.5, fontName="Helvetica", textColor=BLACK,
    )
    s["field_val_sm"] = ParagraphStyle(
        "field_val_sm", fontSize=8, fontName="Helvetica",
        textColor=BLACK, leading=11,
    )
    s["body"] = ParagraphStyle(
        "body", fontSize=8.5, fontName="Helvetica",
        textColor=BLACK, leading=13, alignment=TA_JUSTIFY,
    )
    s["bold"] = ParagraphStyle(
        "bold", fontSize=8.5, fontName="Helvetica-Bold", textColor=NAVY,
    )
    s["warn"] = ParagraphStyle(
        "warn", fontSize=8, fontName="Helvetica-Bold", textColor=RED,
    )
    s["mono"] = ParagraphStyle(
        "mono", fontSize=8, fontName="Courier", textColor=BLACK, leading=12,
    )
    s["footer"] = ParagraphStyle(
        "footer", fontSize=7, fontName="Helvetica",
        textColor=GREY, alignment=TA_CENTER,
    )
    s["soap_hdr"] = ParagraphStyle(
        "soap_hdr", fontSize=9, fontName="Helvetica-Bold",
        textColor=NAVY, spaceAfter=2, spaceBefore=6,
    )
    return s


# ── Layout helpers ────────────────────────────────────────────────────────────

W = A4[0] - 30 * mm   # usable width


def _sec(title, st):
    return Paragraph(f"  ◆ {title}", st["section_hdr"])


def _kv_table(rows_data, st, key_w=55 * mm):
    """Two-column key-value table."""
    rows = [
        [Paragraph(k, st["field_key"]), Paragraph(_safe(v), st["field_val"])]
        for k, v in rows_data
    ]
    t = Table(rows, colWidths=[key_w, W - key_w])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",(0, 0), (-1, -1), 6),
        ("RIGHTPADDING",(0, 0),(-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0,0),(-1, -1), 4),
        ("GRID",       (0, 0), (-1, -1), 0.4, BORDER),
    ]))
    return t


def _hr():
    return HRFlowable(width="100%", thickness=0.5, color=BORDER)


# ── Main generator ────────────────────────────────────────────────────────────

def generate_opd_summary_pdf(c: dict) -> bytes:
    """Return PDF bytes for full OPD Clinical Summary Report."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
        title=f"OPD Summary - {c.get('patient_name', 'Patient')}",
    )
    st  = _styles()
    story = []

    consult_no = str(c.get("id", ""))[:6].upper() or "000001"
    gen_at = datetime.now().strftime("%d %B %Y, %I:%M %p")

    # ══ PAGE 1 ════════════════════════════════════════════════════════════════

    # Header block
    story += [
        Paragraph("■ OPD CLINICAL SUMMARY REPORT", st["title"]),
        Paragraph("AI-Assisted Documentation  |  Voice-Based OPD Engine", st["subtitle"]),
        HRFlowable(width="100%", thickness=2, color=NAVY),
        Spacer(1, 3),
    ]

    # Status bar
    status_row = Table(
        [[
            Paragraph(f"Consultation ID: #{consult_no}", st["bold"]),
            Paragraph(
                f"Status: {c.get('status', 'draft').replace('_', ' ').title()} — Pending Doctor Approval"
                if c.get("status") != "finalized"
                else f"Status: Finalized ✓",
                ParagraphStyle("sr", fontSize=8.5, fontName="Helvetica-Bold",
                               textColor=GREEN if c.get("status") == "finalized" else AMBER,
                               alignment=TA_RIGHT),
            ),
        ]],
        colWidths=[W / 2, W / 2],
    )
    status_row.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
    ]))
    story += [status_row, Spacer(1, 6)]

    # ── Patient & Consultation Information ───────────────────────────────────
    story.append(_sec("PATIENT & CONSULTATION INFORMATION", st))

    pat_consult = Table(
        [
            [
                _kv_table([
                    ("Patient Name",       c.get("patient_name")),
                    ("Age",               c.get("patient_age")),
                    ("Gender",            c.get("patient_gender")),
                ], st, key_w=38 * mm),
                _kv_table([
                    ("Consulting Doctor", c.get("doctor_name")),
                    ("Date",             _date(c.get("consultation_date") or c.get("created_at"))),
                    ("Time",             _time(c.get("consultation_time") or c.get("created_at"))),
                ], st, key_w=38 * mm),
            ]
        ],
        colWidths=[W / 2 - 3, W / 2 - 3],
    )
    pat_consult.setStyle(TableStyle([
        ("VALIGN",      (0,0),(-1,-1), "TOP"),
        ("LEFTPADDING", (0,0),(-1,-1), 0),
        ("RIGHTPADDING",(0,0),(-1,-1), 4),
    ]))
    story += [pat_consult, Spacer(1, 4)]

    if c.get("department") or c.get("patient_mrn"):
        story.append(_kv_table([
            ("Department", c.get("department")),
            ("MRN",        c.get("patient_mrn")),
        ], st))
        story.append(Spacer(1, 4))

    # ── Chief Complaint & History ─────────────────────────────────────────────
    story.append(_sec("CHIEF COMPLAINT & HISTORY", st))
    story.append(_kv_table([
        ("Chief Complaint",       c.get("chief_complaint")),
        ("History of Present\nIllness", c.get("history_of_present_illness")),
        ("Examination Findings",  c.get("examination_findings")),
    ], st, key_w=50 * mm))
    story.append(Spacer(1, 4))

    # ── Diagnosis ─────────────────────────────────────────────────────────────
    story.append(_sec("DIAGNOSIS", st))

    diag_rows = []
    if c.get("diagnosis"):
        diag_rows.append([
            Paragraph("PRIMARY DIAGNOSIS", st["field_key"]),
            Paragraph("ICD-10 CODE", st["field_key"]),
        ])
        diag_rows.append([
            Paragraph(_safe(c.get("diagnosis")), st["field_val"]),
            Paragraph("—", st["field_val"]),
        ])
    if c.get("differential_diagnosis"):
        diag_rows.append([
            Paragraph("SECONDARY / DIFFERENTIAL DIAGNOSIS", st["field_key"]),
            Paragraph("ICD-10", st["field_key"]),
        ])
        diag_rows.append([
            Paragraph(_safe(c.get("differential_diagnosis")), st["field_val"]),
            Paragraph("—", st["field_val"]),
        ])

    if diag_rows:
        dt = Table(diag_rows, colWidths=[W * 0.65, W * 0.35])
        dt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
            ("BACKGROUND", (0, 2), (-1, 2), LIGHT),
            ("GRID",       (0, 0), (-1, -1), 0.4, BORDER),
            ("VALIGN",     (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",(0, 0), (-1, -1), 6),
            ("RIGHTPADDING",(0,0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0,0),(-1, -1), 4),
        ]))
        story += [dt, Spacer(1, 4)]

    # ── Investigations ────────────────────────────────────────────────────────
    labs = c.get("lab_tests") or []
    imaging = c.get("imaging_ordered") or []
    if labs or imaging:
        story.append(_sec("INVESTIGATIONS ORDERED", st))
        inv_rows = [[
            Paragraph("Test / Investigation", st["field_key"]),
            Paragraph("Clinical Indication", st["field_key"]),
            Paragraph("Urgency", st["field_key"]),
        ]]
        for lab in labs:
            inv_rows.append([
                Paragraph(_safe(lab.get("test_name") if isinstance(lab, dict) else str(lab)), st["field_val"]),
                Paragraph(_safe(lab.get("reason", "—") if isinstance(lab, dict) else "—"), st["field_val"]),
                Paragraph(_safe(lab.get("urgency", "Routine") if isinstance(lab, dict) else "Routine"), st["field_val"]),
            ])
        for img in imaging:
            inv_rows.append([
                Paragraph(
                    f"{_safe(img.get('modality', ''))} — {_safe(img.get('region', ''))}"
                    if isinstance(img, dict) else str(img), st["field_val"]),
                Paragraph(_safe(img.get("reason", "—") if isinstance(img, dict) else "—"), st["field_val"]),
                Paragraph("Routine", st["field_val"]),
            ])
        it = Table(inv_rows, colWidths=[W * 0.4, W * 0.4, W * 0.2])
        it.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR",  (0, 0), (-1, 0), WHITE),
            ("GRID",       (0, 0), (-1, -1), 0.4, BORDER),
            ("VALIGN",     (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",(0, 0), (-1, -1), 6),
            ("RIGHTPADDING",(0,0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0,0),(-1, -1), 4),
            ("ROWBACKGROUNDS", (0,1),(-1,-1), [WHITE, LIGHT]),
        ]))
        story += [it, Spacer(1, 4)]

    # ── Page footer 1
    story += [
        _hr(),
        Paragraph(
            f"Page 1  |  OPD Clinical Summary  |  Consultation #{consult_no}",
            st["footer"],
        ),
        PageBreak(),
    ]

    # ══ PAGE 2 ════════════════════════════════════════════════════════════════

    # ── Prescription ──────────────────────────────────────────────────────────
    rx = c.get("prescription") or []
    if rx:
        story.append(_sec("PRESCRIPTION  ■", st))

        meta_row = Table(
            [[
                Paragraph(f"Patient: {_safe(c.get('patient_name'))}", st["bold"]),
                Paragraph(f"Doctor: {_safe(c.get('doctor_name'))}", st["bold"]),
                Paragraph(f"Date: {_date(c.get('consultation_date') or c.get('created_at'))}", st["bold"]),
            ]],
            colWidths=[W / 3, W / 3, W / 3],
        )
        meta_row.setStyle(TableStyle([
            ("BACKGROUND", (0,0),(-1,-1), LIGHT),
            ("GRID",       (0,0),(-1,-1), 0.4, BORDER),
            ("LEFTPADDING",(0,0),(-1,-1), 6),
            ("TOPPADDING", (0,0),(-1,-1), 4),
            ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ]))
        story += [meta_row, Spacer(1, 4)]

        for i, drug in enumerate(rx, 1):
            if isinstance(drug, dict):
                name = _safe(drug.get("drug"))
                dose = _safe(drug.get("dose"), "")
                freq = _safe(drug.get("frequency"), "")
                route = _safe(drug.get("route"), "")
                dur  = _safe(drug.get("duration"), "")
                note = drug.get("notes", "")
                parts = [p for p in [dose, freq, dur, route] if p and p != "Not specified"]
                rx_line = f"{i}. <b>{name}</b> {' | '.join(parts)}"
                if note:
                    rx_line += f"  <i>{note}</i>"
            else:
                rx_line = f"{i}. {drug}"
            story.append(Paragraph(rx_line, ParagraphStyle(
                f"rx{i}", fontSize=8.5, fontName="Helvetica",
                leftIndent=10, spaceAfter=4,
            )))
        story.append(Spacer(1, 4))

    # ── Advice & Follow-up ────────────────────────────────────────────────────
    story.append(_sec("ADVICE & FOLLOW-UP", st))
    story.append(_kv_table([
        ("Advice Given",      c.get("lifestyle_advice")),
        ("Follow-up",         c.get("follow_up_date")),
        ("Follow-up\nInstructions", c.get("follow_up_instructions")),
        ("Referral",          c.get("referral")),
    ], st, key_w=50 * mm))
    story.append(Spacer(1, 6))

    # ── SOAP Note ─────────────────────────────────────────────────────────────
    story.append(_sec("SOAP NOTE (AI-Generated)", st))

    def soap_section(label, text):
        story.append(Paragraph(label, st["soap_hdr"]))
        story.append(Paragraph(_safe(text, "Not documented."), st["body"]))
        story.append(Spacer(1, 4))

    # Build SOAP from consultation fields
    hpi = _safe(c.get("history_of_present_illness"), "")
    exam = _safe(c.get("examination_findings"), "")
    rx_summary = ", ".join(
        drug.get("drug", "") if isinstance(drug, dict) else str(drug)
        for drug in (c.get("prescription") or [])
    )
    lab_summary = ", ".join(
        lab.get("test_name", "") if isinstance(lab, dict) else str(lab)
        for lab in (c.get("lab_tests") or [])
    )

    soap_subjective = hpi or "Patient history as documented above."
    soap_objective = (
        f"{exam}. "
        f"{'Investigations ordered: ' + lab_summary + '.' if lab_summary else ''}"
    ).strip() or "Physical examination and investigations as documented."
    soap_assessment = (
        f"Primary Diagnosis: {_safe(c.get('diagnosis'))}. "
        f"{'Differential: ' + _safe(c.get('differential_diagnosis')) + '.' if c.get('differential_diagnosis') else ''}"
    )
    soup_plan_lines = []
    if rx_summary:
        soup_plan_lines.append(f"1. Medications: {rx_summary}")
    if lab_summary:
        soup_plan_lines.append(f"2. Investigations: {lab_summary}")
    if c.get("lifestyle_advice"):
        soup_plan_lines.append(f"3. Patient Education: {_safe(c.get('lifestyle_advice'))}")
    if c.get("follow_up_instructions"):
        soup_plan_lines.append(f"4. Follow-up: {_safe(c.get('follow_up_instructions'))}")
    soap_plan = "\n".join(soup_plan_lines) if soup_plan_lines else "Plan as documented above."

    soap_section("SUBJECTIVE:", soap_subjective)
    soap_section("OBJECTIVE:", soap_objective)
    soap_section("ASSESSMENT:", soap_assessment)
    soap_section("PLAN:", soap_plan)

    # Page footer 2
    story += [
        _hr(),
        Paragraph(
            f"Page 2  |  OPD Clinical Summary  |  Consultation #{consult_no}",
            st["footer"],
        ),
        PageBreak(),
    ]

    # ══ PAGE 3 ════════════════════════════════════════════════════════════════

    # ── Transcript ────────────────────────────────────────────────────────────
    story.append(_sec("CONSULTATION TRANSCRIPT (Speaker-Labeled)", st))
    transcript = c.get("raw_transcription") or "No transcript recorded."
    story.append(Paragraph(transcript, st["mono"]))
    story.append(Spacer(1, 12))

    _spacer_line = "_" * 60
    story += [
        _hr(),
        Spacer(1, 10),
        Paragraph(f"{_spacer_line}", st["body"]),
        Paragraph("Doctor's Signature:", st["bold"]),
        Spacer(1, 6),
        Paragraph(
            f"___________________________          Date: {_date(c.get('consultation_date') or c.get('created_at'))}",
            st["body"],
        ),
        Spacer(1, 14),
    ]

    # Disclaimer
    story.append(Paragraph(
        "This document was generated by the Voice-Based OPD Documentation Engine using AI assistance. "
        "All clinical decisions must be verified and approved by the treating physician. "
        "This report is confidential and intended for authorized medical personnel only.",
        ParagraphStyle("disclaimer", fontSize=7.5, fontName="Helvetica-Oblique",
                       textColor=GREY, alignment=TA_CENTER, leading=11),
    ))
    story.append(Spacer(1, 6))
    story += [
        _hr(),
        Paragraph(
            f"Generated: {gen_at}  |  Consultation ID: #{consult_no}  |  Powered by Gemini + Deepgram",
            st["footer"],
        ),
        Paragraph(
            f"Page 3  |  OPD Clinical Summary  |  Consultation #{consult_no}",
            st["footer"],
        ),
    ]

    doc.build(story)
    return buf.getvalue()
