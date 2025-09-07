"""
Denial data model
"""

from sqlalchemy import Column, String, Date, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.connection import Base
import uuid


class Denial(Base):
    __tablename__ = "denials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id = Column(UUID(as_uuid=True), ForeignKey("claims.id"), nullable=False)
    denial_code = Column(String(50), nullable=False)
    denial_reason = Column(Text, nullable=False)
    status = Column(
        String(50), default="received"
    )  # received, under_review, appealed, resolved
    appeal_data = Column(JSON)  # Appeal information and documentation
    denied_at = Column(Date, nullable=False)
    appeal_submitted_at = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship
    claim = relationship("Claim", back_populates="denials")

    def to_dict(self):
        return {
            "id": str(self.id),
            "claim_id": str(self.claim_id),
            "denial_code": self.denial_code,
            "denial_reason": self.denial_reason,
            "status": self.status,
            "appeal_data": self.appeal_data,
            "denied_at": self.denied_at.isoformat() if self.denied_at else None,
            "appeal_submitted_at": (
                self.appeal_submitted_at.isoformat()
                if self.appeal_submitted_at
                else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
