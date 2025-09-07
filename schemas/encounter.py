"""
Encounter Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import date, datetime
from uuid import UUID


class EncounterBase(BaseModel):
    patient_id: UUID
    encounter_type: str = Field(
        ..., pattern="^(outpatient|inpatient|emergency|telemedicine)$"
    )
    service_date: date
    raw_notes: Optional[str] = None


class EncounterCreate(EncounterBase):
    pass


class EncounterUpdate(BaseModel):
    encounter_type: Optional[str] = Field(
        None, pattern="^(outpatient|inpatient|emergency|telemedicine)$"
    )
    service_date: Optional[date] = None
    raw_notes: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    status: Optional[str] = Field(None, pattern="^(draft|reviewed|approved|billed)$")


class EncounterResponse(EncounterBase):
    id: UUID
    structured_data: Optional[Dict[str, Any]] = None
    status: str
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EncounterProcessRequest(BaseModel):
    """Request to process encounter with AI"""

    encounter_id: UUID
    force_reprocess: bool = False


class EncounterProcessResponse(BaseModel):
    """Response from AI processing"""

    encounter_id: UUID
    status: str
    structured_data: Dict[str, Any]
    confidence_score: Optional[float] = None
    suggested_codes: Optional[Dict[str, Any]] = None
