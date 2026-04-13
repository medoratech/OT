"""
OT Notes CRUD + sign + export routes.
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc
from pydantic import BaseModel

from database import get_db
from models.user import User
from models.ot_note import OTNote
from utils.auth import get_current_user
from utils.pdf_export import generate_ot_note_pdf

router = APIRouter(prefix="/api/notes", tags=["OT Notes"])


class NoteCreate(BaseModel):
    patient_name: Optional[str] = None
    patient_mrn: Optional[str] = None
    patient_age: Optional[str] = None
    patient_gender: Optional[str] = None
    ward: Optional[str] = None
    bed_number: Optional[str] = None
    date_of_surgery: Optional[str] = None
    time_start: Optional[str] = None
    time_end: Optional[str] = None


class NoteUpdate(BaseModel):
    patient_name: Optional[str] = None
    patient_mrn: Optional[str] = None
    patient_age: Optional[str] = None
    patient_gender: Optional[str] = None
    ward: Optional[str] = None
    bed_number: Optional[str] = None
    date_of_surgery: Optional[str] = None
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    duration_minutes: Optional[str] = None
    surgeon_name: Optional[str] = None
    assistant_surgeon: Optional[str] = None
    anesthetist: Optional[str] = None
    scrub_nurse: Optional[str] = None
    circulating_nurse: Optional[str] = None
    pre_op_diagnosis: Optional[str] = None
    post_op_diagnosis: Optional[str] = None
    type_of_anesthesia: Optional[str] = None
    procedure_name: Optional[str] = None
    procedure_description: Optional[str] = None
    intra_op_findings: Optional[str] = None
    blood_loss_ml: Optional[str] = None
    fluids_given: Optional[str] = None
    sponge_count_correct: Optional[str] = None
    instrument_count_correct: Optional[str] = None
    needle_count_correct: Optional[str] = None
    implants_used: Optional[str] = None
    consumables: Optional[str] = None
    complications: Optional[str] = None
    drain_placed: Optional[str] = None
    wound_closure: Optional[str] = None
    specimen_sent: Optional[str] = None
    post_op_instructions: Optional[str] = None
    disposition: Optional[str] = None
    raw_transcription: Optional[str] = None
    status: Optional[str] = None


def _note_to_dict(n: OTNote) -> dict:
    return {
        "id": n.id,
        "status": n.status,
        "patient_name": n.patient_name,
        "patient_mrn": n.patient_mrn,
        "patient_age": n.patient_age,
        "patient_gender": n.patient_gender,
        "ward": n.ward,
        "bed_number": n.bed_number,
        "date_of_surgery": n.date_of_surgery,
        "time_start": n.time_start,
        "time_end": n.time_end,
        "duration_minutes": n.duration_minutes,
        "surgeon_id": n.surgeon_id,
        "surgeon_name": n.surgeon_name,
        "assistant_surgeon": n.assistant_surgeon,
        "anesthetist": n.anesthetist,
        "scrub_nurse": n.scrub_nurse,
        "circulating_nurse": n.circulating_nurse,
        "pre_op_diagnosis": n.pre_op_diagnosis,
        "post_op_diagnosis": n.post_op_diagnosis,
        "type_of_anesthesia": n.type_of_anesthesia,
        "procedure_name": n.procedure_name,
        "procedure_description": n.procedure_description,
        "intra_op_findings": n.intra_op_findings,
        "blood_loss_ml": n.blood_loss_ml,
        "fluids_given": n.fluids_given,
        "sponge_count_correct": n.sponge_count_correct,
        "instrument_count_correct": n.instrument_count_correct,
        "needle_count_correct": n.needle_count_correct,
        "implants_used": n.implants_used,
        "consumables": n.consumables,
        "complications": n.complications,
        "drain_placed": n.drain_placed,
        "wound_closure": n.wound_closure,
        "specimen_sent": n.specimen_sent,
        "post_op_instructions": n.post_op_instructions,
        "disposition": n.disposition,
        "raw_transcription": n.raw_transcription,
        "missing_fields": n.missing_fields or [],
        "ai_confidence": n.ai_confidence,
        "signed_by": n.signed_by,
        "signed_at": n.signed_at.isoformat() if n.signed_at else None,
        "signature_data": n.signature_data,
        "version": n.version,
        "audit_trail": n.audit_trail or [],
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "updated_at": n.updated_at.isoformat() if n.updated_at else None,
    }


@router.post("/", status_code=201)
async def create_note(
    body: NoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = OTNote(
        surgeon_id=current_user.id,
        surgeon_name=current_user.full_name,
        status="draft",
        audit_trail=[{
            "action": "created",
            "user": current_user.full_name,
            "timestamp": datetime.utcnow().isoformat(),
            "note": "OT Note created",
        }],
        **body.model_dump(exclude_none=True),
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return _note_to_dict(note)


@router.get("/")
async def list_notes(
    status: str = None,
    search: str = "",
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(OTNote).order_by(desc(OTNote.created_at)).limit(limit).offset(offset)
    if current_user.role not in ("admin", "staff"):
        q = q.where(OTNote.surgeon_id == current_user.id)
    if status:
        q = q.where(OTNote.status == status)
    if search:
        q = q.where(
            or_(
                OTNote.patient_name.ilike(f"%{search}%"),
                OTNote.patient_mrn.ilike(f"%{search}%"),
                OTNote.procedure_name.ilike(f"%{search}%"),
            )
        )
    result = await db.execute(q)
    notes = result.scalars().all()
    return [_note_to_dict(n) for n in notes]


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import func
    base = select(OTNote)
    if current_user.role not in ("admin", "staff"):
        base = base.where(OTNote.surgeon_id == current_user.id)

    all_notes = (await db.execute(base)).scalars().all()
    total = len(all_notes)
    signed = sum(1 for n in all_notes if n.status == "signed")
    drafts = sum(1 for n in all_notes if n.status in ("draft", "review", "processing", "dictating"))
    incomplete = sum(1 for n in all_notes if n.missing_fields)

    return {
        "total": total,
        "signed": signed,
        "drafts": drafts,
        "incomplete": incomplete,
        "completion_rate": round((signed / total * 100) if total else 0, 1),
    }


@router.get("/{note_id}")
async def get_note(
    note_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(OTNote).where(OTNote.id == note_id))
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(404, "Note not found")
    return _note_to_dict(note)


@router.patch("/{note_id}")
async def update_note(
    note_id: str,
    body: NoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(OTNote).where(OTNote.id == note_id))
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(404, "Note not found")
    if note.status == "signed":
        raise HTTPException(400, "Cannot edit a signed note")

    updates = body.model_dump(exclude_none=True)
    for k, v in updates.items():
        setattr(note, k, v)

    trail = note.audit_trail or []
    trail.append({
        "action": "updated",
        "user": current_user.full_name,
        "timestamp": datetime.utcnow().isoformat(),
        "note": f"Fields updated: {list(updates.keys())}",
    })
    note.audit_trail = trail
    await db.commit()
    await db.refresh(note)
    return _note_to_dict(note)


@router.post("/{note_id}/sign")
async def sign_note(
    note_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(OTNote).where(OTNote.id == note_id))
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(404, "Note not found")
    if note.status == "signed":
        raise HTTPException(400, "Note already signed")

    note.status = "signed"
    note.signed_by = current_user.full_name
    note.signed_at = datetime.utcnow()
    note.signature_data = body.get("signature_data")

    trail = note.audit_trail or []
    trail.append({
        "action": "signed",
        "user": current_user.full_name,
        "timestamp": datetime.utcnow().isoformat(),
        "note": "Note digitally signed and finalized",
    })
    note.audit_trail = trail

    int_version = int(note.version or "1")
    note.version = str(int_version + 1)

    await db.commit()
    await db.refresh(note)
    return {"success": True, "signed_at": note.signed_at.isoformat(), "note": _note_to_dict(note)}


@router.get("/{note_id}/export/pdf")
async def export_pdf(
    note_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(OTNote).where(OTNote.id == note_id))
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(404, "Note not found")

    pdf_bytes = generate_ot_note_pdf(_note_to_dict(note))
    filename = f"OT_Note_{note.patient_mrn or note_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{note_id}")
async def delete_note(
    note_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(OTNote).where(OTNote.id == note_id))
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(404, "Note not found")
    if note.status == "signed":
        raise HTTPException(400, "Cannot delete a signed note")
    await db.delete(note)
    await db.commit()
    return {"success": True}
