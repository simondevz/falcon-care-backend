"""
Patient management controller
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List
from uuid import UUID

from database.connection import get_db
from models.patient import Patient
from schemas.patient import (
    PatientCreate,
    PatientUpdate,
    PatientResponse,
    PatientListResponse,
)
from utils.auth import get_current_user

router = APIRouter()


@router.post("/", response_model=PatientResponse, status_code=201)
async def create_patient(
    patient_data: PatientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Create a new patient record
    """
    # Check if MRN already exists
    existing_patient = await db.execute(
        select(Patient).where(Patient.mrn == patient_data.mrn)
    )
    if existing_patient.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Patient with MRN {patient_data.mrn} already exists",
        )

    # Create new patient
    patient = Patient(**patient_data.model_dump())
    db.add(patient)
    await db.commit()
    await db.refresh(patient)

    return PatientResponse.model_validate(patient)


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get patient details by ID
    """
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    return PatientResponse.model_validate(patient)


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: UUID,
    patient_data: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Update patient information
    """
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Update only provided fields
    update_data = patient_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)

    await db.commit()
    await db.refresh(patient)

    return PatientResponse.model_validate(patient)


@router.get("/", response_model=PatientListResponse)
async def list_patients(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: str = Query(None, description="Search by name or MRN"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    List patients with pagination and optional search
    """
    # Build base query
    query = select(Patient)
    count_query = select(func.count(Patient.id))

    # Apply search filter if provided
    if search:
        search_filter = Patient.name.ilike(f"%{search}%") | Patient.mrn.ilike(
            f"%{search}%"
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(Patient.created_at.desc())

    # Execute query
    result = await db.execute(query)
    patients = result.scalars().all()

    # Calculate pagination info
    total_pages = (total + per_page - 1) // per_page

    return PatientListResponse(
        patients=[PatientResponse.model_validate(p) for p in patients],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.delete("/{patient_id}")
async def delete_patient(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Delete a patient record (soft delete in production)
    """
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # In production, implement soft delete instead
    await db.delete(patient)
    await db.commit()

    return {"message": "Patient deleted successfully", "patient_id": str(patient_id)}


@router.get("/{patient_id}/encounters")
async def get_patient_encounters(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get all encounters for a specific patient
    """
    # First check if patient exists
    patient_result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = patient_result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Get encounters with patient data
    from models.encounter import Encounter

    encounters_result = await db.execute(
        select(Encounter)
        .where(Encounter.patient_id == patient_id)
        .order_by(Encounter.service_date.desc())
    )
    encounters = encounters_result.scalars().all()

    return {
        "patient_id": str(patient_id),
        "patient_name": patient.name,
        "encounters": [encounter.to_dict() for encounter in encounters],
    }
