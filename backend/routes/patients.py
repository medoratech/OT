"""Patient management routes."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from pydantic import BaseModel

from database import get_db
from models.patient import Patient
from models.user import User
from utils.auth import get_current_user

router = APIRouter(prefix="/api/patients", tags=["Patients"])


class PatientCreate(BaseModel):
    mrn: str
    full_name: str
    dob: Optional[str] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    contact_number: Optional[str] = None
    address: Optional[str] = None
    ward: Optional[str] = None
    bed_number: Optional[str] = None
    admission_date: Optional[str] = None


@router.post("/", status_code=201)
async def create_patient(
    body: PatientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = await db.execute(select(Patient).where(Patient.mrn == body.mrn))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="MRN already exists")
    patient = Patient(**body.model_dump())
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient


@router.get("/")
async def list_patients(
    search: str = "",
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Patient).order_by(Patient.created_at.desc()).limit(limit)
    if search:
        q = q.where(
            or_(
                Patient.full_name.ilike(f"%{search}%"),
                Patient.mrn.ilike(f"%{search}%"),
            )
        )
    result = await db.execute(q)
    patients = result.scalars().all()
    return [
        {
            "id": p.id,
            "mrn": p.mrn,
            "full_name": p.full_name,
            "dob": p.dob,
            "gender": p.gender,
            "blood_group": p.blood_group,
            "ward": p.ward,
            "bed_number": p.bed_number,
            "admission_date": p.admission_date,
        }
        for p in patients
    ]


@router.get("/{patient_id}")
async def get_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    return p
