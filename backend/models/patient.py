from database import Base
from sqlalchemy import Column, String, DateTime, Integer
import uuid
from datetime import datetime, timezone


class Patient(Base):
    __tablename__ = "patients"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    mrn = Column(String(100), unique=True, nullable=False, index=True)   # Medical Record Number
    full_name = Column(String(200), nullable=False)
    dob = Column(String(20), nullable=True)                               # ISO date string
    gender = Column(String(20), nullable=True)
    blood_group = Column(String(10), nullable=True)
    contact_number = Column(String(20), nullable=True)
    address = Column(String(500), nullable=True)
    ward = Column(String(100), nullable=True)
    bed_number = Column(String(50), nullable=True)
    admission_date = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(DateTime, default=lambda: datetime.utcnow(),
                        onupdate=lambda: datetime.utcnow())
