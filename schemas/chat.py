"""
Chat interface schemas for AI agent interaction
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    context: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    timestamp: datetime
    user_id: str
    session_id: Optional[str] = None
    suggested_actions: Optional[List[Dict[str, Any]]] = None
    extracted_data: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None


class ChatSession(BaseModel):
    session_id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    context: Dict[str, Any] = {}


class ChatHistory(BaseModel):
    session_id: str
    messages: List[Dict[str, Any]]
    total_messages: int
