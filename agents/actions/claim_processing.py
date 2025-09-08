"""
Claim processing agent for preparing and submitting claims - Fixed Sync Version
"""

from langchain.schema.messages import SystemMessage, AIMessage
from agents.utils.initializer import get_llm
from agents.utils.models import (
    RCMAgentState,
    ClaimData,
    ClaimProcessingDecision,
    DecisionAction,
    WorkflowStep,
)
from agents.utils.prompts import claim_processing_prompt
from services.mock_payer_service import mock_payer_service
import json
import random
import string

llm = get_llm()


def process_claim_submission(state: RCMAgentState) -> RCMAgentState:
    """Process and prepare claim for submission - SYNC VERSION."""
    if (
        state["exit_requested"]
        or state["workflow_step"] != WorkflowStep.CLAIM_PROCESSING
    ):
        return state

    try:
        print(f"🔄 Starting claim processing step")

        # Get all required data
        patient_data = state.get("patient_data")
        encounter_data = state.get("encounter_data")
        suggested_codes = state.get("suggested_codes")
        eligibility_result = state.get("eligibility_result")

        # Validate we have all necessary components
        missing_components = []
        if not patient_data:
            missing_components.append("patient data")
        if not encounter_data:
            missing_components.append("encounter data")
        if not suggested_codes:
            missing_components.append("medical codes")
        if not eligibility_result or not eligibility_result.eligible:
            missing_components.append("valid eligibility")

        if missing_components:
            state["error_message"] = (
                f"Cannot process claim. Missing: {', '.join(missing_components)}"
            )
            state["status"] = "error"
            return state

        # Calculate claim amounts
        total_amount = calculate_claim_amount(suggested_codes)
        patient_responsibility = calculate_patient_responsibility(
            total_amount, eligibility_result
        )

        # Prepare claim data
        claim_number = generate_claim_number()
        payer_id = map_insurance_provider_to_id(patient_data.insurance_provider)

        # Prepare diagnosis and procedure codes for claim
        diagnosis_codes = [
            {
                "code": code.code,
                "description": code.description,
                "confidence": code.confidence,
            }
            for code in suggested_codes.icd10_codes
        ]

        procedure_codes = [
            {
                "code": code.code,
                "description": code.description,
                "confidence": code.confidence,
                "modifier": getattr(code, "modifier", None),
            }
            for code in suggested_codes.cpt_codes
        ]

        # Create claim data object
        claim_data = ClaimData(
            claim_number=claim_number,
            total_amount=total_amount,
            patient_responsibility=patient_responsibility,
            payer_id=payer_id,
            diagnosis_codes=diagnosis_codes,
            procedure_codes=procedure_codes,
            status="ready_for_submission",
            submission_ready=True,
        )

        state["claim_data"] = claim_data
        state["confidence_scores"]["claim_processing"] = 0.9

        # Mock submit claim to payer (synchronous)
        submission_result = submit_claim_to_payer_sync(claim_data, state)

        if submission_result["success"]:
            state["workflow_step"] = WorkflowStep.COMPLETED
            state["status"] = "completed"
            state["done"] = True
            state["result"] = (
                f"Claim {claim_number} submitted successfully. Reference: {submission_result['reference_number']}"
            )

            # Add completion message
            state["messages"].append(
                AIMessage(
                    content=f"✅ Claim {claim_number} has been successfully submitted to {payer_id}. Total amount: ${total_amount:.2f}, Patient responsibility: ${patient_responsibility:.2f}"
                )
            )

            print(f"✅ Claim processing completed successfully - Claim: {claim_number}")
        else:
            state["error_message"] = (
                f"Claim submission failed: {submission_result['error']}"
            )
            state["status"] = "error"

        return state

    except Exception as e:
        error_msg = f"Claim processing error: {str(e)}"
        print(f"❌ {error_msg}")
        state["error_message"] = error_msg
        state["status"] = "error"
        return state


def calculate_claim_amount(suggested_codes) -> float:
    """Calculate total claim amount based on procedure codes."""
    total = 0.0
    for code in suggested_codes.cpt_codes:
        if code.code.startswith("99"):  # E&M codes
            total += random.uniform(100, 500)
        elif code.code.startswith("93"):  # Cardiology
            total += random.uniform(200, 1000)
        elif code.code.startswith("80"):  # Lab tests
            total += random.uniform(50, 200)
        else:
            total += random.uniform(75, 300)
    return round(total, 2)


def calculate_patient_responsibility(total_amount: float, eligibility_result) -> float:
    """Calculate patient responsibility based on eligibility."""
    if not eligibility_result or not eligibility_result.coverage_details:
        return total_amount

    coverage_details = eligibility_result.coverage_details
    copay = eligibility_result.copay_amount or coverage_details.get("copay_amount", 0)
    deductible_remaining = (
        eligibility_result.deductible_remaining
        or coverage_details.get("deductible_remaining", 0)
    )
    deductible_applied = min(total_amount, deductible_remaining)
    remaining_after_deductible = total_amount - deductible_applied
    coverage_percentage = coverage_details.get("coverage_percentage", 80) / 100
    coinsurance_amount = remaining_after_deductible * (1 - coverage_percentage)
    patient_responsibility = copay + deductible_applied + coinsurance_amount
    return round(min(patient_responsibility, total_amount), 2)


def generate_claim_number() -> str:
    """Generate a unique claim number."""
    return "CLM" + "".join(random.choices(string.digits, k=8))


def map_insurance_provider_to_id(provider_name: str) -> str:
    """Map insurance provider name to payer ID."""
    provider_mapping = {
        "daman": "DAMAN",
        "adnic": "ADNIC",
        "thiqa": "THIQA",
        "bupa": "BUPA",
        "abu dhabi national insurance": "ADNIC",
        "daman national health": "DAMAN",
        "thiqa insurance": "THIQA",
    }
    provider_lower = provider_name.lower()
    for key, value in provider_mapping.items():
        if key in provider_lower:
            return value
    return "DAMAN"  # Default for testing


def submit_claim_to_payer_sync(claim_data: ClaimData, state: RCMAgentState) -> dict:
    """Submit claim to payer via mock service - SYNCHRONOUS VERSION."""
    try:
        # Mock successful submission (no async calls)
        reference_number = "REF" + "".join(random.choices(string.digits, k=10))
        tracking_number = "TRK" + "".join(random.choices(string.digits, k=8))

        return {
            "success": True,
            "reference_number": reference_number,
            "tracking_number": tracking_number,
            "estimated_processing_days": random.randint(3, 7),
            "status": "submitted",
            "submission_timestamp": "2024-01-20T10:30:00Z",
        }

    except Exception as e:
        return {"success": False, "error": f"Submission error: {str(e)}"}
