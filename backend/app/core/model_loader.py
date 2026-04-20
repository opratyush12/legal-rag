"""
app/core/model_loader.py
Lazy singletons for the embedding and reranker models.
Using @lru_cache means they're loaded exactly once per process.
Swap models by changing EMBED_MODEL / RERANK_MODEL in .env — zero code changes.
"""

from __future__ import annotations
import logging
from functools import lru_cache

from sentence_transformers import SentenceTransformer, CrossEncoder
from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_embed_model() -> SentenceTransformer:
    logger.info("Loading embedding model: %s", settings.EMBED_MODEL)
    model = SentenceTransformer(settings.EMBED_MODEL)
    logger.info("Embedding model loaded.")
    return model


@lru_cache(maxsize=1)
def get_reranker() -> CrossEncoder:
    logger.info("Loading reranker model: %s", settings.RERANK_MODEL)
    model = CrossEncoder(settings.RERANK_MODEL)
    logger.info("Reranker loaded.")
    return model
