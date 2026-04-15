"""
Speech routes — upload audio, get transcript, trigger Gemini structuring.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.user import User
from models.ot_note import OTNote
from utils.auth import get_current_user
from services.deepgram_service import transcribe_audio
from services.gemini_service import structure_dictation
from services.sarvam_service import synthesize_speech

router = APIRouter(prefix="/api/speech", tags=["Speech"])


@router.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    note_id: str = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload audio → Deepgram transcription."""
    audio_bytes = await audio.read()
    mime = audio.content_type or "audio/webm"

    result = await transcribe_audio(audio_bytes, mime_type=mime)
    transcript = result["transcript"]

    # Optionally attach transcript to existing note
    if note_id:
        res = await db.execute(select(OTNote).where(OTNote.id == note_id))
        note = res.scalar_one_or_none()
        if note:
            note.raw_transcription = (note.raw_transcription or "") + "\n" + transcript
            note.status = "processing"
            await db.commit()

    return {
        "transcript": transcript,
        "confidence": result["confidence"],
        "words": result["words"],
        "duration": result["duration"],
        "note_id": note_id,
    }


@router.post("/structure")
async def structure(
    note_id: str,
    transcription: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send transcription to Gemini → structured OT note fields."""
    res = await db.execute(select(OTNote).where(OTNote.id == note_id))
    note = res.scalar_one_or_none()
    if not note:
        raise HTTPException(404, "Note not found")

    text = transcription or note.raw_transcription or ""
    if not text.strip():
        raise HTTPException(400, "No transcription available to structure")

    result = await structure_dictation(text)
    structured = result["structured"]
    missing = result["missing_fields"]

    # Merge extracted fields into note
    for field, value in structured.items():
        if hasattr(note, field) and value is not None:
            setattr(note, field, value)

    note.missing_fields = missing
    note.status = "review"

    # Audit trail
    trail = note.audit_trail or []
    trail.append({
        "action": "ai_structured",
        "user": current_user.full_name,
        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        "note": f"Gemini extracted {len(structured)} fields. Missing: {missing}",
    })
    note.audit_trail = trail
    await db.commit()
    await db.refresh(note)

    return {
        "structured": structured,
        "missing_fields": missing,
        "note_id": note_id,
    }


@router.post("/tts")
async def text_to_speech(
    text: str,
    language: str = "en-IN",
    current_user: User = Depends(get_current_user),
):
    """Convert text to speech using Sarvam AI."""
    if not text.strip():
        raise HTTPException(400, "No text provided")
    audio_bytes = await synthesize_speech(text, language_code=language)
    return Response(content=audio_bytes, media_type="audio/wav")
