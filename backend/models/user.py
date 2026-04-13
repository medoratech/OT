from database import Base
from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timezone


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = Column(String(200), nullable=False)
    email = Column(String(200), unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String(50), default="surgeon")        # surgeon | resident | staff | admin
    designation = Column(String(200), nullable=True)
    hospital = Column(String(300), nullable=True)
    department = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    digital_signature = Column(Text, nullable=True)     # Base64 sig image
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(DateTime, default=lambda: datetime.utcnow(),
                        onupdate=lambda: datetime.utcnow())

    ot_notes = relationship("OTNote", back_populates="surgeon", foreign_keys="OTNote.surgeon_id")
