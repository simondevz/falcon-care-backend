"""
Claim processing agent for preparing and submitting claims - API Compatible
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


async def process_claim_submission(state: RCMAgentState) -> RCMAgentState:
    """Process and prepare claim for submission."""
    if (
        state["exit_requested"]
        or state["workflow_step"] != WorkflowStep.CLAIM_PROCESSING
    ):
        return state

    try:
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

        # Create claim processing LLM
        claim_llm = llm.with_structured_output(ClaimProcessingDecision)

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
                "modifier": code.modifier,
            }
            for code in suggested_codes.cpt_codes
        ]

        # Format the prompt
        prompt_content = claim_processing_prompt.format(
            patient_data=json.dumps(patient_data.model_dump(), default=str),
            encounter_data=json.dumps(encounter_data.model_dump(), default=str),
            diagnosis_codes=json.dumps(diagnosis_codes),
            procedure_codes=json.dumps(procedure_codes),
            eligibility_results=json.dumps(
                eligibility_result.model_dump(), default=str
            ),
        )

        decision = claim_llm.invoke(
            [SystemMessage(content=prompt_content)] + state["messages"]
        )

        state["messages"].append(AIMessage(content=decision.message))

        if decision.action == DecisionAction.PROCEED:
            # Create claim data object
            claim_data = ClaimData(
                claim_number=claim_number,
                total_amount=total_amount,
                patient_responsibility=patient_responsibility,
                payer_id=payer_id,
                diagnosis_codes=diagnosis_codes,
                procedure_codes=procedure_codes,
                status="ready_for_submission",
                submission_ready=decision.ready_for_submission,
            )

            state["claim_data"] = claim_data
            state["confidence_scores"][
                "claim_processing"
            ] = 0.9  # High confidence for successful processing

            if decision.ready_for_submission:
                # Attempt to submit claim (async)
                submission_result = await submit_claim_to_payer(claim_data, state)

                if submission_result["success"]:
                    state["workflow_step"] = WorkflowStep.COMPLETED
                    state["status"] = "completed"
                    state["done"] = True
                    state["result"] = (
                        f"Claim {claim_number} submitted successfully. Reference: {submission_result['reference_number']}"
                    )
                else:
                    state["error_message"] = (
                        f"Claim submission failed: {submission_result['error']}"
                    )
                    state["status"] = "error"
            else:
                state["question_to_ask"] = (
                    f"Claim {claim_number} is prepared but requires review before submission. Would you like to review the claim details?"
                )
                state["need_user_input"] = True
                state["status"] = "reviewing"

        elif decision.action == DecisionAction.ASK_USER:
            state["question_to_ask"] = decision.message
            state["need_user_input"] = True
            state["status"] = "collecting"
            state["workflow_step"] = WorkflowStep.DATA_COLLECTION
        elif decision.action == DecisionAction.ERROR:
            state["error_message"] = decision.message
            state["status"] = "error"

        return state

    except Exception as e:
        state["error_message"] = f"Claim processing error: {str(e)}"
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
    return "UNKNOWN"


async def submit_claim_to_payer(claim_data: ClaimData, state: RCMAgentState) -> dict:
    """Submit claim to payer via mock service."""
    try:
        submission_data = {
            "claim_id": claim_data.claim_number,
            "payer_id": claim_data.payer_id,
            "total_amount": claim_data.total_amount,
            "patient_responsibility": claim_data.patient_responsibility,
            "diagnosis_codes": claim_data.diagnosis_codes,
            "procedure_codes": claim_data.procedure_codes,
            "patient_data": (
                state.get("patient_data").model_dump()
                if state.get("patient_data")
                else {}
            ),
            "encounter_data": (
                state.get("encounter_data").model_dump()
                if state.get("encounter_data")
                else {}
            ),
        }

        result = await mock_payer_service.submit_claim(submission_data)

        if result.get("status") == "submitted":
            return {
                "success": True,
                "reference_number": result.get("reference_number"),
                "tracking_number": result.get("tracking_number"),
                "estimated_processing_days": result.get("estimated_processing_days"),
            }
        else:
            return {
                "success": False,
                "error": result.get("rejection_reason", "Unknown submission error"),
            }

    except Exception as e:
        return {"success": False, "error": f"Submission error: {str(e)}"}
