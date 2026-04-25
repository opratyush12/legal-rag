"""
app/main.py — FastAPI application factory.
"""
from __future__ import annotations
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.index_manager import IndexManager
from app.routers import search, cases, chat, voice, assistant, upload

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Startup: loading vector index …")
    await IndexManager.load()
    if IndexManager.is_ready():
        logger.info("Index loaded successfully.")
    else:
        logger.warning("Index NOT loaded — search will return 503 until you run build_index.py.")
    yield
    logger.info("Shutdown complete.")


app = FastAPI(
    title="Legal Case RAG",
    version="1.0.0",
    description="Semantic search + reranking + LLM chat over 34k Supreme Court cases.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(cases.router,  prefix="/api/cases",  tags=["cases"])
app.include_router(chat.router,   prefix="/api/chat",   tags=["chat"])
app.include_router(voice.router,     prefix="/api/voice",     tags=["voice"])
app.include_router(assistant.router, prefix="/api/assistant", tags=["assistant"])
app.include_router(upload.router,    prefix="/api/upload",    tags=["upload"])


@app.get("/health", tags=["meta"])
async def health():
    return {
        "status": "ok",
        "index_loaded": IndexManager.is_ready(),
        "model": settings.EMBED_MODEL,
    }
