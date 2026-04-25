"""app/routers/cases.py — PDF download + text preview."""

import urllib.parse
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.storage import storage
from app.core.config import settings
from app.core.index_manager import IndexManager
from app.models.schemas import CasePreviewResponse

router = APIRouter()


@router.get("/{pdf_index:path}/download")
async def download_pdf(pdf_index: str):
    pdf_index = urllib.parse.unquote(pdf_index)
    path = storage.get_pdf_path(pdf_index)
    if path is None:
        raise HTTPException(404, f"PDF '{pdf_index}' not found.")
    return FileResponse(str(path), media_type="application/pdf", filename=pdf_index)


@router.get("/{pdf_index:path}/preview", response_model=CasePreviewResponse)
async def preview_case(pdf_index: str):
    pdf_index = urllib.parse.unquote(pdf_index)
    if not IndexManager.is_ready():
        raise HTTPException(503, "Index not loaded.")
    chunks = IndexManager.chunks_for(pdf_index)
    if not chunks:
        raise HTTPException(404, f"Case '{pdf_index}' not found in index.")
    return CasePreviewResponse(
        pdf_index=pdf_index,
        text_preview=" ".join(chunks)[: settings.PREVIEW_MAX_CHARS],
        available=storage.exists(pdf_index),
    )
