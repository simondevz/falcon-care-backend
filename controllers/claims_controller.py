"""
Claims management controller
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Dict, Any
from uuid import UUID
from datetime import datetime, date
import random
import string

from database.connection import get_db
from models.claim import Claim
from models.patient import Patient
from models.encounter import Encounter
from models.denial import Denial
from schemas.claim import (
    ClaimCreate,
    ClaimUpdate,
    ClaimResponse,
    ClaimSubmissionRequest,
    ClaimSubmissionResponse,
    EligibilityCheckRequest,
    EligibilityCheckResponse,
)
from utils.auth import get_current_user

router = APIRouter()


def generate_claim_number() -> str:
    """Generate a unique claim number"""
    return "CLM" + "".join(random.choices(string.digits, k=8))


@router.post("/", response_model=ClaimResponse, status_code=201)
async def create_claim(
    claim_data: ClaimCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Create a new claim from an encounter
    """
    # Verify patient and encounter exist
    patient_result = await db.execute(
        select(Patient).where(Patient.id == claim_data.patient_id)
    )
    patient = patient_result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    encounter_result = await db.execute(
        select(Encounter).where(Encounter.id == claim_data.encounter_id)
    )
    encounter = encounter_result.scalar_one_or_none()

    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    # Generate claim number
    claim_number = generate_claim_number()

    # Create claim
    claim = Claim(**claim_data.model_dump(), claim_number=claim_number)

    db.add(claim)
    await db.commit()
    await db.refresh(claim)

    return ClaimResponse.model_validate(claim)


@router.get("/{claim_id}", response_model=ClaimResponse)
async def get_claim(
    claim_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get claim details by ID
    """
    result = await db.execute(select(Claim).where(Claim.id == claim_id))
    claim = result.scalar_one_or_none()

    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    return ClaimResponse.model_validate(claim)


@router.put("/{claim_id}", response_model=ClaimResponse)
async def update_claim(
    claim_id: UUID,
    claim_data: ClaimUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Update claim information
    """
    result = await db.execute(select(Claim).where(Claim.id == claim_id))
    claim = result.scalar_one_or_none()

    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    # Update only provided fields
    update_data = claim_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(claim, field, value)

    await db.commit()
    await db.refresh(claim)

    return ClaimResponse.model_validate(claim)


@router.post("/{claim_id}/submit", response_model=ClaimSubmissionResponse)
async def submit_claim(
    claim_id: UUID,
    submission_request: ClaimSubmissionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Submit claim to payer (mock implementation)
    """
    result = await db.execute(select(Claim).where(Claim.id == claim_id))
    claim = result.scalar_one_or_none()

    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    if claim.status == "submitted":
        raise HTTPException(status_code=400, detail="Claim already submitted")

    # Mock payer submission
    reference_number = "REF" + "".join(random.choices(string.digits, k=10))

    # Update claim status
    claim.status = "submitted"
    claim.submitted_at = datetime.utcnow()

    # Apply mock payer rules
    claim.payer_rules_applied = {
        "eligibility_verified": True,
        "pre_auth_required": False,
        "rules_passed": ["medical_necessity", "billing_accuracy"],
        "warnings": [],
    }

    await db.commit()

    return ClaimSubmissionResponse(
        claim_id=claim_id,
        submission_status="submitted",
        reference_number=reference_number,
        estimated_processing_days=5,
        message="Claim submitted successfully to payer",
    )


@router.get("/")
async def list_claims(
    patient_id: UUID = Query(None, description="Filter by patient ID"),
    status: str = Query(None, description="Filter by status"),
    payer_id: str = Query(None, description="Filter by payer"),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    List claims with optional filters
    """
    query = select(Claim)
    count_query = select(func.count(Claim.id))

    # Apply filters
    if patient_id:
        query = query.where(Claim.patient_id == patient_id)
        count_query = count_query.where(Claim.patient_id == patient_id)
    if status:
        query = query.where(Claim.status == status)
        count_query = count_query.where(Claim.status == status)
    if payer_id:
        query = query.where(Claim.payer_id == payer_id)
        count_query = count_query.where(Claim.payer_id == payer_id)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(Claim.created_at.desc())

    result = await db.execute(query)
    claims = result.scalars().all()

    total_pages = (total + per_page - 1) // per_page

    return {
        "claims": [ClaimResponse.model_validate(c) for c in claims],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }


@router.post("/check-eligibility", response_model=EligibilityCheckResponse)
async def check_eligibility(
    eligibility_request: EligibilityCheckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Check patient eligibility with payer (mock implementation)
    """
    # Verify patient exists
    patient_result = await db.execute(
        select(Patient).where(Patient.id == eligibility_request.patient_id)
    )
    patient = patient_result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Mock eligibility check
    mock_response = {
        "deductible_remaining": 500.00,
        "copay_amount": 25.00,
        "coverage_percentage": 80,
        "requires_prior_auth": False,
        "covered_services": ["outpatient", "diagnostic"],
        "limitations": [],
    }

    return EligibilityCheckResponse(
        patient_id=eligibility_request.patient_id,
        eligible=True,
        coverage_details=mock_response,
        confidence_score=0.95,
        message="Patient is eligible for coverage",
    )


@router.get("/{claim_id}/denials")
async def get_claim_denials(
    claim_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get all denials for a specific claim
    """
    # Verify claim exists
    claim_result = await db.execute(select(Claim).where(Claim.id == claim_id))
    claim = claim_result.scalar_one_or_none()

    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    # Get denials
    denials_result = await db.execute(
        select(Denial)
        .where(Denial.claim_id == claim_id)
        .order_by(Denial.denied_at.desc())
    )
    denials = denials_result.scalars().all()

    return {
        "claim_id": str(claim_id),
        "denials": [denial.to_dict() for denial in denials],
    }


@router.delete("/{claim_id}")
async def delete_claim(
    claim_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Delete a claim
    """
    result = await db.execute(select(Claim).where(Claim.id == claim_id))
    claim = result.scalar_one_or_none()

    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    if claim.status == "submitted":
        raise HTTPException(status_code=400, detail="Cannot delete submitted claim")

    await db.delete(claim)
    await db.commit()

    return {"message": "Claim deleted successfully", "claim_id": str(claim_id)}
