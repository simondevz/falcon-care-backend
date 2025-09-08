"""
Medical coding agent for ICD-10 and CPT code suggestions - API Compatible
"""

from langchain.schema.messages import SystemMessage, AIMessage
from agents.utils.initializer import get_llm
from agents.utils.models import (
    MedicalCode,
    RCMAgentState,
    SuggestedCodes,
    CodingDecision,
    DecisionAction,
    WorkflowStep,
)
from agents.utils.prompts import medical_coding_prompt
import json
from rich.console import Console
import traceback

console = Console()

llm = get_llm()


def suggest_medical_codes(state: RCMAgentState) -> RCMAgentState:
    """Suggest appropriate ICD-10 and CPT codes based on structured clinical data."""
    if state["exit_requested"] or state["workflow_step"] != WorkflowStep.MEDICAL_CODING:
        return state

    try:
        print(f"🔄 Starting medical coding step")

        # Get structured clinical data
        structured_data = state.get("structured_data")
        patient_data = state.get("patient_data")

        if not structured_data:
            state["error_message"] = "No structured clinical data available for coding"
            state["status"] = "error"
            return state

        # Prepare coding context
        payer_info = {}
        if patient_data and patient_data.insurance_provider:
            payer_info = {
                "payer_name": patient_data.insurance_provider,
                "policy_number": patient_data.policy_number,
            }

        # Create coding prompt
        coding_prompt = f"""
You are a medical coding expert specializing in ICD-10 and CPT coding. Based on the structured clinical data, suggest appropriate medical codes.

Structured Clinical Data: {json.dumps(structured_data.model_dump(), default=str)}
Payer Information: {json.dumps(payer_info, default=str)}

Suggest appropriate codes and return ONLY a JSON object:
{{
    "icd10_codes": [
        {{
            "code": "ICD-10 code",
            "description": "code description", 
            "confidence": 0.9,
            "rationale": "reason for selection"
        }}
    ],
    "cpt_codes": [
        {{
            "code": "CPT code",
            "description": "procedure description",
            "confidence": 0.9,
            "rationale": "reason for selection",
            "modifier": "modifier if applicable or null"
        }}
    ],
    "overall_confidence": 0.9,
    "requires_human_review": false
}}

Return only the JSON, no other text.
"""

        response = llm.invoke([SystemMessage(content=coding_prompt)])

        # Parse the JSON response
        import re

        json_match = re.search(r"\{.*\}", response.content, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            codes_data = json.loads(json_str)

            # Create MedicalCode objects
            icd10_codes = []
            for code_info in codes_data.get("icd10_codes", []):
                icd10_codes.append(
                    MedicalCode(
                        code=code_info["code"],
                        description=code_info["description"],
                        confidence=code_info["confidence"],
                        rationale=code_info["rationale"],
                    )
                )

            cpt_codes = []
            for code_info in codes_data.get("cpt_codes", []):
                cpt_codes.append(
                    MedicalCode(
                        code=code_info["code"],
                        description=code_info["description"],
                        confidence=code_info["confidence"],
                        rationale=code_info["rationale"],
                        modifier=code_info.get("modifier"),
                    )
                )

            # Create SuggestedCodes object
            suggested_codes = SuggestedCodes(
                icd10_codes=icd10_codes,
                cpt_codes=cpt_codes,
                overall_confidence=codes_data.get("overall_confidence", 0.8),
                requires_human_review=codes_data.get("requires_human_review", False),
            )

            state["suggested_codes"] = suggested_codes

            # Calculate overall confidence
            all_codes = icd10_codes + cpt_codes
            if all_codes:
                avg_confidence = sum(code.confidence for code in all_codes) / len(
                    all_codes
                )
                state["confidence_scores"]["medical_coding"] = avg_confidence

                # Check if requires human approval
                if suggested_codes.requires_human_review or avg_confidence < 0.8:
                    state["question_to_ask"] = (
                        f"Medical codes suggested with {avg_confidence:.2f} confidence. Do you approve these codes?"
                    )
                    state["need_user_input"] = True
                    state["status"] = "reviewing"
                else:
                    # Auto-approve high confidence codes
                    state["workflow_step"] = WorkflowStep.ELIGIBILITY_CHECKING
                    state["status"] = "processing"
                    state["messages"].append(
                        AIMessage(
                            content="Medical codes approved. Now checking patient eligibility..."
                        )
                    )
                    print(
                        f"✅ Medical coding completed with confidence: {avg_confidence}"
                    )
            else:
                state["question_to_ask"] = (
                    "No medical codes could be suggested. Please provide more specific clinical information."
                )
                state["need_user_input"] = True
                state["status"] = "collecting"
                state["workflow_step"] = WorkflowStep.DATA_COLLECTION
        else:
            raise ValueError("No valid JSON in response")

        return state

    except Exception as e:
        state["error_message"] = f"Medical coding error: {str(e)}"
        state["status"] = "error"
        print(f"❌ Medical coding error: {str(e)}")
        return state
