from database import Base
from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timezone


class OTNote(Base):
    __tablename__ = "ot_notes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # ── Status ─────────────────────────────────────────────────────────────
    status = Column(String(50), default="draft")
    # draft | dictating | processing | review | signed | archived

    # ── Identifiers ────────────────────────────────────────────────────────
    patient_id = Column(String, ForeignKey("patients.id"), nullable=True)
    patient_name = Column(String(200), nullable=True)
    patient_mrn = Column(String(100), nullable=True)
    patient_age = Column(String(20), nullable=True)
    patient_gender = Column(String(20), nullable=True)
    ward = Column(String(100), nullable=True)
    bed_number = Column(String(50), nullable=True)

    # ── Procedure Timing ───────────────────────────────────────────────────
    date_of_surgery = Column(String(30), nullable=True)
    time_start = Column(String(20), nullable=True)
    time_end = Column(String(20), nullable=True)
    duration_minutes = Column(String(20), nullable=True)

    # ── Care Team ──────────────────────────────────────────────────────────
    surgeon_id = Column(String, ForeignKey("users.id"), nullable=True)
    surgeon_name = Column(String(200), nullable=True)
    assistant_surgeon = Column(String(300), nullable=True)
    anesthetist = Column(String(200), nullable=True)
    scrub_nurse = Column(String(200), nullable=True)
    circulating_nurse = Column(String(200), nullable=True)

    # ── Clinical Content ───────────────────────────────────────────────────
    pre_op_diagnosis = Column(Text, nullable=True)
    post_op_diagnosis = Column(Text, nullable=True)
    type_of_anesthesia = Column(String(100), nullable=True)
    procedure_name = Column(String(300), nullable=True)
    procedure_description = Column(Text, nullable=True)
    intra_op_findings = Column(Text, nullable=True)

    # ── Safety & Counts ────────────────────────────────────────────────────
    blood_loss_ml = Column(String(50), nullable=True)
    fluids_given = Column(Text, nullable=True)
    sponge_count_correct = Column(String(20), nullable=True)   # yes | no | not_done
    instrument_count_correct = Column(String(20), nullable=True)
    needle_count_correct = Column(String(20), nullable=True)

    # ── Implants / Consumables ─────────────────────────────────────────────
    implants_used = Column(Text, nullable=True)
    consumables = Column(Text, nullable=True)

    # ── Complications & Outcome ────────────────────────────────────────────
    complications = Column(Text, nullable=True)
    drain_placed = Column(String(20), nullable=True)
    wound_closure = Column(Text, nullable=True)
    specimen_sent = Column(Text, nullable=True)

    # ── Post-op ────────────────────────────────────────────────────────────
    post_op_instructions = Column(Text, nullable=True)
    disposition = Column(String(100), nullable=True)  # ICU | ward | recovery | home

    # ── AI Processing ──────────────────────────────────────────────────────
    raw_transcription = Column(Text, nullable=True)
    audio_file_path = Column(String(500), nullable=True)
    audio_deleted = Column(Boolean, default=False)
    missing_fields = Column(JSON, default=list)
    ai_confidence = Column(String(20), nullable=True)

    # ── Signature & Audit ──────────────────────────────────────────────────
    signed_by = Column(String(200), nullable=True)
    signed_at = Column(DateTime, nullable=True)
    signature_data = Column(Text, nullable=True)      # Base64 image of signature
    version = Column(String(10), default="1")
    audit_trail = Column(JSON, default=list)          # [{action, user, timestamp, note}]

    # ── Timestamps ─────────────────────────────────────────────────────────
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(DateTime, default=lambda: datetime.utcnow(),
                        onupdate=lambda: datetime.utcnow())

    surgeon = relationship("User", back_populates="ot_notes", foreign_keys=[surgeon_id])
