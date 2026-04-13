"""
SQLAlchemy model for Doctor-Patient Consultation records.
"""
from database import Base
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime


class Consultation(Base):
    __tablename__ = "consultations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # ── Status ─────────────────────────────────────────────────────────────
    status = Column(String(50), default="draft")
    # draft | recording | processing | review | finalized

    # ── Patient Info ───────────────────────────────────────────────────────
    patient_id = Column(String, ForeignKey("patients.id"), nullable=True)
    patient_name = Column(String(200), nullable=True)
    patient_mrn = Column(String(100), nullable=True)
    patient_age = Column(String(20), nullable=True)
    patient_gender = Column(String(20), nullable=True)
    chief_complaint = Column(Text, nullable=True)

    # ── Doctor Info ────────────────────────────────────────────────────────
    doctor_id = Column(String, ForeignKey("users.id"), nullable=True)
    doctor_name = Column(String(200), nullable=True)
    consultation_date = Column(String(30), nullable=True)
    consultation_time = Column(String(20), nullable=True)
    department = Column(String(200), nullable=True)

    # ── Raw Conversation ───────────────────────────────────────────────────
    raw_transcription = Column(Text, nullable=True)

    # ── AI-Extracted Clinical Fields ───────────────────────────────────────
    diagnosis = Column(Text, nullable=True)                     # Primary diagnosis
    differential_diagnosis = Column(Text, nullable=True)        # DDx
    history_of_present_illness = Column(Text, nullable=True)    # HPI summary
    examination_findings = Column(Text, nullable=True)          # Clinical exam

    # Prescription (JSON list of {drug, dose, frequency, duration, route, notes})
    prescription = Column(JSON, default=list)

    # Lab tests (JSON list of {test_name, urgency, reason})
    lab_tests = Column(JSON, default=list)

    # Imaging (JSON list of {modality, region, reason})
    imaging_ordered = Column(JSON, default=list)

    # Follow-up
    follow_up_date = Column(String(50), nullable=True)
    follow_up_instructions = Column(Text, nullable=True)

    # Referral
    referral = Column(Text, nullable=True)

    # Lifestyle / advice
    lifestyle_advice = Column(Text, nullable=True)

    # ── AI Meta ────────────────────────────────────────────────────────────
    missing_fields = Column(JSON, default=list)
    ai_confidence = Column(String(20), nullable=True)

    # ── Audit ──────────────────────────────────────────────────────────────
    audit_trail = Column(JSON, default=list)

    # ── Timestamps ─────────────────────────────────────────────────────────
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(DateTime, default=lambda: datetime.utcnow(),
                        onupdate=lambda: datetime.utcnow())

    doctor = relationship("User", foreign_keys=[doctor_id])
