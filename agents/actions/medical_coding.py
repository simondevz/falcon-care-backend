"""
Medical coding agent for ICD-10 and CPT code suggestions - API Compatible
"""

from langchain.schema.messages import SystemMessage, AIMessage
from agents.utils.initializer import get_llm
from agents.utils.models import (
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

        # Create coding LLM
        coding_llm = llm.with_structured_output(CodingDecision)

        # Format the prompt
        prompt_content = medical_coding_prompt.format(
            structured_data=json.dumps(structured_data.model_dump(), default=str),
            payer_info=json.dumps(payer_info, default=str),
        )

        decision = coding_llm.invoke(
            [SystemMessage(content=prompt_content)] + state["messages"]
        )

        state["messages"].append(AIMessage(content=decision.message))

        if decision.action == DecisionAction.PROCEED and decision.suggested_codes:
            state["suggested_codes"] = decision.suggested_codes

            # Calculate overall confidence from individual code confidences
            all_codes = (
                decision.suggested_codes.icd10_codes
                + decision.suggested_codes.cpt_codes
            )
            if all_codes:
                avg_confidence = sum(code.confidence for code in all_codes) / len(
                    all_codes
                )
                state["confidence_scores"]["medical_coding"] = avg_confidence

                # Check if requires human approval
                if decision.requires_approval or avg_confidence < 0.8:
                    state["question_to_ask"] = (
                        f"Please review the suggested medical codes. Average confidence: {avg_confidence:.2f}. Do you approve these codes?"
                    )
                    state["need_user_input"] = True
                    state["status"] = "reviewing"
                else:
                    # Auto-approve high confidence codes
                    state["workflow_step"] = WorkflowStep.ELIGIBILITY_CHECKING
                    state["status"] = "processing"
            else:
                state["question_to_ask"] = (
                    "No medical codes could be suggested. Please provide more specific clinical information."
                )
                state["need_user_input"] = True
                state["status"] = "collecting"
                state["workflow_step"] = WorkflowStep.DATA_COLLECTION

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
        state["error_message"] = f"Medical coding error: {str(e)}"
        state["status"] = "error"
        return state
        return state

    except Exception as e:
        console.print(f"[bold red]❌ Error in medical coding: {e}[/bold red]")
        console.print("[bold red]>>> Exception details:[/bold red]")
        console.print(f"[red]Exception type: {type(e)}[/red]")
        console.print(f"[red]Exception message: {str(e)}[/red]")
        console.print("[red]Stack trace:[/red]")
        traceback.print_exc()
        console.print("[bold red]>>> End of exception details[/bold red]")

        state["error_message"] = f"Medical coding error: {str(e)}"
        state["status"] = "error"
        return state
