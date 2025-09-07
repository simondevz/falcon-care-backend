"""
Claim data model
"""

from sqlalchemy import Column, String, Date, DateTime, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.connection import Base
import uuid


class Claim(Base):
    __tablename__ = "claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    encounter_id = Column(
        UUID(as_uuid=True), ForeignKey("encounters.id"), nullable=False
    )
    claim_number = Column(String(100), unique=True)
    status = Column(
        String(50), default="draft"
    )  # draft, submitted, processing, paid, denied
    payer_id = Column(String(100), nullable=False)  # Insurance payer identifier
    total_amount = Column(Numeric(10, 2), nullable=False)
    patient_responsibility = Column(Numeric(10, 2), default=0.00)
    diagnosis_codes = Column(JSON)  # ICD-10 codes
    procedure_codes = Column(JSON)  # CPT codes
    payer_rules_applied = Column(JSON)  # Rules that were applied during processing
    submitted_at = Column(DateTime(timezone=True))
    processed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    patient = relationship("Patient")
    encounter = relationship("Encounter")
    denials = relationship("Denial", back_populates="claim")

    def to_dict(self):
        return {
            "id": str(self.id),
            "patient_id": str(self.patient_id),
            "encounter_id": str(self.encounter_id),
            "claim_number": self.claim_number,
            "status": self.status,
            "payer_id": self.payer_id,
            "total_amount": float(self.total_amount) if self.total_amount else 0.0,
            "patient_responsibility": (
                float(self.patient_responsibility)
                if self.patient_responsibility
                else 0.0
            ),
            "diagnosis_codes": self.diagnosis_codes,
            "procedure_codes": self.procedure_codes,
            "payer_rules_applied": self.payer_rules_applied,
            "submitted_at": (
                self.submitted_at.isoformat() if self.submitted_at else None
            ),
            "processed_at": (
                self.processed_at.isoformat() if self.processed_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
