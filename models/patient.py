"""
Patient data model
"""

from sqlalchemy import Column, String, Date, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from database.connection import Base
import uuid


class Patient(Base):
    __tablename__ = "patients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(String(20), nullable=False)
    phone = Column(String(20))
    email = Column(String(255))
    address = Column(Text)
    insurance_provider = Column(String(255))
    policy_number = Column(String(100))
    mrn = Column(String(50), unique=True, nullable=False)  # Medical Record Number
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "date_of_birth": (
                self.date_of_birth.isoformat() if self.date_of_birth else None
            ),
            "gender": self.gender,
            "phone": self.phone,
            "email": self.email,
            "address": self.address,
            "insurance_provider": self.insurance_provider,
            "policy_number": self.policy_number,
            "mrn": self.mrn,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
