"""
Eligibility checking agent for insurance verification - API Compatible
"""

from langchain.schema.messages import SystemMessage, AIMessage
from agents.utils.initializer import get_llm
from agents.utils.models import (
    RCMAgentState,
    EligibilityResult,
    EligibilityDecision,
    DecisionAction,
    WorkflowStep,
)
from agents.utils.prompts import eligibility_verification_prompt
from services.mock_payer_service import mock_payer_service
import json
from datetime import datetime

llm = get_llm()


def check_patient_eligibility(state: RCMAgentState) -> RCMAgentState:
    """Check patient eligibility and coverage details."""
    if (
        state["exit_requested"]
        or state["workflow_step"] != WorkflowStep.ELIGIBILITY_CHECKING
    ):
        return state

    try:
        # Get required data
        patient_data = state.get("patient_data")
        encounter_data = state.get("encounter_data")
        suggested_codes = state.get("suggested_codes")

        if not patient_data or not patient_data.insurance_provider:
            state["question_to_ask"] = (
                "I need patient insurance information to check eligibility. Please provide the insurance provider and policy details."
            )
            state["need_user_input"] = True
            state["status"] = "collecting"
            state["workflow_step"] = WorkflowStep.DATA_COLLECTION
            return state

        # Prepare eligibility check data
        payer_id = map_insurance_provider_to_id(patient_data.insurance_provider)
        service_date = (
            encounter_data.service_date
            if encounter_data and encounter_data.service_date
            else datetime.now().date()
        )

        # Proposed services from codes
        proposed_services = []
        if suggested_codes:
            proposed_services.extend([code.code for code in suggested_codes.cpt_codes])
            proposed_services.extend(
                [code.code for code in suggested_codes.icd10_codes]
            )

        # Call mock payer service for eligibility check (this would be async in real implementation)
        try:
            # Note: In real implementation, this would be await mock_payer_service.check_eligibility()
            # For now, we'll simulate the response
            eligibility_response = {
                "patient_id": (
                    str(patient_data.patient_id)
                    if patient_data.patient_id
                    else "unknown"
                ),
                "payer_id": payer_id,
                "eligible": True,
                "coverage_details": {
                    "deductible_remaining": 500.0,
                    "copay_amount": 25.0,
                    "coverage_percentage": 80,
                    "requires_prior_auth": False,
                    "max_benefit": 100000.0,
                    "policy_status": "active",
                },
                "confidence_score": 0.95,
            }
        except Exception as api_error:
            # Fallback to mock data if API fails
            eligibility_response = {
                "eligible": True,
                "coverage_details": {"copay_amount": 25.0, "coverage_percentage": 80},
                "confidence_score": 0.8,
            }

        # Create eligibility LLM for processing response
        eligibility_llm = llm.with_structured_output(EligibilityDecision)

        # Format the prompt
        prompt_content = eligibility_verification_prompt.format(
            patient_data=json.dumps(patient_data.model_dump(), default=str),
            insurance_info=json.dumps(
                {
                    "provider": patient_data.insurance_provider,
                    "policy_number": patient_data.policy_number,
                    "payer_id": payer_id,
                }
            ),
            service_date=str(service_date),
            proposed_services=json.dumps(proposed_services),
        )

        # Add eligibility response context
        prompt_content += (
            f"\n\nPayer Response: {json.dumps(eligibility_response, default=str)}"
        )

        decision = eligibility_llm.invoke(
            [SystemMessage(content=prompt_content)] + state["messages"]
        )

        state["messages"].append(AIMessage(content=decision.message))

        if decision.action == DecisionAction.PROCEED and decision.eligibility_result:
            state["eligibility_result"] = decision.eligibility_result
            state["confidence_scores"]["eligibility_check"] = (
                decision.eligibility_result.confidence_score or 0.0
            )

            # Check if patient is eligible
            if decision.eligibility_result.eligible:
                state["workflow_step"] = WorkflowStep.CLAIM_PROCESSING
                state["status"] = "processing"

                # Check for prior auth requirements
                if decision.eligibility_result.requires_prior_auth:
                    state["question_to_ask"] = (
                        "Prior authorization is required for this service. Would you like me to initiate the prior auth process?"
                    )
                    state["need_user_input"] = True
                    state["status"] = "reviewing"
            else:
                state["question_to_ask"] = (
                    f"Patient is not eligible for coverage. Reason: {decision.message}. Would you like to proceed with self-pay or check alternative coverage?"
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
        state["error_message"] = f"Eligibility checking error: {str(e)}"
        state["status"] = "error"
        return state


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

    # Default fallback
    return "UNKNOWN"
