"""
Conditional logic for RCM workflow routing - API Compatible
"""

from agents.utils.models import RCMAgentState, WorkflowStep


def should_continue_processing(state: RCMAgentState) -> bool:
    """
    Determine if the workflow should continue processing automatically
    """
    # Don't continue if user input is needed
    if state.get("need_user_input"):
        return False

    # Don't continue if done or error
    if state.get("done") or state.get("exit_requested") or state.get("error_message"):
        return False

    # Don't continue if in reviewing status (needs human approval)
    if state.get("status") == "reviewing":
        return False

    return True


def get_next_workflow_step(state: RCMAgentState) -> WorkflowStep:
    """
    Determine the next workflow step based on current state
    """
    current_step = state.get("workflow_step", WorkflowStep.INITIALIZATION)
    status = state.get("status", "collecting")

    # If we need user input, stay in data collection
    if state.get("need_user_input"):
        return WorkflowStep.DATA_COLLECTION

    # If there's an error, don't advance
    if state.get("error_message"):
        return current_step

    # Normal workflow progression
    if current_step == WorkflowStep.INITIALIZATION:
        return WorkflowStep.DATA_COLLECTION

    elif current_step == WorkflowStep.DATA_COLLECTION:
        if state.get("ready_for_processing"):
            return WorkflowStep.DATA_STRUCTURING
        return WorkflowStep.DATA_COLLECTION

    elif current_step == WorkflowStep.DATA_STRUCTURING:
        if state.get("structured_data") and status == "processing":
            return WorkflowStep.MEDICAL_CODING
        return current_step

    elif current_step == WorkflowStep.MEDICAL_CODING:
        if state.get("suggested_codes") and status == "processing":
            return WorkflowStep.ELIGIBILITY_CHECKING
        return current_step

    elif current_step == WorkflowStep.ELIGIBILITY_CHECKING:
        if state.get("eligibility_result") and status == "processing":
            return WorkflowStep.CLAIM_PROCESSING
        return current_step

    elif current_step == WorkflowStep.CLAIM_PROCESSING:
        if state.get("claim_data") or state.get("done"):
            return WorkflowStep.COMPLETED
        return current_step

    else:  # COMPLETED or unknown
        return WorkflowStep.COMPLETED


def needs_human_review(state: RCMAgentState) -> bool:
    """
    Determine if the current state requires human review
    """
    # Check confidence scores
    confidence_scores = state.get("confidence_scores", {})

    for step, score in confidence_scores.items():
        if score < 0.7:  # Low confidence threshold
            return True

    # Check if explicitly marked for review
    if state.get("status") == "reviewing":
        return True

    # Check for specific conditions requiring review
    if state.get("eligibility_result") and not state["eligibility_result"].eligible:
        return True

    return False


def can_auto_proceed(state: RCMAgentState) -> bool:
    """
    Determine if workflow can proceed automatically without user intervention
    """
    # Can't proceed if user input needed
    if state.get("need_user_input"):
        return False

    # Can't proceed if requires human review
    if needs_human_review(state):
        return False

    # Can't proceed if in error state
    if state.get("error_message"):
        return False

    # Check confidence scores for auto-approval
    confidence_scores = state.get("confidence_scores", {})
    if confidence_scores:
        avg_confidence = sum(confidence_scores.values()) / len(confidence_scores)
        return avg_confidence >= 0.8  # High confidence threshold for auto-proceed

    return True


# Legacy functions for backward compatibility (kept but simplified)
def decide_after_user_input(state: RCMAgentState) -> str:
    """Legacy: Decide what to do after processing user input."""
    if state["exit_requested"]:
        return "end"
    elif state["ready_for_processing"]:
        return "data_structuring"
    else:
        return "user_agent_decision"


def decide_after_user_agent_decision(state: RCMAgentState) -> str:
    """Legacy: Decide what to do after user agent decision."""
    if state["exit_requested"] or state["done"]:
        return "end"
    elif state["need_user_input"]:
        return "user_input"
    elif state["ready_for_processing"]:
        return "data_structuring"
    else:
        return "user_input"


def decide_after_data_structuring(state: RCMAgentState) -> str:
    """Legacy: Decide what to do after data structuring."""
    if state["exit_requested"] or state["done"]:
        return "end"
    elif state["status"] == "error":
        return "end"
    elif state["need_user_input"]:
        return "user_input"
    elif state["workflow_step"] == WorkflowStep.MEDICAL_CODING:
        return "medical_coding"
    else:
        return "user_input"


def decide_after_coding(state: RCMAgentState) -> str:
    """Legacy: Decide what to do after medical coding."""
    if state["exit_requested"] or state["done"]:
        return "end"
    elif state["status"] == "error":
        return "end"
    elif state["need_user_input"]:
        return "user_input"
    elif state["workflow_step"] == WorkflowStep.ELIGIBILITY_CHECKING:
        return "eligibility_checking"
    else:
        return "user_input"


def decide_after_eligibility(state: RCMAgentState) -> str:
    """Legacy: Decide what to do after eligibility checking."""
    if state["exit_requested"] or state["done"]:
        return "end"
    elif state["status"] == "error":
        return "end"
    elif state["need_user_input"]:
        return "user_input"
    elif state["workflow_step"] == WorkflowStep.CLAIM_PROCESSING:
        return "claim_processing"
    else:
        return "user_input"


def decide_after_claim_processing(state: RCMAgentState) -> str:
    """Legacy: Decide what to do after claim processing."""
    if state["exit_requested"] or state["done"]:
        return "end"
    elif state["status"] == "error":
        return "end"
    elif state["need_user_input"]:
        return "user_input"
    else:
        return "end"


def should_continue(state: RCMAgentState) -> str:
    """Legacy: Final conditional to continue or end."""
    if state["exit_requested"] or state["done"]:
        return "end"
    else:
        return "user_input"
