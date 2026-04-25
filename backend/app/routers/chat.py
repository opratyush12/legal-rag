"""app/routers/chat.py — Groq-powered chat with a selected case."""

import asyncio
import logging
from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatRequest, ChatResponse
from app.services.groq_service import chat_with_case
from app.core.index_manager import IndexManager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not IndexManager.is_ready():
        raise HTTPException(503, "Index not loaded.")

    chunks = IndexManager.chunks_for(request.pdf_index)
    if not chunks:
        raise HTTPException(404, f"Case '{request.pdf_index}' not in index.")

    case_text = " ".join(chunks)

    try:
        reply = await asyncio.to_thread(
            chat_with_case, request.pdf_index, case_text, request.messages
        )
    except RuntimeError as exc:
        logger.error("Chat error for %s: %s", request.pdf_index, exc)
        raise HTTPException(503, "Chat service is temporarily unavailable.")

    return ChatResponse(reply=reply, pdf_index=request.pdf_index)
