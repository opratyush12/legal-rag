"""
app/core/config.py
Central configuration — every tunable knob lives here.
All values are env-driven (load from .env automatically).
"""

from __future__ import annotations
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Data ───────────────────────────────────────────────────────────────────
    CSV_PATH: str = "/data/csv/supreme_court_clean_english.csv"

    PDF_STORAGE_BACKEND: str = "local"
    PDF_LOCAL_DIR: str = "/data/pdfs"

    S3_BUCKET: str = ""
    S3_PREFIX: str = "pdfs/"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"

    # ── Index ──────────────────────────────────────────────────────────────────
    INDEX_DIR: str = "./index_store"
    INDEX_FILE: str = "faiss.index"
    META_FILE: str = "metadata.pkl"
    BM25_FILE: str = "bm25.pkl"          # NEW: BM25 index file
    MAX_INDEX_ROWS: int = 12000

    # Chunking — sentence-aware
    CHUNK_SIZE: int = 1200               # target chars per chunk
    OVERLAP: int = 200                   # char overlap between chunks
    MIN_CHUNK_CHARS: int = 100           # discard chunks shorter than this

    # ── Models ─────────────────────────────────────────────────────────────────
    EMBED_MODEL: str = "BAAI/bge-small-en-v1.5"
    RERANK_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    EMBED_BATCH_SIZE: int = 128

    # ── Search ─────────────────────────────────────────────────────────────────
    FAISS_RETRIEVE_K: int = 200
    CANDIDATE_PDFS: int = 20
    TOP_K: int = 5

    # Hybrid search weights (must sum to 1.0)
    SEMANTIC_WEIGHT: float = 0.65        # NEW: FAISS semantic score weight
    BM25_WEIGHT: float = 0.35            # NEW: BM25 keyword score weight
    USE_BM25: bool = True                # NEW: toggle hybrid search

    # Reranking
    RERANK_CHUNKS: int = 4               # chunks per PDF fed to CrossEncoder
    CHUNK_COUNT_BOOST: float = 0.15      # NEW: boost per extra matching chunk

    # Query expansion
    USE_QUERY_EXPANSION: bool = True     # NEW: Groq query expansion toggle
    QUERY_EXPANSION_VARIANTS: int = 3    # NEW: number of expanded queries

    # ── Groq ───────────────────────────────────────────────────────────────────
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_MAX_TOKENS: int = 1024
    GROQ_FALLBACK_MODELS: List[str] = ["llama-3.1-8b-instant", "gemma2-9b-it"]
    GROQ_SUMMARY_MAX_TOKENS: int = 350
    GROQ_SUMMARY_TEMPERATURE: float = 0.2
    GROQ_CHAT_TEMPERATURE: float = 0.3
    GROQ_ASSISTANT_TEMPERATURE: float = 0.4
    CHAT_CONTEXT_MAX_CHARS: int = 5500
    SUMMARY_CONTEXT_MAX_CHARS: int = 1800

    # ── Upload / PDF ───────────────────────────────────────────────────────────
    MAX_PDF_MB: int = 20
    PREVIEW_MAX_CHARS: int = 4000

    # ── Confidence thresholds ──────────────────────────────────────────────────
    CONFIDENCE_HIGH_THRESHOLD: float = 4.0
    CONFIDENCE_MEDIUM_THRESHOLD: float = 0.0

    # ── TTS ────────────────────────────────────────────────────────────────────
    TTS_VOICE: str = "hi-IN-SwaraNeural"

    # ── Server ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = []

    @field_validator("CORS_ORIGINS", "GROQ_FALLBACK_MODELS", mode="before")
    @classmethod
    def parse_str_list(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @property
    def index_path(self) -> Path:
        return Path(self.INDEX_DIR) / self.INDEX_FILE

    @property
    def meta_path(self) -> Path:
        return Path(self.INDEX_DIR) / self.META_FILE

    @property
    def bm25_path(self) -> Path:
        return Path(self.INDEX_DIR) / self.BM25_FILE


settings = Settings()
