"""
FalconCare MVP - AI-Native RCM Platform
FastAPI Backend Application Entry Point
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
    yield
    # Shutdown
    print("🔄 FalconCare Backend Shutting Down")


app = FastAPI(
    title="FalconCare MVP API",
    description="AI-Native Revenue Cycle Management Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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


# Chat Interface for AI Agent (placeholder for now)
@app.post("/chat")
async def chat_interface(message: dict, current_user: dict = Depends(get_current_user)):
    """
    Chat interface for AI agent interaction
    This will be connected to LangGraph workflows later
    """
    user_message = message.get("message", "")

    # Simple echo response for now - will be replaced with AI agent
    return {
        "response": f"Received your message: {user_message}. AI agent integration coming soon!",
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": current_user["user_id"],
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
