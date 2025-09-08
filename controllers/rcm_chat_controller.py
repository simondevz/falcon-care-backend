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
        ai_message_content = "I'm processing your request..."

        if updated_state.get("question_to_ask"):
            ai_message_content = updated_state["question_to_ask"]
        elif updated_state.get("result"):
            ai_message_content = updated_state["result"]
        elif updated_state.get("error_message"):
            ai_message_content = (
                f"I encountered an issue: {updated_state['error_message']}"
            )
        elif updated_state.get("messages") and updated_state["messages"]:
            # Get the last AI message
            for msg in reversed(updated_state["messages"]):
                if hasattr(msg, "type") and msg.type == "ai":
                    ai_message_content = msg.content
                    break

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

    if "data_structuring" in workflow_step and status == "processing":
        actions.append(
            {
                "action": "review_structured_data",
                "label": "Review Structured Data",
                "description": "Review the extracted clinical information",
            }
        )

    elif "medical_coding" in workflow_step and status == "reviewing":
        actions.extend(
            [
                {
                    "action": "approve_codes",
                    "label": "Approve Medical Codes",
                    "description": "Review and approve suggested ICD-10 and CPT codes",
                },
                {
                    "action": "request_changes",
                    "label": "Request Changes",
                    "description": "Ask for modifications to the suggested codes",
                },
            ]
        )

    elif "eligibility_checking" in workflow_step and status == "processing":
        actions.append(
            {
                "action": "view_coverage",
                "label": "View Coverage Details",
                "description": "See detailed insurance coverage information",
            }
        )

    elif "claim_processing" in workflow_step and status == "reviewing":
        actions.extend(
            [
                {
                    "action": "submit_claim",
                    "label": "Submit Claim",
                    "description": "Submit the prepared claim to the payer",
                },
                {
                    "action": "review_claim",
                    "label": "Review Claim Details",
                    "description": "Review claim before submission",
                },
            ]
        )

    elif state.get("done") and state.get("claim_data"):
        actions.extend(
            [
                {
                    "action": "track_claim",
                    "label": "Track Claim Status",
                    "description": "Monitor the submitted claim progress",
                },
                {
                    "action": "start_new",
                    "label": "Start New Case",
                    "description": "Begin processing a new patient encounter",
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
