"""
app/routers/upload.py
POST /api/upload/pdf  — Accept a PDF, extract text, search against existing index.
The PDF is NOT added to the index — it's used as a rich query only.
This keeps the curated knowledge base clean.
"""

import io
import logging
import asyncio
import re

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.core.index_manager import IndexManager
from app.models.schemas import SearchResponse
from app.services.search_service import run_search
from app.models.schemas import SearchRequest

from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


def _clean_extracted_text(raw: str) -> str:
    """Remove PDF artifacts from extracted text."""
    return (
        raw.replace("\x00", " ")
        .replace("\x0c", "\n")  # form feed → newline
        .replace("\x0b", " ")
        # Remove PDF escape sequences like \026
        .encode("utf-8", errors="ignore")
        .decode("utf-8")
        .replace("\ufffd", " ")
        # Collapse whitespace
        .__class__(re.sub(r"[ \t]{2,}", " ", raw.replace("\x00", " ")))
    )


def _extract_text_pdfplumber(content: bytes) -> str:
    """Primary extractor — pdfplumber (best for structured legal PDFs)."""
    import pdfplumber

    text_parts = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    return "\n".join(text_parts)


def _extract_text_pymupdf(content: bytes) -> str:
    """Fallback extractor — PyMuPDF (faster, handles more PDF types)."""
    import fitz  # PyMuPDF

    doc = fitz.open(stream=content, filetype="pdf")
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts)


def extract_text(content: bytes) -> str:
    """Try pdfplumber first, fall back to PyMuPDF."""
    text = ""
    try:
        text = _extract_text_pdfplumber(content)
        logger.info("Text extracted with pdfplumber — %d chars", len(text))
    except Exception as exc:
        logger.warning("pdfplumber failed (%s), trying PyMuPDF …", exc)
        try:
            text = _extract_text_pymupdf(content)
            logger.info("Text extracted with PyMuPDF — %d chars", len(text))
        except Exception as exc2:
            logger.error("Both PDF extractors failed: %s", exc2)
            raise HTTPException(
                status_code=422,
                detail="Could not extract text from this PDF. It may be scanned/image-only.",
            )

    # Clean artifacts
    text = re.sub(r"\\[0-9]{2,3}", " ", text)  # \026 style escapes
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if len(text) < 50:
        raise HTTPException(
            status_code=422,
            detail="Extracted text is too short. PDF may be image-only or corrupted.",
        )
    return text


def _make_query(text: str, max_chars: int = 2000) -> str:
    """
    Convert extracted PDF text into a search query.
    Takes the first substantive portion (skips headers/titles).
    """
    lines = [line.strip() for line in text.split("\n") if len(line.strip()) > 40]
    query = " ".join(lines[:10])
    return query[:max_chars]


@router.post("/pdf", response_model=SearchResponse)
async def search_from_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF → extract text → search against the 34k Supreme Court index.
    The uploaded PDF is NOT stored or added to the index.
    """
    if not IndexManager.is_ready():
        raise HTTPException(503, "Vector index not loaded.")

    # Validate file type
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        ct = file.content_type or "unknown"
        if not (file.filename or "").lower().endswith(".pdf"):
            raise HTTPException(400, f"Only PDF files are accepted. Got: {ct}")

    # Read file
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_PDF_MB:
        raise HTTPException(
            413, f"PDF too large ({size_mb:.1f} MB). Max {settings.MAX_PDF_MB} MB."
        )

    # Validate PDF magic bytes (%PDF header)
    if not content[:5].startswith(b"%PDF-"):
        raise HTTPException(400, "Invalid PDF file: missing PDF header.")

    logger.info("PDF upload: %s  %.2f MB", file.filename, size_mb)

    # Extract text in thread (CPU-bound)
    text = await asyncio.to_thread(extract_text, content)
    query = _make_query(text)

    logger.info("Search query from PDF (%d chars): %s…", len(query), query[:120])

    # Run through the normal search pipeline
    request = SearchRequest(query=query, top_k=settings.TOP_K)
    return await run_search(request)
