"""
Gemini LLM service.
Converts raw surgical dictation → structured OT note JSON.
"""
from typing import List
import json
import re
import google.generativeai as genai
from config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

_MODEL = "gemini-2.0-flash"

STRUCTURE_PROMPT = """You are a senior medical documentation assistant helping surgeons create structured, legally defensible operative notes.

Given a raw surgical dictation transcript, extract and structure the information into the following JSON fields.
Return ONLY valid JSON, no markdown, no explanation.

Fields to extract:
21: {{
22:   "pre_op_diagnosis": "string or null",
23:   "post_op_diagnosis": "string or null",
24:   "procedure_name": "string or null",
25:   "procedure_description": "string or null",
26:   "type_of_anesthesia": "string or null",
27:   "intra_op_findings": "string or null",
28:   "blood_loss_ml": "string or null (e.g. '150', 'minimal', 'not mentioned')",
29:   "fluids_given": "string or null",
30:   "sponge_count_correct": "yes | no | not_mentioned",
31:   "instrument_count_correct": "yes | no | not_mentioned",
32:   "needle_count_correct": "yes | no | not_mentioned",
33:   "implants_used": "string or null",
34:   "consumables": "string or null",
35:   "complications": "string or null (write 'None' if no complications mentioned)",
36:   "drain_placed": "yes | no | not_mentioned",
37:   "wound_closure": "string or null",
38:   "specimen_sent": "string or null",
39:   "post_op_instructions": "string or null",
40:   "disposition": "ICU | ward | recovery | home | null",
41:   "surgeon_name": "string or null",
42:   "assistant_surgeon": "string or null",
43:   "anesthetist": "string or null",
44:   "scrub_nurse": "string or null",
45:   "date_of_surgery": "string or null",
46:   "time_start": "string or null",
47:   "time_end": "string or null",
48:   "patient_name": "string or null",
49:   "patient_age": "string or null",
50:   "patient_gender": "string or null",
51:   "patient_mrn": "string or null",
52:   "ward": "string or null",
53:   "bed_number": "string or null"
54: }}

Important rules:
- Do not invent clinical details not present in the dictation
- If a field is not mentioned, set it to null
- For counts (sponge/instrument/needle), only mark "yes" if explicitly confirmed
- Blood loss must be a rough number or description if mentioned
- procedure_description should be comprehensive step-by-step narrative

Raw Dictation:
\"\"\"
{transcription}
\"\"\"
"""

MANDATORY_FIELDS = [
    "pre_op_diagnosis",
    "post_op_diagnosis",
    "procedure_name",
    "procedure_description",
    "type_of_anesthesia",
    "blood_loss_ml",
    "sponge_count_correct",
    "instrument_count_correct",
    "complications",
    "post_op_instructions",
    "surgeon_name",
]

FIELD_LABELS = {
    "pre_op_diagnosis": "Pre-operative Diagnosis",
    "post_op_diagnosis": "Post-operative Diagnosis",
    "procedure_name": "Procedure Name",
    "procedure_description": "Procedure Description",
    "type_of_anesthesia": "Type of Anesthesia",
    "blood_loss_ml": "Blood Loss",
    "sponge_count_correct": "Sponge Count",
    "instrument_count_correct": "Instrument Count",
    "needle_count_correct": "Needle Count",
    "complications": "Complications",
    "post_op_instructions": "Post-operative Instructions",
    "surgeon_name": "Surgeon Name",
    "intra_op_findings": "Intra-operative Findings",
    "disposition": "Patient Disposition",
}


async def structure_dictation(transcription: str) -> dict:
    """Send transcription to Gemini and return structured note fields."""
    prompt = STRUCTURE_PROMPT.format(transcription=transcription)

    model = genai.GenerativeModel(_MODEL)
    response = model.generate_content(prompt)
    raw = response.text.strip()

    # Strip markdown code fences if present
    raw = re.sub(r"^```(?:json)?", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"```$", "", raw, flags=re.MULTILINE)
    raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Attempt repair: find first { ... }
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            data = json.loads(m.group())
        else:
            data = {}

    missing = _validate_mandatory(data)
    return {"structured": data, "missing_fields": missing}


def _validate_mandatory(data: dict) -> List[str]:
    """Return list of human-readable missing mandatory field labels."""
    missing = []
    for field in MANDATORY_FIELDS:
        val = data.get(field)
        if val is None or str(val).strip().lower() in ("", "null", "not_mentioned"):
            missing.append(FIELD_LABELS.get(field, field))
    return missing


async def enhance_note_section(section_text: str, section_name: str) -> str:
    """Ask Gemini to polish/expand a single section of the OT note."""
    model = genai.GenerativeModel(_MODEL)
    prompt = (
        f"You are a medical documentation expert. "
        f"Improve the following '{section_name}' section of an operative note "
        f"to be clear, professional, and medically accurate. "
        f"Keep all clinical facts exactly as given. "
        f"Return only the improved text, no explanation.\n\n"
        f"Original:\n{section_text}"
    )
    response = model.generate_content(prompt)
    return response.text.strip()
