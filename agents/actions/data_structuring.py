"""
Data structuring agent for clinical notes processing - API Compatible
"""

from langchain.schema.messages import SystemMessage, AIMessage
from agents.utils.initializer import get_llm
from agents.utils.models import (
    RCMAgentState,
    StructuredClinicalData,
    DataStructuringDecision,
    DecisionAction,
    WorkflowStep,
)
from agents.utils.prompts import data_structuring_prompt
import json
import traceback

llm = get_llm()


def structure_clinical_data(state: RCMAgentState) -> RCMAgentState:
    """Structure clinical data from raw notes and encounter information."""
    if state["exit_requested"] or not state["ready_for_processing"]:
        return state

    try:
        # Get raw clinical notes and context
        encounter_data = state.get("encounter_data")
        patient_data = state.get("patient_data")

        if not encounter_data or not encounter_data.raw_clinical_notes:
            state["question_to_ask"] = (
                "I need clinical notes to process. Please provide the clinical documentation for this encounter."
            )
            state["need_user_input"] = True
            state["status"] = "collecting"
            state["workflow_step"] = WorkflowStep.DATA_COLLECTION
            return state

        # Prepare context for structuring
        raw_notes = encounter_data.raw_clinical_notes
        patient_context = patient_data.model_dump() if patient_data else {}
        encounter_context = encounter_data.model_dump() if encounter_data else {}

        # Create structured LLM
        structuring_llm = llm.with_structured_output(DataStructuringDecision)

        # Format the prompt
        prompt_content = data_structuring_prompt.format(
            raw_notes=raw_notes,
            patient_context=json.dumps(patient_context, default=str),
            encounter_context=json.dumps(encounter_context, default=str),
        )

        decision = structuring_llm.invoke(
            [SystemMessage(content=prompt_content)] + state["messages"]
        )

        state["messages"].append(AIMessage(content=decision.message))

        if decision.action == DecisionAction.PROCEED and decision.structured_data:
            state["structured_data"] = decision.structured_data
            state["confidence_scores"]["data_structuring"] = (
                decision.confidence_score or 0.0
            )
            state["workflow_step"] = WorkflowStep.MEDICAL_CODING
            state["status"] = "processing"

            # Check confidence level
            if decision.confidence_score and decision.confidence_score < 0.7:
                state["question_to_ask"] = (
                    f"The clinical data extraction had low confidence ({decision.confidence_score:.2f}). Please review and confirm the extracted information is accurate."
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
        error_msg = f"Data structuring error: {str(e)}"
        state["error_message"] = error_msg
        state["status"] = "error"
        return state
