"""
RCM Agent implementation with LangGraph-style workflow execution
"""

from typing import Dict, Any, Optional
from langchain.schema.messages import HumanMessage, AIMessage, SystemMessage
from agents.utils.models import (
    RCMAgentState,
    WorkflowStep,
    PatientData,
    EncounterData,
)
from agents.actions.user_interaction import (
    initialize_rcm_state,
    process_user_input,
    generate_user_agent_decision,
)
from agents.actions.data_structuring import structure_clinical_data
from agents.actions.medical_coding import suggest_medical_codes
from agents.actions.eligibility_checking import check_patient_eligibility
from agents.actions.claim_processing import process_claim_submission
from agents.utils.conditionals import (
    should_continue_processing,
    get_next_workflow_step,
)
import asyncio


class RCMAgentExecutor:
    """Executor for RCM workflow steps"""

    def __init__(self):
        self.workflow_functions = {
            WorkflowStep.INITIALIZATION: self._initialize_workflow,
            WorkflowStep.DATA_COLLECTION: self._process_data_collection,
            WorkflowStep.DATA_STRUCTURING: self._structure_data,
            WorkflowStep.MEDICAL_CODING: self._process_medical_coding,
            WorkflowStep.ELIGIBILITY_CHECKING: self._check_eligibility,
            WorkflowStep.CLAIM_PROCESSING: self._process_claim,
            WorkflowStep.COMPLETED: self._handle_completion,
        }

    def execute_step(
        self, state: RCMAgentState, user_input: Optional[str] = None
    ) -> RCMAgentState:
        """Execute a single workflow step"""
        try:
            # Add user input if provided
            if user_input and user_input.strip():
                state["messages"].append(HumanMessage(content=user_input))
                state["need_user_input"] = False

            # Get current workflow step
            current_step = state.get("workflow_step", WorkflowStep.INITIALIZATION)

            # Execute the appropriate workflow function
            if current_step in self.workflow_functions:
                state = self.workflow_functions[current_step](state)
            else:
                state["error_message"] = f"Unknown workflow step: {current_step}"
                state["status"] = "error"

            # Continue processing if no user input needed and not done
            max_iterations = 5
            iterations = 0

            while (
                not state.get("need_user_input")
                and not state.get("done")
                and not state.get("error_message")
                and iterations < max_iterations
            ):
                iterations += 1
                next_step = get_next_workflow_step(state)

                if next_step != state.get("workflow_step"):
                    state["workflow_step"] = next_step
                    print(f"🔄 Moving to next step: {next_step}")

                    # Execute the next step
                    if next_step in self.workflow_functions:
                        state = self.workflow_functions[next_step](state)
                    else:
                        break
                else:
                    break

            return state

        except Exception as e:
            state["error_message"] = f"Execution error: {str(e)}"
            state["status"] = "error"
            return state

    def _initialize_workflow(self, state: RCMAgentState) -> RCMAgentState:
        """Initialize the workflow"""
        return initialize_rcm_state(state)

    def _process_data_collection(self, state: RCMAgentState) -> RCMAgentState:
        """Handle data collection phase"""
        # Process user input if needed
        if state.get("need_user_input") and state["messages"]:
            state = process_user_input(state)

        # Generate user agent decision
        if not state.get("need_user_input") and not state.get("exit_requested"):
            state = generate_user_agent_decision(state)

        return state

    def _structure_data(self, state: RCMAgentState) -> RCMAgentState:
        """Handle data structuring phase"""
        return structure_clinical_data(state)

    def _process_medical_coding(self, state: RCMAgentState) -> RCMAgentState:
        """Handle medical coding phase"""
        return suggest_medical_codes(state)

    def _check_eligibility(self, state: RCMAgentState) -> RCMAgentState:
        """Handle eligibility checking phase"""
        return check_patient_eligibility(state)

    def _process_claim(self, state: RCMAgentState) -> RCMAgentState:
        """Handle claim processing phase"""
        # Note: This needs to be async in real implementation
        try:
            # For now, we'll run the async function in a sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(process_claim_submission(state))
            loop.close()
            return result
        except Exception as e:
            state["error_message"] = f"Claim processing error: {str(e)}"
            state["status"] = "error"
            return state

    def _handle_completion(self, state: RCMAgentState) -> RCMAgentState:
        """Handle workflow completion"""
        if not state.get("result"):
            state["result"] = "RCM workflow completed successfully"
        state["done"] = True
        state["status"] = "completed"
        return state


def create_initial_state(
    user_input: Optional[str] = None,
    patient_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> RCMAgentState:
    """Create initial RCM agent state"""
    state: RCMAgentState = {
        "messages": [],
        "patient_data": None,
        "encounter_data": None,
        "structured_data": None,
        "suggested_codes": None,
        "eligibility_result": None,
        "claim_data": None,
        "status": "collecting",
        "workflow_step": WorkflowStep.INITIALIZATION,
        "question_to_ask": None,
        "ready_for_processing": False,
        "need_user_input": True,
        "done": False,
        "exit_requested": False,
        "result": None,
        "error_message": None,
        "confidence_scores": {},
        "user_context": context or {},
    }

    # Add initial user input if provided
    if user_input:
        state["user_context"]["initial_input"] = user_input
        state["user_context"]["api_mode"] = True

    if patient_id:
        state["user_context"]["patient_id"] = patient_id

    return state


def format_agent_response(state: RCMAgentState) -> Dict[str, Any]:
    """Format agent state for API response"""
    return {
        "status": state.get("status"),
        "workflow_step": str(state.get("workflow_step", "")),
        "question_to_ask": state.get("question_to_ask"),
        "result": state.get("result"),
        "error_message": state.get("error_message"),
        "done": state.get("done", False),
        "need_user_input": state.get("need_user_input", False),
        "confidence_scores": state.get("confidence_scores", {}),
        "patient_data": (
            state["patient_data"].model_dump() if state.get("patient_data") else None
        ),
        "encounter_data": (
            state["encounter_data"].model_dump()
            if state.get("encounter_data")
            else None
        ),
        "structured_data": (
            state["structured_data"].model_dump()
            if state.get("structured_data")
            else None
        ),
        "suggested_codes": (
            state["suggested_codes"].model_dump()
            if state.get("suggested_codes")
            else None
        ),
        "eligibility_result": (
            state["eligibility_result"].model_dump()
            if state.get("eligibility_result")
            else None
        ),
        "claim_data": (
            state["claim_data"].model_dump() if state.get("claim_data") else None
        ),
    }
