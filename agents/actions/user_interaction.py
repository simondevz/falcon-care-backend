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
        # Check if we have all required information
        current_patient = state.get("patient_data")
        current_encounter = state.get("encounter_data")

        # Determine what information we still need
        missing_info = []

        if not current_patient or not current_patient.name:
            missing_info.append("patient name")
        if not current_patient or not current_patient.date_of_birth:
            missing_info.append("date of birth")
        if not current_patient or not current_patient.gender:
            missing_info.append("gender")
        if not current_patient or not current_patient.insurance_provider:
            missing_info.append("insurance provider")
        if not current_patient or not current_patient.policy_number:
            missing_info.append("policy number")
        if not current_patient or not current_patient.mrn:
            missing_info.append("medical record number (MRN)")
        if not current_encounter or not current_encounter.encounter_type:
            missing_info.append("encounter type")
        if not current_encounter or not current_encounter.service_date:
            missing_info.append("service date")
        if not current_encounter or not current_encounter.raw_clinical_notes:
            missing_info.append("clinical notes")

        # Create enhanced decision prompt with current state
        decision_prompt = f"""
{user_agent_prompt}

Current Information Status:
Patient Data: {current_patient.model_dump() if current_patient else "None"}
Encounter Data: {current_encounter.model_dump() if current_encounter else "None"}

Missing Information: {missing_info if missing_info else "None - all required info collected"}

Recent conversation context:
{' '.join([msg.content for msg in state["messages"][-3:] if hasattr(msg, 'content')])}

Based on the conversation and current information status, decide:
1. If missing critical information: use "ask_user" and ask for the FIRST missing item
2. If all required information is collected: use "proceed" 
3. If workflow is complete: use "finalize"

Respond with a clear, professional message.
"""

        # Get decision from LLM
        structured_llm = llm.with_structured_output(UserAgentDecision)

        decision = structured_llm.invoke(
            [SystemMessage(content=decision_prompt)]
            + state["messages"][-5:]  # Last 5 messages for context
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
                    content="Great! I have all the information needed. Let me process the clinical data and suggest appropriate medical codes..."
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
            "I had trouble understanding your request. Could you please provide the patient's basic information: name, date of birth, and insurance details?"
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
        # Combine all user messages for extraction
        user_messages = [msg.content for msg in messages if msg.type == "human"]
        combined_text = " ".join(user_messages)

        console.print(
            f"🔍 Extracting data from: {combined_text[:200]}...", style="bold blue"
        )

        # Extract using a single LLM call with manual parsing
        extraction_prompt = f"""
Please extract patient and encounter information from this healthcare conversation and format it as JSON.

Conversation: {combined_text}

Extract the following information and return ONLY a JSON object in this exact format:
{{
    "patient": {{
        "name": "patient full name or null",
        "date_of_birth": "YYYY-MM-DD format or null", 
        "gender": "male/female/other or null",
        "insurance_provider": "insurance company name or null",
        "policy_number": "policy number or null",
        "mrn": "medical record number or null"
    }},
    "encounter": {{
        "encounter_type": "outpatient/inpatient/emergency/telemedicine or null",
        "service_date": "YYYY-MM-DD format or null",
        "chief_complaint": "main complaint or null",
        "raw_clinical_notes": "full clinical notes or null"
    }}
}}

Return only the JSON, no other text.
"""

        response = llm.invoke([SystemMessage(content=extraction_prompt)])

        # Parse the JSON response
        import json
        import re

        # Extract JSON from response
        json_match = re.search(r"\{.*\}", response.content, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            data = json.loads(json_str)

            # Create PatientData object
            patient_info = data.get("patient", {})
            patient_data = PatientData(
                name=patient_info.get("name"),
                date_of_birth=patient_info.get("date_of_birth"),
                gender=patient_info.get("gender"),
                insurance_provider=patient_info.get("insurance_provider"),
                policy_number=patient_info.get("policy_number"),
                mrn=patient_info.get("mrn"),
            )

            # Create EncounterData object
            encounter_info = data.get("encounter", {})
            encounter_data = EncounterData(
                encounter_type=encounter_info.get("encounter_type"),
                service_date=encounter_info.get("service_date"),
                chief_complaint=encounter_info.get("chief_complaint"),
                raw_clinical_notes=encounter_info.get("raw_clinical_notes"),
            )

            console.print(
                f"✅ Successfully extracted patient: {patient_data.name}",
                style="bold green",
            )
            console.print(
                f"✅ Successfully extracted encounter: {encounter_data.encounter_type}",
                style="bold green",
            )

            return patient_data, encounter_data
        else:
            console.print("⚠️ No JSON found in response", style="bold yellow")
            raise ValueError("No valid JSON in response")

    except Exception as e:
        console.print(f"⚠️ Could not extract healthcare data: {e}", style="bold yellow")
        console.print(f"⚠️ Attempting fallback extraction...", style="bold yellow")

        # Fallback: Manual regex extraction
        try:
            combined_text = " ".join(
                [msg.content for msg in messages if msg.type == "human"]
            )

            # Extract patient data using regex patterns
            import re

            # Patient name
            name_match = re.search(
                r"Patient:\s*([^,\n]+)", combined_text, re.IGNORECASE
            )
            name = name_match.group(1).strip() if name_match else None

            # Date of birth
            dob_match = re.search(r"DOB:\s*(\d{4}-\d{2}-\d{2})", combined_text)
            if not dob_match:
                dob_match = re.search(r"(\d{4}-\d{2}-\d{2})", combined_text)
            dob = dob_match.group(1) if dob_match else None

            # Gender
            gender_match = re.search(r"(Male|Female|male|female)", combined_text)
            gender = gender_match.group(1).lower() if gender_match else None

            # Insurance
            insurance_match = re.search(
                r"Insurance:\s*([^,\n]+)", combined_text, re.IGNORECASE
            )
            if not insurance_match:
                insurance_match = re.search(
                    r"(DAMAN|ADNIC|THIQA|BUPA)", combined_text, re.IGNORECASE
                )
            insurance = insurance_match.group(1).strip() if insurance_match else None

            # Policy number
            policy_match = re.search(
                r"Policy\s+Number:\s*([^\s,\n]+)", combined_text, re.IGNORECASE
            )
            policy = policy_match.group(1).strip() if policy_match else None

            # MRN
            mrn_match = re.search(r"MRN:\s*([^\s,\n]+)", combined_text, re.IGNORECASE)
            mrn = mrn_match.group(1).strip() if mrn_match else None

            # Encounter type
            encounter_match = re.search(
                r"Encounter:\s*([^,\n]+)", combined_text, re.IGNORECASE
            )
            if not encounter_match:
                encounter_match = re.search(
                    r"(Outpatient|Inpatient|Emergency|outpatient|inpatient|emergency)",
                    combined_text,
                )
            encounter_type = (
                encounter_match.group(1).strip() if encounter_match else None
            )

            # Service date
            service_date_match = re.search(r"on\s+(\d{4}-\d{2}-\d{2})", combined_text)
            service_date = service_date_match.group(1) if service_date_match else None

            # Chief complaint
            complaint_match = re.search(
                r"Chief\s+Complaint:\s*([^,\n]+)", combined_text, re.IGNORECASE
            )
            chief_complaint = (
                complaint_match.group(1).strip() if complaint_match else None
            )

            # Clinical notes (everything after "Clinical Notes:")
            notes_match = re.search(
                r"Clinical\s+Notes:\s*(.+)", combined_text, re.IGNORECASE | re.DOTALL
            )
            clinical_notes = notes_match.group(1).strip() if notes_match else None

            patient_data = PatientData(
                name=name,
                date_of_birth=dob,
                gender=gender,
                insurance_provider=insurance,
                policy_number=policy,
                mrn=mrn,
            )

            encounter_data = EncounterData(
                encounter_type=encounter_type,
                service_date=service_date,
                chief_complaint=chief_complaint,
                raw_clinical_notes=clinical_notes,
            )

            console.print(
                f"✅ Fallback extraction - Patient: {name}", style="bold cyan"
            )
            console.print(
                f"✅ Fallback extraction - Encounter: {encounter_type}",
                style="bold cyan",
            )

            return patient_data, encounter_data

        except Exception as fallback_error:
            console.print(
                f"⚠️ Fallback extraction failed: {fallback_error}", style="bold red"
            )

            # Last resort: dynamic regex extraction
            combined_text = " ".join(
                [msg.content for msg in messages if msg.type == "human"]
            )

            # Extract patient data using dynamic regex patterns
            import re

            # Patient name - look for "Patient: [Name]"
            name_match = re.search(
                r"Patient:\s*([^,\n]+)", combined_text, re.IGNORECASE
            )
            name = name_match.group(1).strip() if name_match else None

            # Date of birth - look for DOB: or date patterns
            dob_match = re.search(
                r"DOB:\s*(\d{4}-\d{2}-\d{2})", combined_text, re.IGNORECASE
            )
            if not dob_match:
                dob_match = re.search(r"(\d{4}-\d{2}-\d{2})", combined_text)
            dob = dob_match.group(1) if dob_match else None

            # Gender - look for Male/Female
            gender_match = re.search(r"\b(Male|Female)\b", combined_text, re.IGNORECASE)
            gender = gender_match.group(1).lower() if gender_match else None

            # Insurance - look for known providers or "Insurance: [Provider]"
            insurance_match = re.search(
                r"Insurance:\s*([^,\n]+)", combined_text, re.IGNORECASE
            )
            if not insurance_match:
                # Look for common insurance providers
                insurance_match = re.search(
                    r"\b(DAMAN[^,\n]*|ADNIC[^,\n]*|THIQA[^,\n]*|BUPA[^,\n]*)\b",
                    combined_text,
                    re.IGNORECASE,
                )
            insurance = insurance_match.group(1).strip() if insurance_match else None

            # Policy number - look for alphanumeric patterns
            policy_match = re.search(
                r"Policy\s+Number:\s*([A-Z0-9]+)", combined_text, re.IGNORECASE
            )
            if not policy_match:
                # Look for patterns like DM followed by numbers
                policy_match = re.search(r"\b([A-Z]{2}\d{10,})\b", combined_text)
            policy = policy_match.group(1) if policy_match else None

            # MRN - look for MRN: pattern
            mrn_match = re.search(r"MRN:\s*([A-Z0-9]+)", combined_text, re.IGNORECASE)
            if not mrn_match:
                # Look for MRN followed by numbers
                mrn_match = re.search(r"\b(MRN\d+)\b", combined_text, re.IGNORECASE)
            mrn = mrn_match.group(1) if mrn_match else None

            # Encounter type - look for visit types
            encounter_match = re.search(
                r"Encounter:\s*([^,\n]+)", combined_text, re.IGNORECASE
            )
            if not encounter_match:
                encounter_match = re.search(
                    r"\b(Outpatient|Inpatient|Emergency|Telemedicine)\b",
                    combined_text,
                    re.IGNORECASE,
                )
            encounter_type = (
                encounter_match.group(1).strip().lower() if encounter_match else None
            )

            # Service date - look for date patterns
            service_date_match = re.search(
                r"on\s+(\d{4}-\d{2}-\d{2})", combined_text, re.IGNORECASE
            )
            if not service_date_match:
                service_date_match = re.search(r"(\d{4}-\d{2}-\d{2})", combined_text)
            service_date = service_date_match.group(1) if service_date_match else None

            # Chief complaint
            complaint_match = re.search(
                r"Chief\s+Complaint:\s*([^,\n]+)", combined_text, re.IGNORECASE
            )
            chief_complaint = (
                complaint_match.group(1).strip() if complaint_match else None
            )

            # Clinical notes - extract everything after "Clinical Notes:"
            notes_match = re.search(
                r"Clinical\s+Notes:\s*(.+)", combined_text, re.IGNORECASE | re.DOTALL
            )
            clinical_notes = notes_match.group(1).strip() if notes_match else None

            # If no clinical notes found, look for "Patient presents with"
            if not clinical_notes:
                presents_match = re.search(
                    r"Patient presents with.+", combined_text, re.IGNORECASE | re.DOTALL
                )
                clinical_notes = (
                    presents_match.group(0).strip() if presents_match else None
                )

            patient_data = PatientData(
                name=name,
                date_of_birth=dob,
                gender=gender,
                insurance_provider=insurance,
                policy_number=policy,
                mrn=mrn,
            )

            encounter_data = EncounterData(
                encounter_type=encounter_type,
                service_date=service_date,
                chief_complaint=chief_complaint,
                raw_clinical_notes=clinical_notes,
            )

            console.print(
                f"✅ Dynamic extraction - Patient: {name}", style="bold magenta"
            )
            console.print(
                f"✅ Dynamic extraction - Encounter: {encounter_type}",
                style="bold magenta",
            )

            return patient_data, encounter_data
