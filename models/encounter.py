"""
Encounter data model
"""

from sqlalchemy import Column, String, Date, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.connection import Base
import uuid


class Encounter(Base):
    __tablename__ = "encounters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    encounter_type = Column(
        String(100), nullable=False
    )  # outpatient, inpatient, emergency, etc.
    service_date = Column(Date, nullable=False)
    raw_notes = Column(Text)  # Original unstructured clinical notes
    structured_data = Column(JSON)  # AI-processed structured data
    status = Column(String(50), default="draft")  # draft, reviewed, approved, billed
    created_by = Column(UUID(as_uuid=True))  # User who created the encounter
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship to patient
    patient = relationship("Patient", back_populates="encounters")

    def to_dict(self):
        return {
            "id": str(self.id),
            "patient_id": str(self.patient_id),
            "encounter_type": self.encounter_type,
            "service_date": (
                self.service_date.isoformat() if self.service_date else None
            ),
            "raw_notes": self.raw_notes,
            "structured_data": self.structured_data,
            "status": self.status,
            "created_by": str(self.created_by) if self.created_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# Add relationship to Patient model
from models.patient import Patient

Patient.encounters = relationship("Encounter", back_populates="patient")
