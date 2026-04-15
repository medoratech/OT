"""
Consultation routes — CRUD, audio transcription, AI structuring, and PDF export.
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from database import get_db
from models.user import User
from models.consultation import Consultation
from utils.auth import get_current_user
from services.deepgram_service import transcribe_audio
from services.consultation_service import structure_consultation
from utils.opd_pdf_export import generate_opd_summary_pdf

router = APIRouter(prefix="/api/consultations", tags=["Consultations"])



# ── Pydantic schemas ────────────────────────────────────────────────────────


class ConsultationCreate(BaseModel):
    patient_name: Optional[str] = None
    patient_mrn: Optional[str] = None
    patient_age: Optional[str] = None
    patient_gender: Optional[str] = None
    chief_complaint: Optional[str] = None
    consultation_date: Optional[str] = None
    consultation_time: Optional[str] = None
    department: Optional[str] = None


class ConsultationUpdate(BaseModel):
    patient_name: Optional[str] = None
    patient_mrn: Optional[str] = None
    patient_age: Optional[str] = None
    patient_gender: Optional[str] = None
    chief_complaint: Optional[str] = None
    consultation_date: Optional[str] = None
    consultation_time: Optional[str] = None
    department: Optional[str] = None
    diagnosis: Optional[str] = None
    differential_diagnosis: Optional[str] = None
    history_of_present_illness: Optional[str] = None
    examination_findings: Optional[str] = None
    prescription: Optional[list] = None
    lab_tests: Optional[list] = None
    imaging_ordered: Optional[list] = None
    follow_up_date: Optional[str] = None
    follow_up_instructions: Optional[str] = None
    referral: Optional[str] = None
    lifestyle_advice: Optional[str] = None
    raw_transcription: Optional[str] = None
    status: Optional[str] = None


# ── Helpers ─────────────────────────────────────────────────────────────────


def _consult_to_dict(c: Consultation) -> dict:
    return {
        "id": c.id,
        "status": c.status,
        "patient_name": c.patient_name,
        "patient_mrn": c.patient_mrn,
        "patient_age": c.patient_age,
        "patient_gender": c.patient_gender,
        "chief_complaint": c.chief_complaint,
        "doctor_id": c.doctor_id,
        "doctor_name": c.doctor_name,
        "consultation_date": c.consultation_date,
        "consultation_time": c.consultation_time,
        "department": c.department,
        "raw_transcription": c.raw_transcription,
        "diagnosis": c.diagnosis,
        "differential_diagnosis": c.differential_diagnosis,
        "history_of_present_illness": c.history_of_present_illness,
        "examination_findings": c.examination_findings,
        "prescription": c.prescription or [],
        "lab_tests": c.lab_tests or [],
        "imaging_ordered": c.imaging_ordered or [],
        "follow_up_date": c.follow_up_date,
        "follow_up_instructions": c.follow_up_instructions,
        "referral": c.referral,
        "lifestyle_advice": c.lifestyle_advice,
        "missing_fields": c.missing_fields or [],
        "audit_trail": c.audit_trail or [],
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


# ── CRUD Routes ─────────────────────────────────────────────────────────────


@router.post("/", status_code=201)
async def create_consultation(
    body: ConsultationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new consultation record."""
    consult = Consultation(
        doctor_id=current_user.id,
        doctor_name=current_user.full_name,
        status="draft",
        audit_trail=[{
            "action": "created",
            "user": current_user.full_name,
            "timestamp": datetime.utcnow().isoformat(),
            "note": "Consultation created",
        }],
        **body.model_dump(exclude_none=True),
    )
    db.add(consult)
    await db.commit()
    await db.refresh(consult)
    return _consult_to_dict(consult)


@router.get("/")
async def list_consultations(
    status: str = None,
    search: str = "",
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List consultations for the current user."""
    q = select(Consultation).order_by(desc(Consultation.created_at)).limit(limit).offset(offset)
    if current_user.role not in ("admin", "staff"):
        q = q.where(Consultation.doctor_id == current_user.id)
    if status:
        q = q.where(Consultation.status == status)
    if search:
        from sqlalchemy import or_
        q = q.where(
            or_(
                Consultation.patient_name.ilike(f"%{search}%"),
                Consultation.patient_mrn.ilike(f"%{search}%"),
                Consultation.diagnosis.ilike(f"%{search}%"),
            )
        )
    result = await db.execute(q)
    return [_consult_to_dict(c) for c in result.scalars().all()]


@router.get("/stats")
async def get_consultation_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get consultation statistics."""
    q = select(Consultation)
    if current_user.role not in ("admin", "staff"):
        q = q.where(Consultation.doctor_id == current_user.id)
    all_c = (await db.execute(q)).scalars().all()
    total = len(all_c)
    finalized = sum(1 for c in all_c if c.status == "finalized")
    drafts = sum(1 for c in all_c if c.status in ("draft", "recording", "processing", "review"))
    incomplete = sum(1 for c in all_c if c.missing_fields)
    return {
        "total": total,
        "finalized": finalized,
        "drafts": drafts,
        "incomplete": incomplete,
    }


@router.get("/{consult_id}")
async def get_consultation(
    consult_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Consultation).where(Consultation.id == consult_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Consultation not found")
    return _consult_to_dict(c)


@router.patch("/{consult_id}")
async def update_consultation(
    consult_id: str,
    body: ConsultationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Consultation).where(Consultation.id == consult_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Consultation not found")
    if c.status == "finalized":
        raise HTTPException(400, "Cannot edit a finalized consultation")

    updates = body.model_dump(exclude_none=True)
    for k, v in updates.items():
        setattr(c, k, v)

    trail = c.audit_trail or []
    trail.append({
        "action": "updated",
        "user": current_user.full_name,
        "timestamp": datetime.utcnow().isoformat(),
        "note": f"Fields updated: {list(updates.keys())}",
    })
    c.audit_trail = trail
    await db.commit()
    await db.refresh(c)
    return _consult_to_dict(c)


@router.delete("/{consult_id}")
async def delete_consultation(
    consult_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Consultation).where(Consultation.id == consult_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Consultation not found")
    if c.status == "finalized":
        raise HTTPException(400, "Cannot delete a finalized consultation")
    await db.delete(c)
    await db.commit()
    return {"success": True}


# ── Speech Routes ────────────────────────────────────────────────────────────


@router.post("/{consult_id}/transcribe")
async def transcribe_consultation(
    consult_id: str,
    audio: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload audio of consultation → Deepgram transcription, appended to record."""
    result = await db.execute(select(Consultation).where(Consultation.id == consult_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Consultation not found")

    audio_bytes = await audio.read()
    mime = audio.content_type or "audio/webm"
    trans_result = await transcribe_audio(audio_bytes, mime_type=mime)
    transcript = trans_result["transcript"]

    # Append to existing transcription
    c.raw_transcription = ((c.raw_transcription or "") + "\n" + transcript).strip()
    c.status = "processing"

    trail = c.audit_trail or []
    trail.append({
        "action": "transcribed",
        "user": current_user.full_name,
        "timestamp": datetime.utcnow().isoformat(),
        "note": f"Audio transcribed. {len(transcript)} chars added.",
    })
    c.audit_trail = trail
    await db.commit()

    return {
        "transcript": transcript,
        "confidence": trans_result["confidence"],
        "duration": trans_result["duration"],
        "consult_id": consult_id,
    }


@router.post("/{consult_id}/structure")
async def structure_consult(
    consult_id: str,
    transcription: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send conversation transcript to Gemini → structured clinical fields."""
    result = await db.execute(select(Consultation).where(Consultation.id == consult_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Consultation not found")

    text = transcription or c.raw_transcription or ""
    if not text.strip():
        raise HTTPException(400, "No transcription available to structure")

    ai_result = await structure_consultation(text)
    structured = ai_result["structured"]
    missing = ai_result["missing_fields"]

    # Map extracted fields onto model
    field_map = {
        "diagnosis": "diagnosis",
        "differential_diagnosis": "differential_diagnosis",
        "history_of_present_illness": "history_of_present_illness",
        "examination_findings": "examination_findings",
        "prescription": "prescription",
        "lab_tests": "lab_tests",
        "imaging_ordered": "imaging_ordered",
        "follow_up_date": "follow_up_date",
        "follow_up_instructions": "follow_up_instructions",
        "referral": "referral",
        "lifestyle_advice": "lifestyle_advice",
    }
    for ai_key, model_attr in field_map.items():
        val = structured.get(ai_key)
        if val is not None:
            setattr(c, model_attr, val)

    c.missing_fields = missing
    c.status = "review"

    trail = c.audit_trail or []
    trail.append({
        "action": "ai_structured",
        "user": current_user.full_name,
        "timestamp": datetime.utcnow().isoformat(),
        "note": f"AI extracted consultation fields. Missing: {missing}",
    })
    c.audit_trail = trail
    await db.commit()
    await db.refresh(c)

    return {
        "structured": structured,
        "missing_fields": missing,
        "consult_id": consult_id,
        "consultation": _consult_to_dict(c),
    }


@router.post("/{consult_id}/finalize")
async def finalize_consultation(
    consult_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark consultation as finalized (doctor has reviewed and approved)."""
    result = await db.execute(select(Consultation).where(Consultation.id == consult_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Consultation not found")
    if c.status == "finalized":
        raise HTTPException(400, "Already finalized")

    c.status = "finalized"
    trail = c.audit_trail or []
    trail.append({
        "action": "finalized",
        "user": current_user.full_name,
        "timestamp": datetime.utcnow().isoformat(),
        "note": "Consultation finalized by doctor",
    })
    c.audit_trail = trail
    await db.commit()
    await db.refresh(c)
    return {"success": True, "consultation": _consult_to_dict(c)}


# ── PDF Export Route ─────────────────────────────────────────────────────────


@router.get("/{consult_id}/export/pdf")
async def export_consult_pdf(
    consult_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate and stream the OPD Clinical Summary Report as PDF."""
    result = await db.execute(select(Consultation).where(Consultation.id == consult_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Consultation not found")

    data = _consult_to_dict(c)
    pdf_bytes = generate_opd_summary_pdf(data)
    mrn = c.patient_mrn or consult_id
    filename = f"OPD_Summary_{mrn}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

