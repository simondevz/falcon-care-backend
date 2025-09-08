"""
User interaction agent for RCM workflows
"""

from typing import List
from langchain.schema.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    AIMessage,
)
from rich.console import Console
from rich.prompt import Prompt

from agents.utils.initializer import get_llm
from agents.utils.models import (
    RCMAgentState,
    DecisionAction,
    PatientData,
    EncounterData,
    UserAgentDecision,
    WorkflowStep,
)
from agents.utils.prompts import user_agent_prompt

console = Console()
llm = get_llm()


def initialize_rcm_state(state: RCMAgentState) -> RCMAgentState:
    """Initialize the RCM agent state."""
    state["messages"] = []
    state["patient_data"] = None
    state["encounter_data"] = None
    state["structured_data"] = None
    state["suggested_codes"] = None
    state["eligibility_result"] = None
    state["claim_data"] = None
    state["status"] = "collecting"
    state["workflow_step"] = WorkflowStep.DATA_COLLECTION
    state["question_to_ask"] = None
    state["ready_for_processing"] = False
    state["need_user_input"] = True
    state["done"] = False
    state["exit_requested"] = False
    state["result"] = None
    state["error_message"] = None
    state["confidence_scores"] = {}

    # Set initial question based on context
    user_context = state.get("user_context", {})
    initial_input = user_context.get("initial_input")

    if initial_input:
        # Process initial input immediately
        state["messages"].append(HumanMessage(content=initial_input))
        state["question_to_ask"] = None
    else:
        state["question_to_ask"] = (
            "Welcome to FalconCare RCM! Please describe the patient encounter you'd like to process."
        )

    return state


def process_user_input(state: RCMAgentState) -> RCMAgentState:
    """Process user input and add it to the messages."""
    try:
        # Check if we're in API mode (no interactive prompts)
        user_context = state.get("user_context", {})
        api_mode = user_context.get("api_mode", False)

        if api_mode:
            # In API mode, we expect input to already be in messages
            if not state["messages"] or state["messages"][-1].type != "human":
                state["error_message"] = "No user input provided in API mode"
                state["status"] = "error"
                return state
        else:
            # Interactive mode - prompt for input
            if state["question_to_ask"]:
                prompt_text = state["question_to_ask"]
            else:
                prompt_text = "Please provide additional information: "

            # Get user input with Rich Prompt
            user_input = Prompt.ask(f"\n[bold cyan]{prompt_text}[/bold cyan]")

            # Check for exit command
            if user_input.lower() in ["exit", "quit", "bye", "done"]:
                state["exit_requested"] = True
                return state

            # Add user message to the conversation history
            if user_input.strip():
                state["messages"].append(HumanMessage(content=user_input))

        # Clear the question after processing
        state["question_to_ask"] = None
        state["need_user_input"] = False

        return state

    except KeyboardInterrupt:
        state["exit_requested"] = True
        return state
    except Exception as e:
        console.print(f"❌ Error processing input: {e}", style="bold red")
        state["error_message"] = str(e)
        state["status"] = "error"
        return state


def generate_user_agent_decision(state: RCMAgentState) -> RCMAgentState:
    """Generate user agent decision using the LLM."""
    # Skip if exit requested or no messages
    if state["exit_requested"] or not state["messages"]:
        return state

    # Also skip if the last message is not from user
    if state["messages"][-1].type != "human":
        return state

    console.print(
        f"🤖 Processing messages: {len(state['messages'])} total", style="bold yellow"
    )
    console.print(
        f"📊 Current workflow step: {state['workflow_step']}", style="bold yellow"
    )

    try:
        # Create decision prompt
        decision_prompt = f"""
{user_agent_prompt}

Current workflow step: {state['workflow_step']}
Current patient data: {state.get('patient_data')}
Current encounter data: {state.get('encounter_data')}

Based on the conversation, decide what to do:
1. "ask_user" - Need more information from user
2. "proceed" - Have enough info to proceed to next processing step
3. "finalize" - Task is complete

Keep your message simple and clear without special formatting.
"""

        # Get decision from LLM
        structured_llm = llm.with_structured_output(UserAgentDecision)

        decision = structured_llm.invoke(
            [SystemMessage(content=decision_prompt)] + state["messages"]
        )

        console.print(
            f"🤖 UserAgent Decision: {decision.action} - {decision.message}",
            style="bold green",
        )

        # Handle different actions
        if decision.action == DecisionAction.ASK_USER:
            # Set question to ask user
            state["question_to_ask"] = decision.message
            state["messages"].append(AIMessage(content=decision.message))
            state["status"] = "collecting"
            state["need_user_input"] = True
            return state

        elif decision.action == DecisionAction.PROCEED:
            # Extract patient and encounter data from conversation
            patient_data, encounter_data = extract_healthcare_data_from_messages(
                state["messages"]
            )

            console.print(
                f"✅ Extracted patient data: {patient_data}", style="bold green"
            )
            console.print(
                f"✅ Extracted encounter data: {encounter_data}", style="bold green"
            )

            state["messages"].append(
                AIMessage(
                    content="Great! I have the information needed. Processing your clinical data now..."
                )
            )
            state["patient_data"] = patient_data
            state["encounter_data"] = encounter_data
            state["status"] = "processing"
            state["workflow_step"] = WorkflowStep.DATA_STRUCTURING
            state["ready_for_processing"] = True
            state["done"] = False
            return state

        elif decision.action == DecisionAction.FINALIZE:
            state["messages"].append(AIMessage(content=decision.message))
            state["status"] = "completed"
            state["workflow_step"] = WorkflowStep.COMPLETED
            state["done"] = True
            state["result"] = "RCM workflow completed successfully"
            return state

        else:  # ERROR case
            state["messages"].append(
                AIMessage(content="I encountered an error processing your request.")
            )
            state["status"] = "error"
            state["done"] = True
            state["error_message"] = decision.message
            return state

    except Exception as e:
        console.print(
            f"❌ Error in generate_user_agent_decision: {e}", style="bold red"
        )
        state["question_to_ask"] = (
            "I had trouble understanding your request. Could you please clarify the patient encounter details?"
        )
        state["status"] = "collecting"
        state["need_user_input"] = True
        state["error_message"] = str(e)
        return state


def extract_healthcare_data_from_messages(
    messages: List[BaseMessage],
) -> tuple[PatientData, EncounterData]:
    """
    Extract patient and encounter data from conversation messages.
    """
    try:
        # Use LLM to extract structured healthcare data
        patient_extractor = llm.with_structured_output(PatientData)
        encounter_extractor = llm.with_structured_output(EncounterData)

        extraction_prompt = """
Extract healthcare information from this conversation.
Look for patient demographics, insurance information, encounter details, and clinical notes.
If information is not mentioned, leave fields as null.
"""

        # Extract patient data
        patient_data = patient_extractor.invoke(
            [
                SystemMessage(
                    content=extraction_prompt
                    + "\nFocus on patient demographics and insurance information."
                )
            ]
            + messages
        )

        # Extract encounter data
        encounter_data = encounter_extractor.invoke(
            [
                SystemMessage(
                    content=extraction_prompt
                    + "\nFocus on encounter details, clinical notes, and services provided."
                )
            ]
            + messages
        )

        return patient_data, encounter_data

    except Exception as e:
        console.print(f"⚠️ Could not extract healthcare data: {e}", style="bold yellow")
        # Return empty data if extraction fails
        return PatientData(), EncounterData()
