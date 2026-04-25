"""app/models/schemas.py — all API request/response models."""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


# ── Search ─────────────────────────────────────────────────────────────────────


class SearchRequest(BaseModel):
    query: str = Field(
        ..., min_length=10, description="Case description or legal scenario."
    )
    top_k: int = Field(default=5, ge=1, le=20)


class CaseSummary(BaseModel):
    pdf_index: str
    relevance_score: float
    confidence: str  # "High" | "Medium" | "Low"
    summary: str  # AI-generated relevance explanation
    snippet: str  # raw text excerpt
    available: bool  # is the PDF downloadable?
    chunk_hits: int  # how many chunks matched this case


class SearchResponse(BaseModel):
    query: str
    expanded_queries: List[str]  # queries actually used (original + expansions)
    results: List[CaseSummary]
    total_candidates_evaluated: int


# ── Cases ──────────────────────────────────────────────────────────────────────


class CasePreviewResponse(BaseModel):
    pdf_index: str
    text_preview: str
    available: bool


# ── Chat ───────────────────────────────────────────────────────────────────────


class ChatMessage(BaseModel):
    role: str = Field(..., pattern=r"^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=10000)


class ChatRequest(BaseModel):
    pdf_index: str = Field(
        ..., min_length=1, max_length=500, pattern=r"^[a-zA-Z0-9_\-\.\(\)\[\] ]+$"
    )
    messages: List[ChatMessage] = Field(..., min_length=1, max_length=50)


class ChatResponse(BaseModel):
    reply: str
    pdf_index: str


# ── Voice ──────────────────────────────────────────────────────────────────────


class TTSRequest(BaseModel):
    text: str = Field(..., max_length=3000)
    voice: Optional[str] = None
