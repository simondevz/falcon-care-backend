"""
Claim Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List, Literal
from datetime import date, datetime
from uuid import UUID
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

# Configurable rules:
MAX_DIGITS = 10  # total digits (integer + fractional) allowed
DECIMAL_PLACES = 2  # decimal places to quantize to
QUANT = Decimal("0.01")  # Decimal('0.01') for 2 places


def _enforce_decimal_value(value) -> Decimal:
    """
    Convert input to Decimal, quantize to DECIMAL_PLACES, enforce >= 0 and max digits.
    Accepts str, int, float, Decimal.
    """
    if value is None:
        return value
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ValueError("value is not a valid decimal")

    # round / quantize to required decimal places
    d = d.quantize(QUANT, rounding=ROUND_HALF_UP)

    # non-negative check
    if d < Decimal("0"):
        raise ValueError("value must be >= 0")

    # check total digits (remove sign and decimal point)
    s = f"{d:.{DECIMAL_PLACES}f}".replace("-", "").replace(".", "")
    if len(s) > MAX_DIGITS:
        raise ValueError(f"value has too many digits (max {MAX_DIGITS})")

    return d


class ClaimBase(BaseModel):
    patient_id: UUID
    encounter_id: UUID
    payer_id: str = Field(..., min_length=1, max_length=100)
    total_amount: Decimal = Field(..., ge=0)
    patient_responsibility: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0)

    # validators applied before pydantic parsing to ensure correct Decimal
    @field_validator("total_amount", "patient_responsibility", mode="before")
    def _validate_money_fields(cls, v):
        return _enforce_decimal_value(v)


class ClaimCreate(ClaimBase):
    diagnosis_codes: Optional[List[Dict[str, Any]]] = None
    procedure_codes: Optional[List[Dict[str, Any]]] = None


class ClaimUpdate(BaseModel):
    payer_id: Optional[str] = Field(None, min_length=1, max_length=100)
    total_amount: Optional[Decimal] = Field(None, ge=0)
    patient_responsibility: Optional[Decimal] = Field(None, ge=0)
    diagnosis_codes: Optional[List[Dict[str, Any]]] = None
    procedure_codes: Optional[List[Dict[str, Any]]] = None
    status: Optional[Literal["draft", "submitted", "processing", "paid", "denied"]] = (
        None
    )

    @field_validator("total_amount", "patient_responsibility", mode="before")
    def _validate_optional_money(cls, v):
        # allow None through
        if v is None:
            return v
        return _enforce_decimal_value(v)


class ClaimResponse(ClaimBase):
    id: UUID
    claim_number: Optional[str] = None
    status: str
    diagnosis_codes: Optional[List[Dict[str, Any]]] = None
    procedure_codes: Optional[List[Dict[str, Any]]] = None
    payer_rules_applied: Optional[Dict[str, Any]] = None
    submitted_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Pydantic v2 config style
    model_config = {"from_attributes": True}


class ClaimSubmissionRequest(BaseModel):
    claim_id: UUID
    submit_to_payer: bool = True


class ClaimSubmissionResponse(BaseModel):
    claim_id: UUID
    submission_status: str
    reference_number: Optional[str] = None
    estimated_processing_days: Optional[int] = None
    message: str


class EligibilityCheckRequest(BaseModel):
    patient_id: UUID
    payer_id: str
    service_date: date


class EligibilityCheckResponse(BaseModel):
    patient_id: UUID
    eligible: bool
    coverage_details: Dict[str, Any]
    confidence_score: float
    message: str
