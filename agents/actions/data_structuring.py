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
    if state["exit_requested"]:
        return state

    try:
        print(f"🔄 Starting data structuring step")

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

        # Use simple JSON extraction instead of structured output
        structuring_prompt = f"""
You are a medical data extraction expert. Extract and structure clinical information from the provided notes.

Patient Context: {json.dumps(patient_context, default=str)}
Encounter Context: {json.dumps(encounter_context, default=str)}
Raw Clinical Notes: {raw_notes}

Extract the following information and return ONLY a JSON object:
{{
    "patient_info": {{
        "name": "patient name",
        "age": "calculated age or null",
        "gender": "gender"
    }},
    "encounter_details": {{
        "type": "encounter type",
        "date": "service date",
        "location": "location or null"
    }},
    "diagnoses": ["list of suspected diagnoses"],
    "procedures": ["list of procedures performed"],
    "medications": ["list of medications"],
    "vital_signs": {{
        "blood_pressure": "BP reading",
        "heart_rate": "HR",
        "respiratory_rate": "RR",
        "temperature": "temp",
        "oxygen_saturation": "O2 sat"
    }},
    "assessment_and_plan": {{
        "assessment": "clinical assessment",
        "plan": "treatment plan"
    }},
    "confidence_score": 0.9
}}

Return only the JSON, no other text.
"""

        response = llm.invoke([SystemMessage(content=structuring_prompt)])

        # Parse the JSON response
        import re

        json_match = re.search(r"\{.*\}", response.content, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            structured_data_dict = json.loads(json_str)

            # Create StructuredClinicalData object
            structured_data = StructuredClinicalData(
                patient_info=structured_data_dict.get("patient_info"),
                encounter_details=structured_data_dict.get("encounter_details"),
                diagnoses=structured_data_dict.get("diagnoses", []),
                procedures=structured_data_dict.get("procedures", []),
                medications=structured_data_dict.get("medications", []),
                vital_signs=structured_data_dict.get("vital_signs"),
                assessment_and_plan=structured_data_dict.get("assessment_and_plan"),
                confidence_score=structured_data_dict.get("confidence_score", 0.8),
            )

            state["structured_data"] = structured_data
            state["confidence_scores"]["data_structuring"] = (
                structured_data.confidence_score or 0.8
            )
            state["workflow_step"] = WorkflowStep.MEDICAL_CODING
            state["status"] = "processing"

            print(
                f"✅ Data structuring completed with confidence: {structured_data.confidence_score}"
            )

            # Add AI message about completion
            state["messages"].append(
                AIMessage(
                    content="Clinical data has been structured successfully. Now suggesting appropriate medical codes..."
                )
            )

        else:
            raise ValueError("No valid JSON in response")

        return state

    except Exception as e:
        error_msg = f"Data structuring error: {str(e)}"
        print(f"❌ {error_msg}")
        state["error_message"] = error_msg
        state["status"] = "error"
        return state
