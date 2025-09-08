"""
FalconCare MVP - AI-Native RCM Platform
FastAPI Backend Application Entry Point with RCM Agent Integration
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
import uvicorn
from datetime import datetime

from database.connection import engine, get_db
from models import patient, encounter, claim, denial
from controllers import (
    patient_controller,
    encounter_controller,
    claims_controller,
    auth_controller,
    rcm_chat_controller,
)
from utils.auth import get_current_user


# Create all tables
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(patient.Base.metadata.create_all)
        await conn.run_sync(encounter.Base.metadata.create_all)
        await conn.run_sync(claim.Base.metadata.create_all)
        await conn.run_sync(denial.Base.metadata.create_all)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await create_tables()
    print("🏥 FalconCare Backend Started Successfully")
    print("🤖 RCM AI Agent Initialized")
    yield
    # Shutdown
    print("🔄 FalconCare Backend Shutting Down")


app = FastAPI(
    title="FalconCare MVP API",
    description="AI-Native Revenue Cycle Management Platform with LangGraph Agents",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "https://falcon-care-frontend.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()


# Health Check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "service": "FalconCare MVP Backend",
        "features": {
            "ai_agent": "enabled",
            "langgraph": "enabled",
            "rcm_workflows": "enabled",
        },
    }


# Authentication Routes
app.include_router(auth_controller.router, prefix="/auth", tags=["Authentication"])

# Patient Management Routes
app.include_router(
    patient_controller.router,
    prefix="/patients",
    tags=["Patients"],
    dependencies=[Depends(get_current_user)],
)

# Encounter Routes
app.include_router(
    encounter_controller.router,
    prefix="/encounters",
    tags=["Encounters"],
    dependencies=[Depends(get_current_user)],
)

# Claims Routes
app.include_router(
    claims_controller.router,
    prefix="/claims",
    tags=["Claims"],
    dependencies=[Depends(get_current_user)],
)

# RCM AI Agent Chat Interface
app.include_router(
    rcm_chat_controller.router,
    prefix="/ai",
    tags=["AI Agent"],
    dependencies=[Depends(get_current_user)],
)


# Legacy Chat Interface (for backward compatibility)
@app.post("/chat")
async def legacy_chat_interface(
    message: dict, current_user: dict = Depends(get_current_user)
):
    """Legacy chat interface - redirects to new AI agent endpoint"""
    user_message = message.get("message", "")

    if not user_message:
        raise HTTPException(status_code=400, detail="Message is required")

    try:
        # Import here to avoid circular imports
        from agents.rcm_agent import (
            RCMAgentExecutor,
            create_initial_state,
            format_agent_response,
        )

        # Create executor and initial state
        executor = RCMAgentExecutor()
        initial_state = create_initial_state(user_input=user_message)

        # Execute agent step
        result_state = executor.execute_step(initial_state, user_message)
        result = format_agent_response(result_state)

        return {
            "response": result.get("result")
            or result.get("question_to_ask")
            or "RCM agent processed your request",
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": current_user["user_id"],
            "agent_result": result,
            "note": "This endpoint is deprecated. Please use /ai/chat for enhanced functionality.",
        }
    except Exception as e:
        return {
            "response": f"I encountered an error: {str(e)}",
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": current_user["user_id"],
            "error": True,
        }


# AI Agent Status Endpoint
@app.get("/ai/status")
async def ai_agent_status(current_user: dict = Depends(get_current_user)):
    """Get AI agent status and capabilities"""
    return {
        "status": "active",
        "agent_type": "RCM LangGraph Agent",
        "capabilities": [
            "Clinical data structuring",
            "Medical coding (ICD-10, CPT)",
            "Insurance eligibility verification",
            "Claim processing and submission",
            "Denial management",
        ],
        "workflow_steps": [
            "data_collection",
            "data_structuring",
            "medical_coding",
            "eligibility_checking",
            "claim_processing",
        ],
        "supported_payers": ["DAMAN", "ADNIC", "THIQA", "BUPA"],
        "confidence_thresholds": {
            "auto_approve": 0.9,
            "human_review": 0.7,
            "reject": 0.5,
        },
    }


# Error Handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {
        "error": "Resource not found",
        "detail": str(exc),
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return {
        "error": "Internal server error",
        "detail": "An unexpected error occurred",
        "timestamp": datetime.utcnow().isoformat(),
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
