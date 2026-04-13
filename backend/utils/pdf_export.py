"""
PDF export utility — generates a legally-formatted OT Note PDF.
Uses ReportLab for rich PDF generation.
"""
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

PRIMARY = colors.HexColor("#1a3a5c")
ACCENT = colors.HexColor("#0ea5e9")
LIGHT_BG = colors.HexColor("#f0f7ff")
BORDER = colors.HexColor("#cbd5e1")
RED = colors.HexColor("#dc2626")


def _safe(val, fallback="Not specified"):
    if val and str(val).strip() not in ("", "null", "None", "not_mentioned"):
        return str(val).strip()
    return fallback


def generate_ot_note_pdf(note: dict) -> bytes:
    """Return PDF bytes for the given OT note dict."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title", fontSize=16, fontName="Helvetica-Bold",
        textColor=PRIMARY, alignment=TA_CENTER, spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "subtitle", fontSize=9, fontName="Helvetica",
        textColor=colors.grey, alignment=TA_CENTER, spaceAfter=10,
    )
    section_style = ParagraphStyle(
        "section", fontSize=10, fontName="Helvetica-Bold",
        textColor=colors.white, spaceAfter=4, spaceBefore=8,
        leftIndent=4, backColor=PRIMARY,
    )
    field_key_style = ParagraphStyle(
        "field_key", fontSize=8.5, fontName="Helvetica-Bold",
        textColor=PRIMARY,
    )
    field_val_style = ParagraphStyle(
        "field_val", fontSize=8.5, fontName="Helvetica",
        textColor=colors.black,
    )
    warn_style = ParagraphStyle(
        "warn", fontSize=8, fontName="Helvetica-Bold",
        textColor=RED,
    )

    story = []

    # ── Header ──────────────────────────────────────────────────────────────
    story.append(Paragraph("MEDORA", title_style))
    story.append(Paragraph("OT Documentation System — Operative Note", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY))
    story.append(Spacer(1, 4))

    status_text = f"Status: {note.get('status', 'draft').upper()}"
    note_id = f"Note ID: {note.get('id', 'N/A')}"
    generated = f"Generated: {datetime.now().strftime('%d %b %Y  %H:%M')}"
    story.append(Paragraph(f"{status_text}   |   {note_id}   |   {generated}", subtitle_style))
    story.append(Spacer(1, 6))

    def section(title):
        story.append(Paragraph(f"  {title}", section_style))

    def row(key, val, warn=False):
        style = warn_style if warn else field_val_style
        return [Paragraph(key, field_key_style), Paragraph(_safe(val), style)]

    def table(rows, col_widths=None):
        cw = col_widths or [60 * mm, 110 * mm]
        t = Table(rows, colWidths=cw)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), LIGHT_BG),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ]))
        story.append(t)
        story.append(Spacer(1, 4))

    # ── Patient Info ────────────────────────────────────────────────────────
    section("PATIENT INFORMATION")
    table([
        row("Patient Name", note.get("patient_name")),
        row("MRN", note.get("patient_mrn")),
        row("Age / Gender", f"{_safe(note.get('patient_age'))} / {_safe(note.get('patient_gender'))}"),
        row("Ward / Bed", f"{_safe(note.get('ward'))} / {_safe(note.get('bed_number'))}"),
    ])

    # ── Procedure Timing ────────────────────────────────────────────────────
    section("PROCEDURE TIMING")
    table([
        row("Date of Surgery", note.get("date_of_surgery")),
        row("Time Start", note.get("time_start")),
        row("Time End", note.get("time_end")),
        row("Duration", note.get("duration_minutes") and f"{note['duration_minutes']} min"),
    ])

    # ── Care Team ───────────────────────────────────────────────────────────
    section("CARE TEAM")
    table([
        row("Operating Surgeon", note.get("surgeon_name")),
        row("Assistant Surgeon", note.get("assistant_surgeon")),
        row("Anesthetist", note.get("anesthetist")),
        row("Scrub Nurse", note.get("scrub_nurse")),
        row("Circulating Nurse", note.get("circulating_nurse")),
    ])

    # ── Diagnosis ───────────────────────────────────────────────────────────
    section("DIAGNOSIS")
    table([
        row("Pre-operative Diagnosis", note.get("pre_op_diagnosis")),
        row("Post-operative Diagnosis", note.get("post_op_diagnosis")),
        row("Type of Anesthesia", note.get("type_of_anesthesia")),
    ])

    # ── Procedure ───────────────────────────────────────────────────────────
    section("PROCEDURE")
    table([
        row("Procedure Name", note.get("procedure_name")),
        row("Procedure Description", note.get("procedure_description")),
        row("Intra-operative Findings", note.get("intra_op_findings")),
    ], col_widths=[60 * mm, 110 * mm])

    # ── Safety Counts ───────────────────────────────────────────────────────
    section("SAFETY COUNTS & CLINICAL DATA")
    sc = note.get("sponge_count_correct", "not_mentioned")
    ic = note.get("instrument_count_correct", "not_mentioned")
    nc = note.get("needle_count_correct", "not_mentioned")
    table([
        row("Blood Loss (mL)", note.get("blood_loss_ml"), warn=not note.get("blood_loss_ml")),
        row("Fluids Given", note.get("fluids_given")),
        row("Sponge Count", sc, warn=sc != "yes"),
        row("Instrument Count", ic, warn=ic != "yes"),
        row("Needle Count", nc, warn=nc != "yes"),
    ])

    # ── Implants ────────────────────────────────────────────────────────────
    section("IMPLANTS & CONSUMABLES")
    table([
        row("Implants Used", note.get("implants_used")),
        row("Consumables", note.get("consumables")),
        row("Specimen Sent", note.get("specimen_sent")),
    ])

    # ── Outcome ─────────────────────────────────────────────────────────────
    section("COMPLICATIONS & OUTCOME")
    table([
        row("Complications", note.get("complications") or "None"),
        row("Drain Placed", note.get("drain_placed")),
        row("Wound Closure", note.get("wound_closure")),
        row("Disposition", note.get("disposition")),
    ])

    # ── Post-op Instructions ─────────────────────────────────────────────────
    section("POST-OPERATIVE INSTRUCTIONS")
    table([
        row("Instructions", note.get("post_op_instructions")),
    ])

    # ── Missing Fields Warning ────────────────────────────────────────────────
    missing = note.get("missing_fields") or []
    if missing:
        story.append(Spacer(1, 4))
        warn_rows = [[
            Paragraph("⚠ INCOMPLETE — Missing Mandatory Fields:", warn_style),
            Paragraph(", ".join(missing), warn_style),
        ]]
        wt = Table(warn_rows, colWidths=[80 * mm, 90 * mm])
        wt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff5f5")),
            ("BOX", (0, 0), (-1, -1), 1, RED),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(wt)
        story.append(Spacer(1, 4))

    # ── Signature ─────────────────────────────────────────────────────────────
    section("DIGITAL SIGNATURE & CERTIFICATION")
    signed_by = note.get("signed_by") or "UNSIGNED"
    signed_at = note.get("signed_at") or "—"
    sig_rows = [
        row("Signed By", signed_by),
        row("Signed At", str(signed_at)),
        row("Note Version", note.get("version", "1")),
        row("Certification",
            "I certify that this operative note accurately represents the procedure performed "
            "and the findings observed during surgery." if note.get("status") == "signed" else "NOT YET CERTIFIED"),
    ]
    table(sig_rows)

    # ── Footer ─────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
    story.append(Paragraph(
        "CONFIDENTIAL MEDICAL RECORD — MEDORA OT Documentation System",
        ParagraphStyle("footer", fontSize=7, textColor=colors.grey, alignment=TA_CENTER),
    ))

    doc.build(story)
    return buffer.getvalue()
