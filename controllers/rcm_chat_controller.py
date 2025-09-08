"""
RCM Chat interface controller for AI agent interaction - Fixed version
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
import json

from database.connection import get_db
from models.patient import Patient
from models.encounter import Encounter
from schemas.chat import ChatMessage, ChatResponse
from utils.auth import get_current_user

router = APIRouter()

# In-memory session storage (use Redis in production)
chat_sessions = {}


def get_or_create_session_state(session_id: str, user_id: str):
    """Get existing session state or create new one"""
    if session_id not in chat_sessions:
        # Import here to avoid circular imports
        from agents.rcm_agent import create_initial_state

        chat_sessions[session_id] = {
            "user_id": user_id,
            "agent_state": create_initial_state(),
            "messages": [],
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
        }

    chat_sessions[session_id]["last_activity"] = datetime.utcnow()
    return chat_sessions[session_id]


def save_session_state(session_id: str, agent_state: Dict[str, Any]):
    """Save agent state to session"""
    if session_id in chat_sessions:
        chat_sessions[session_id]["agent_state"] = agent_state
        chat_sessions[session_id]["last_activity"] = datetime.utcnow()


@router.post("/chat", response_model=ChatResponse)
async def chat_with_rcm_agent(
    message: ChatMessage,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Process chat message with RCM AI agent using single-step execution
    """
    try:
        # Import here to avoid circular imports
        from agents.rcm_agent import RCMAgentExecutor, format_agent_response

        session_id = message.session_id or str(uuid4())
        user_id = current_user["user_id"]

        # Get or create session state
        session = get_or_create_session_state(session_id, user_id)
        agent_state = session["agent_state"]

        # Add user message to session history
        user_message = {
            "role": "user",
            "content": message.message,
            "timestamp": datetime.utcnow().isoformat(),
        }
        session["messages"].append(user_message)

        # Create executor and execute single step
        rcm_executor = RCMAgentExecutor()
        updated_state = rcm_executor.execute_step(agent_state, message.message)

        # Save updated state
        save_session_state(session_id, updated_state)

        # Format response for frontend
        agent_response = format_agent_response(updated_state)

        # Determine AI response message
        # ai_message_content = "I'm processing your request..."

        # if updated_state.get("question_to_ask"):
        #     ai_message_content = updated_state["question_to_ask"]
        # elif updated_state.get("result"):
        #     ai_message_content = updated_state["result"]
        # elif updated_state.get("error_message"):
        #     ai_message_content = (
        #         f"I encountered an issue: {updated_state['error_message']}"
        #     )
        # elif updated_state.get("messages") and updated_state["messages"]:
        #     # Get the last AI message
        #     for msg in reversed(updated_state["messages"]):
        #         if hasattr(msg, "type") and msg.type == "ai":
        #             ai_message_content = msg.content
        #             break

        # Generate contextual AI response using LLM
        ai_message_content = await generate_contextual_response(updated_state)

        # Add AI response to session history
        ai_message = {
            "role": "assistant",
            "content": ai_message_content,
            "timestamp": datetime.utcnow().isoformat(),
            "agent_data": {
                "workflow_step": str(updated_state.get("workflow_step", "")),
                "status": updated_state.get("status"),
                "confidence_scores": updated_state.get("confidence_scores", {}),
            },
        }
        session["messages"].append(ai_message)

        # Add AI response to session history
        ai_message = {
            "role": "assistant",
            "content": ai_message_content,
            "timestamp": datetime.utcnow().isoformat(),
            "agent_data": {
                "workflow_step": str(updated_state.get("workflow_step", "")),
                "status": updated_state.get("status"),
                "confidence_scores": updated_state.get("confidence_scores", {}),
            },
        }
        session["messages"].append(ai_message)

        # Generate suggested actions based on current state
        suggested_actions = generate_suggested_actions(updated_state)

        # Extract relevant data for frontend
        extracted_data = extract_data_for_frontend(updated_state)

        # Calculate overall confidence score
        confidence_scores = updated_state.get("confidence_scores", {})
        confidence_score = None
        if confidence_scores:
            confidence_score = sum(confidence_scores.values()) / len(confidence_scores)

        return ChatResponse(
            response=ai_message_content,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=session_id,
            suggested_actions=suggested_actions,
            extracted_data=extracted_data,
            confidence_score=confidence_score,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing chat message: {str(e)}"
        )


def extract_data_for_frontend(updated_state: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and format data for frontend consumption"""
    extracted_data = {}

    # Helper function to convert models to dict
    def to_dict(data):
        if hasattr(data, "model_dump"):
            return data.model_dump()
        elif hasattr(data, "dict"):
            return data.dict()
        else:
            return data

    # Extract various data types
    data_keys = ["patient_data", "structured_data", "suggested_codes", "claim_data"]

    for key in data_keys:
        if updated_state.get(key):
            extracted_data[key] = to_dict(updated_state[key])

    return extracted_data


def generate_suggested_actions(state: Dict[str, Any]) -> list:
    """Generate suggested actions based on current workflow step"""
    actions = []

    workflow_step = str(state.get("workflow_step", ""))
    status = state.get("status")

    if status == "processing":
        if "data_collection" in workflow_step.lower():
            actions.append(
                {
                    "action": "view_progress",
                    "label": "View Progress",
                    "description": "See what information has been collected so far",
                }
            )

        elif "data_structuring" in workflow_step.lower():
            actions.extend(
                [
                    {
                        "action": "view_structured_data",
                        "label": "View Structured Data",
                        "description": "See how clinical notes are being organized",
                    },
                    {
                        "action": "cancel_processing",
                        "label": "Cancel",
                        "description": "Stop current processing",
                    },
                ]
            )

        elif "medical_coding" in workflow_step.lower():
            actions.extend(
                [
                    {
                        "action": "view_codes_preview",
                        "label": "Preview Codes",
                        "description": "See preliminary code suggestions",
                    },
                    {
                        "action": "pause_for_review",
                        "label": "Pause for Review",
                        "description": "Stop and review before proceeding",
                    },
                ]
            )

        elif "eligibility_checking" in workflow_step.lower():
            actions.extend(
                [
                    {
                        "action": "view_eligibility_status",
                        "label": "Check Status",
                        "description": "View current eligibility verification status",
                    },
                    {
                        "action": "skip_eligibility",
                        "label": "Skip Verification",
                        "description": "Proceed without eligibility check",
                    },
                ]
            )

        elif "claim_processing" in workflow_step.lower():
            actions.extend(
                [
                    {
                        "action": "view_claim_preview",
                        "label": "Preview Claim",
                        "description": "Review claim before final submission",
                    },
                    {
                        "action": "modify_claim",
                        "label": "Modify Claim",
                        "description": "Make changes to the claim data",
                    },
                ]
            )

    elif status == "reviewing":
        if "codes" in str(state.get("question_to_ask", "")).lower():
            actions.extend(
                [
                    {
                        "action": "approve_codes",
                        "label": "Approve All Codes",
                        "description": "Accept all suggested medical codes and continue",
                    },
                    {
                        "action": "review_individual_codes",
                        "label": "Review Each Code",
                        "description": "Review and modify individual codes",
                    },
                    {
                        "action": "reject_codes",
                        "label": "Reject Codes",
                        "description": "Reject suggestions and provide new clinical information",
                    },
                ]
            )

        elif "eligibility" in str(state.get("question_to_ask", "")).lower():
            actions.extend(
                [
                    {
                        "action": "proceed_anyway",
                        "label": "Proceed Anyway",
                        "description": "Continue despite eligibility issues",
                    },
                    {
                        "action": "check_alternative_coverage",
                        "label": "Check Alternative Coverage",
                        "description": "Look for other insurance options",
                    },
                    {
                        "action": "convert_to_self_pay",
                        "label": "Self-Pay Option",
                        "description": "Process as self-pay patient",
                    },
                ]
            )

        elif "claim" in str(state.get("question_to_ask", "")).lower():
            actions.extend(
                [
                    {
                        "action": "submit_claim",
                        "label": "Submit Claim Now",
                        "description": "Submit the prepared claim to the payer",
                    },
                    {
                        "action": "review_claim_details",
                        "label": "Review Details",
                        "description": "Examine all claim components before submission",
                    },
                    {
                        "action": "save_as_draft",
                        "label": "Save as Draft",
                        "description": "Save claim for later submission",
                    },
                ]
            )

    elif state.get("done") and state.get("claim_data"):
        actions.extend(
            [
                {
                    "action": "view_claim_summary",
                    "label": "View Claim Summary",
                    "description": "See complete claim details and submission status",
                },
                {
                    "action": "track_claim_status",
                    "label": "Track Claim",
                    "description": "Monitor the submitted claim progress with payer",
                },
                {
                    "action": "print_claim",
                    "label": "Print Claim",
                    "description": "Generate printable claim form",
                },
                {
                    "action": "start_new_case",
                    "label": "New Patient",
                    "description": "Begin processing a new patient encounter",
                },
            ]
        )

    elif state.get("error_message"):
        actions.extend(
            [
                {
                    "action": "retry_step",
                    "label": "Retry",
                    "description": "Attempt to retry the failed step",
                },
                {
                    "action": "restart_workflow",
                    "label": "Start Over",
                    "description": "Begin the workflow from the beginning",
                },
                {
                    "action": "get_help",
                    "label": "Get Help",
                    "description": "View troubleshooting information",
                },
            ]
        )

    elif status == "collecting":
        actions.extend(
            [
                {
                    "action": "provide_example",
                    "label": "Show Example",
                    "description": "See an example of the required information format",
                },
                {
                    "action": "upload_document",
                    "label": "Upload Document",
                    "description": "Upload clinical notes or patient information file",
                },
                {
                    "action": "skip_optional",
                    "label": "Skip Optional Fields",
                    "description": "Continue with only required information",
                },
            ]
        )

    return actions


@router.get("/chat/sessions/{session_id}")
async def get_chat_session(
    session_id: str, current_user: dict = Depends(get_current_user)
):
    """Get chat session history and current state"""
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Chat session not found")

    session = chat_sessions[session_id]

    # Verify user owns this session
    if session["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Import here to avoid circular imports
    from agents.rcm_agent import format_agent_response

    # Format agent state for response
    agent_response = format_agent_response(session["agent_state"])

    return {
        "session_id": session_id,
        "messages": session["messages"],
        "agent_state": agent_response,
        "created_at": session["created_at"].isoformat(),
        "last_activity": session["last_activity"].isoformat(),
    }


@router.delete("/chat/sessions/{session_id}")
async def delete_chat_session(
    session_id: str, current_user: dict = Depends(get_current_user)
):
    """Delete chat session"""
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Chat session not found")

    session = chat_sessions[session_id]

    # Verify user owns this session
    if session["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    del chat_sessions[session_id]
    return {"message": "Chat session deleted successfully"}


@router.post("/process-encounter")
async def process_encounter_with_agent(
    encounter_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Process an existing encounter through the RCM agent"""
    try:
        # Import here to avoid circular imports
        from agents.rcm_agent import (
            RCMAgentExecutor,
            create_initial_state,
            format_agent_response,
        )

        # Get encounter with patient data
        result = await db.execute(select(Encounter).where(Encounter.id == encounter_id))
        encounter = result.scalar_one_or_none()

        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found")

        # Get patient data
        patient_result = await db.execute(
            select(Patient).where(Patient.id == encounter.patient_id)
        )
        patient = patient_result.scalar_one_or_none()

        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        # Prepare input for RCM agent
        clinical_notes = encounter.raw_notes or "No clinical notes available"
        patient_info = f"Patient: {patient.name}, DOB: {patient.date_of_birth}, Insurance: {patient.insurance_provider}"
        encounter_info = f"Encounter Type: {encounter.encounter_type}, Service Date: {encounter.service_date}"

        combined_input = (
            f"{patient_info}\n{encounter_info}\nClinical Notes: {clinical_notes}"
        )

        # Create new session for this encounter processing
        session_id = str(uuid4())
        initial_state = create_initial_state(
            user_input=combined_input,
            patient_id=str(patient.id),
            context={"encounter_id": str(encounter_id)},
        )

        # Execute initial processing steps
        rcm_executor = RCMAgentExecutor()
        processed_state = rcm_executor.execute_step(initial_state, combined_input)

        # Continue processing if no user input needed
        max_iterations = 5  # Prevent infinite loops
        iterations = 0
        while (
            not processed_state.get("need_user_input")
            and not processed_state.get("done")
            and not processed_state.get("error_message")
            and iterations < max_iterations
        ):
            processed_state = rcm_executor.execute_step(processed_state)
            iterations += 1

        # Save session
        chat_sessions[session_id] = {
            "user_id": current_user["user_id"],
            "agent_state": processed_state,
            "messages": [],
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
        }

        # Update encounter with results if successful
        if processed_state.get("structured_data"):
            structured_data = processed_state["structured_data"]
            encounter.structured_data = extract_data_for_frontend(
                {"structured_data": structured_data}
            )["structured_data"]
            encounter.status = "processed"
            await db.commit()

        return {
            "encounter_id": str(encounter_id),
            "session_id": session_id,
            "status": processed_state.get("status", "processing"),
            "workflow_step": str(processed_state.get("workflow_step", "")),
            "result": format_agent_response(processed_state),
            "message": "Encounter processing initiated with RCM agent",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing encounter: {str(e)}"
        )


async def generate_contextual_response(updated_state: Dict[str, Any]) -> str:
    """Generate contextual user response using LLM based on full workflow state"""

    # Import LLM here to avoid circular imports
    from agents.utils.initializer import get_llm
    from langchain.schema.messages import SystemMessage

    llm = get_llm()

    # Prepare comprehensive workflow context
    workflow_context = {
        "current_step": str(updated_state.get("workflow_step", "")).replace(
            "WorkflowStep.", ""
        ),
        "status": updated_state.get("status"),
        "done": updated_state.get("done", False),
        "need_user_input": updated_state.get("need_user_input", False),
        "error_message": updated_state.get("error_message"),
        "question_to_ask": updated_state.get("question_to_ask"),
        "result": updated_state.get("result"),
        "confidence_scores": updated_state.get("confidence_scores", {}),
    }

    # Add data summaries
    patient_data = updated_state.get("patient_data")
    if patient_data:
        workflow_context["patient_summary"] = {
            "name": getattr(patient_data, "name", None),
            "insurance": getattr(patient_data, "insurance_provider", None),
            "mrn": getattr(patient_data, "mrn", None),
        }

    encounter_data = updated_state.get("encounter_data")
    if encounter_data:
        workflow_context["encounter_summary"] = {
            "type": getattr(encounter_data, "encounter_type", None),
            "date": getattr(encounter_data, "service_date", None),
            "chief_complaint": getattr(encounter_data, "chief_complaint", None),
        }

    structured_data = updated_state.get("structured_data")
    if structured_data:
        workflow_context["structured_data_available"] = True
        workflow_context["diagnoses"] = getattr(structured_data, "diagnoses", [])
        workflow_context["procedures"] = getattr(structured_data, "procedures", [])

    suggested_codes = updated_state.get("suggested_codes")
    if suggested_codes:
        workflow_context["codes_summary"] = {
            "icd10_count": len(getattr(suggested_codes, "icd10_codes", [])),
            "cpt_count": len(getattr(suggested_codes, "cpt_codes", [])),
            "overall_confidence": getattr(suggested_codes, "overall_confidence", 0),
            "requires_review": getattr(suggested_codes, "requires_human_review", False),
        }

        # Include first few codes for context
        icd_codes = getattr(suggested_codes, "icd10_codes", [])
        cpt_codes = getattr(suggested_codes, "cpt_codes", [])

        if icd_codes:
            workflow_context["sample_icd_codes"] = [
                {
                    "code": getattr(code, "code", ""),
                    "description": getattr(code, "description", ""),
                    "confidence": getattr(code, "confidence", 0),
                }
                for code in icd_codes[:3]
            ]

        if cpt_codes:
            workflow_context["sample_cpt_codes"] = [
                {
                    "code": getattr(code, "code", ""),
                    "description": getattr(code, "description", ""),
                    "confidence": getattr(code, "confidence", 0),
                }
                for code in cpt_codes[:3]
            ]

    eligibility_result = updated_state.get("eligibility_result")
    if eligibility_result:
        workflow_context["eligibility_summary"] = {
            "eligible": getattr(eligibility_result, "eligible", False),
            "payer_id": getattr(eligibility_result, "payer_id", ""),
            "copay": getattr(eligibility_result, "copay_amount", 0),
            "deductible_remaining": getattr(
                eligibility_result, "deductible_remaining", 0
            ),
        }

    claim_data = updated_state.get("claim_data")
    if claim_data:
        workflow_context["claim_summary"] = {
            "claim_number": getattr(claim_data, "claim_number", ""),
            "total_amount": getattr(claim_data, "total_amount", 0),
            "patient_responsibility": getattr(claim_data, "patient_responsibility", 0),
            "status": getattr(claim_data, "status", ""),
            "submission_ready": getattr(claim_data, "submission_ready", False),
        }

    # Create response generation prompt
    response_prompt = f"""
You are a healthcare RCM (Revenue Cycle Management) AI assistant communicating with a healthcare provider. Based on the current workflow state, generate an appropriate response for the user.

WORKFLOW CONTEXT:
{json.dumps(workflow_context, indent=2, default=str)}

GUIDELINES:
1. Be conversational and professional
2. Clearly explain what has happened and what's currently happening
3. If there are next steps needed from the user, clearly state them
4. If showing medical codes or data, format them nicely
5. If there are errors, explain them clearly and suggest solutions
6. If workflow is complete, provide a clear summary
7. Use medical terminology appropriately but keep it accessible
8. Be encouraging and supportive

RESPONSE REQUIREMENTS:
- Start with current status
- Explain what was accomplished 
- Show relevant data (codes, amounts, etc.) if available
- Clearly state next steps or what user should do
- Keep it concise but informative
- Use bullet points or formatting for clarity when showing data

Generate a response that would be helpful and informative for the healthcare provider:
"""

    try:
        response = llm.invoke([SystemMessage(content=response_prompt)])
        return response.content

    except Exception as e:
        # Fallback to simple message if LLM fails
        if workflow_context.get("error_message"):
            return f"I encountered an issue: {workflow_context['error_message']}"
        elif workflow_context.get("question_to_ask"):
            return workflow_context[
                "question_to_ask"
            ]  # Generate contextual AI response using LLM
        # ai_message_content = await generate_contextual_response(updated_state)

        # # Add AI response to session history
        # ai_message = {
        #     "role": "assistant",
        #     "content": ai_message_content,
        #     "timestamp": datetime.utcnow().isoformat(),
        #     "agent_data": {
        #         "workflow_step": str(updated_state.get("workflow_step", "")),
        #         "status": updated_state.get("status"),
        #         "confidence_scores": updated_state.get("confidence_scores", {}),
        #     },
        # }
        # session["messages"].append(ai_message)
        elif workflow_context.get("result"):
            return workflow_context["result"]
        elif workflow_context.get("done"):
            return "RCM workflow completed successfully!"
        else:
            return f"Processing {workflow_context.get('current_step', 'workflow')}..."
