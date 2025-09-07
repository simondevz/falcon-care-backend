"""
Encounter management controller
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any
from uuid import UUID
import json

from database.connection import get_db
from models.encounter import Encounter
from models.patient import Patient
from schemas.encounter import (
    EncounterCreate,
    EncounterUpdate,
    EncounterResponse,
    EncounterProcessRequest,
    EncounterProcessResponse,
)
from utils.auth import get_current_user

router = APIRouter()


@router.post("/", response_model=EncounterResponse, status_code=201)
async def create_encounter(
    encounter_data: EncounterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Create a new encounter from clinical notes
    """
    # Verify patient exists
    patient_result = await db.execute(
        select(Patient).where(Patient.id == encounter_data.patient_id)
    )
    patient = patient_result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Create encounter
    encounter = Encounter(
        **encounter_data.model_dump(), created_by=UUID(current_user["user_id"])
    )

    db.add(encounter)
    await db.commit()
    await db.refresh(encounter)

    return EncounterResponse.model_validate(encounter)


@router.get("/{encounter_id}", response_model=EncounterResponse)
async def get_encounter(
    encounter_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get encounter details by ID
    """
    result = await db.execute(select(Encounter).where(Encounter.id == encounter_id))
    encounter = result.scalar_one_or_none()

    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    return EncounterResponse.model_validate(encounter)


@router.put("/{encounter_id}", response_model=EncounterResponse)
async def update_encounter(
    encounter_id: UUID,
    encounter_data: EncounterUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Update encounter information
    """
    result = await db.execute(select(Encounter).where(Encounter.id == encounter_id))
    encounter = result.scalar_one_or_none()

    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    # Update only provided fields
    update_data = encounter_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(encounter, field, value)

    await db.commit()
    await db.refresh(encounter)

    return EncounterResponse.model_validate(encounter)


@router.post("/{encounter_id}/process", response_model=EncounterProcessResponse)
async def process_encounter(
    encounter_id: UUID,
    process_request: EncounterProcessRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Process encounter with AI to extract structured data and suggest codes
    This is a placeholder - will be connected to LangGraph workflows later
    """
    result = await db.execute(select(Encounter).where(Encounter.id == encounter_id))
    encounter = result.scalar_one_or_none()

    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    if not encounter.raw_notes:
        raise HTTPException(status_code=400, detail="No raw notes to process")

    # Mock AI processing (replace with actual AI service later)
    mock_structured_data = {
        "patient": {
            "chief_complaint": "Chest pain",
            "symptoms": ["chest pain", "shortness of breath"],
            "vital_signs": {
                "blood_pressure": "140/90",
                "heart_rate": "85",
                "temperature": "98.6",
            },
        },
        "assessment": {
            "primary_diagnosis": "Chest pain, unspecified",
            "secondary_diagnoses": [],
        },
        "plan": {
            "procedures": ["ECG", "Blood work"],
            "medications": [],
            "follow_up": "Return if symptoms worsen",
        },
    }

    mock_suggested_codes = {
        "icd10_codes": [
            {
                "code": "R06.00",
                "description": "Dyspnea, unspecified",
                "confidence": 0.85,
                "rationale": "Patient reported shortness of breath",
            }
        ],
        "cpt_codes": [
            {
                "code": "93000",
                "description": "Electrocardiogram, routine ECG with at least 12 leads",
                "confidence": 0.90,
                "rationale": "ECG ordered for chest pain evaluation",
            }
        ],
    }

    # Update encounter with structured data
    encounter.structured_data = mock_structured_data
    encounter.status = "reviewed"

    await db.commit()
    await db.refresh(encounter)

    return EncounterProcessResponse(
        encounter_id=encounter_id,
        status="processed",
        structured_data=mock_structured_data,
        confidence_score=0.88,
        suggested_codes=mock_suggested_codes,
    )


@router.get("/")
async def list_encounters(
    patient_id: UUID = Query(None, description="Filter by patient ID"),
    status: str = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    List encounters with optional filters
    """
    query = select(Encounter)

    # Apply filters
    if patient_id:
        query = query.where(Encounter.patient_id == patient_id)
    if status:
        query = query.where(Encounter.status == status)

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(Encounter.service_date.desc())

    result = await db.execute(query)
    encounters = result.scalars().all()

    return {
        "encounters": [EncounterResponse.model_validate(e) for e in encounters],
        "page": page,
        "per_page": per_page,
    }


@router.delete("/{encounter_id}")
async def delete_encounter(
    encounter_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Delete an encounter
    """
    result = await db.execute(select(Encounter).where(Encounter.id == encounter_id))
    encounter = result.scalar_one_or_none()

    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    await db.delete(encounter)
    await db.commit()

    return {
        "message": "Encounter deleted successfully",
        "encounter_id": str(encounter_id),
    }
