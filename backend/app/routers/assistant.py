"""
app/routers/assistant.py
General legal assistant — constitutional questions, rights, procedures.
NOT grounded in a specific case. Uses Constitution reference + LLM knowledge.
Separate from /api/chat which is always case-specific.
"""
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from app.models.schemas import ChatMessage
from app.services.groq_service import general_legal_chat

router = APIRouter()


class AssistantRequest(BaseModel):
    messages: List[ChatMessage]


class AssistantResponse(BaseModel):
    reply: str


@router.post("", response_model=AssistantResponse)
async def assistant(request: AssistantRequest):
    if not request.messages:
        raise HTTPException(400, "messages list is empty.")
    try:
        reply = await asyncio.to_thread(general_legal_chat, request.messages)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))
    return AssistantResponse(reply=reply)
