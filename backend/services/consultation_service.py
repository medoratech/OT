"""
Gemini service for Doctor-Patient Consultation structuring.
Extracts diagnosis, prescription, lab tests, and follow-up from raw conversation.
"""
import json
import re
from typing import List
import google.generativeai as genai
from config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

_MODEL = "gemini-2.0-flash"

CONSULTATION_PROMPT = """You are an expert clinical documentation AI trained to assist doctors.
Your job is to read a doctor-patient consultation transcript and produce a COMPLETE, FILLED structured clinical note.

CRITICAL INSTRUCTIONS:
1. Return ONLY valid JSON — no markdown fences, no explanation, no preamble
2. You MUST produce a diagnosis even if the doctor did not say it explicitly — infer from symptoms and context
3. You MUST produce a prescription even if drugs were only casually mentioned (e.g. "take Paracetamol", "continue Metformin")
4. You MUST produce follow_up_instructions even if only implied (e.g. "come back if not better", "review in 3 days")
5. For any field where information is genuinely absent, use null for strings and [] for arrays — never skip a field
6. Write in clean clinical language, not verbatim quotes
7. Standard OTC drugs like Paracetamol, Cetirizine, ORS, Vitamin C etc. should be inferred at standard doses if mentioned without explicit dose

Output this exact JSON structure:
{{
  "diagnosis": "Primary clinical diagnosis as a clean medical term. REQUIRED — infer from symptoms if not stated.",
  "differential_diagnosis": "Other possible diagnoses to rule out, or null",
  "history_of_present_illness": "Concise structured paragraph: onset, character, duration, associated symptoms, aggravating/relieving factors",
  "examination_findings": "Physical examination findings if mentioned, else null",
  "prescription": [
    {{
      "drug": "Drug name",
      "dose": "e.g. 500mg — use standard dose if not mentioned",
      "route": "Oral / IV / IM / Topical",
      "frequency": "e.g. Once daily, Twice daily, TID, QID, SOS",
      "duration": "e.g. 3 days, 5 days, 1 week, continue",
      "notes": "e.g. Take after food, At bedtime, With plenty of water, or null"
    }}
  ],
  "lab_tests": [
    {{
      "test_name": "Full test name e.g. CBC, LFT, Dengue NS1 Antigen, Urine routine",
      "urgency": "routine",
      "reason": "Brief clinical reason for ordering"
    }}
  ],
  "imaging_ordered": [
    {{
      "modality": "X-Ray / USG / CT / MRI / Echo",
      "region": "Chest / Abdomen / Right knee / etc.",
      "reason": "Brief reason"
    }}
  ],
  "follow_up_date": "e.g. After 3 days, 1 week, After reports are ready. REQUIRED — use '3 days' if not specified",
  "follow_up_instructions": "Instructions: what to watch for, when to return urgently, red flags. REQUIRED.",
  "referral": "Specialist referral if mentioned, else null",
  "lifestyle_advice": "Diet, rest, hydration, activity restrictions, or null"
}}

Transcript:
\"\"\"
{transcription}
\"\"\"
"""

MANDATORY_CONSULTATION_FIELDS = [
    "diagnosis",
    "prescription",
    "follow_up_instructions",
]

FIELD_LABELS = {
    "diagnosis": "Diagnosis",
    "prescription": "Prescription",
    "follow_up_instructions": "Follow-up Instructions",
    "lab_tests": "Lab Tests",
    "history_of_present_illness": "History of Present Illness",
}


async def structure_consultation(transcription: str) -> dict:
    """Send doctor-patient conversation to Gemini and return structured consultation."""
    prompt = CONSULTATION_PROMPT.format(transcription=transcription)

    model = genai.GenerativeModel(_MODEL)
    response = model.generate_content(prompt)
    raw = response.text.strip()

    # Strip markdown fences if model adds them despite instructions
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)
    raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON object from messy response
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group())
            except json.JSONDecodeError:
                data = {}
        else:
            data = {}

    # Ensure arrays are always lists, never strings
    for list_field in ("prescription", "lab_tests", "imaging_ordered"):
        if not isinstance(data.get(list_field), list):
            data[list_field] = []

    missing = _validate_mandatory(data)
    return {"structured": data, "missing_fields": missing}


def _validate_mandatory(data: dict) -> List[str]:
    missing = []
    for field in MANDATORY_CONSULTATION_FIELDS:
        val = data.get(field)
        if val is None or (isinstance(val, (list, str)) and not val):
            missing.append(FIELD_LABELS.get(field, field))
    return missing
