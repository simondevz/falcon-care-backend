"""
Patient Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date, datetime
from uuid import UUID


class PatientBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    date_of_birth: date
    gender: str = Field(..., pattern="^(male|female|other)$")
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    insurance_provider: Optional[str] = Field(None, max_length=255)
    policy_number: Optional[str] = Field(None, max_length=100)
    mrn: str = Field(..., min_length=1, max_length=50)


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, pattern="^(male|female|other)$")
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    insurance_provider: Optional[str] = Field(None, max_length=255)
    policy_number: Optional[str] = Field(None, max_length=100)


class PatientResponse(PatientBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PatientListResponse(BaseModel):
    patients: list[PatientResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
