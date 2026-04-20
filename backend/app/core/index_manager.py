"""
app/core/index_manager.py
Singleton that owns FAISS index + metadata + BM25 index.
Loaded once at FastAPI startup; shared read-only across all requests.
"""

from __future__ import annotations
import logging
import pickle
import re
from typing import Optional

import faiss

from app.core.config import settings

logger = logging.getLogger(__name__)


def _simple_tokenize(text: str) -> list[str]:
    return re.findall(r'[a-zA-Z]{2,}', text.lower())


class _IndexManager:
    _index:    Optional[faiss.Index] = None
    _metadata: Optional[list]        = None
    _bm25:     Optional[object]      = None   # rank_bm25.BM25Okapi or None
    _bm25_chunks: Optional[list[str]] = None

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    async def load(self) -> None:
        idx_path  = settings.index_path
        meta_path = settings.meta_path
        bm25_path = settings.bm25_path

        if not idx_path.exists() or not meta_path.exists():
            logger.warning(
                "Index files not found (%s). Run: python scripts/build_index.py",
                idx_path,
            )
            return

        logger.info("Loading FAISS index from %s …", idx_path)
        self._index = faiss.read_index(str(idx_path))

        with open(meta_path, "rb") as f:
            self._metadata = pickle.load(f)

        logger.info(
            "FAISS ready — %d vectors, %d metadata records.",
            self._index.ntotal, len(self._metadata),
        )

        # Load BM25 if available
        if bm25_path.exists():
            try:
                with open(bm25_path, "rb") as f:
                    data = pickle.load(f)
                self._bm25        = data["bm25"]
                self._bm25_chunks = data["chunks"]
                logger.info("BM25 index loaded — %d chunks.", len(self._bm25_chunks))
            except Exception as exc:
                logger.warning("BM25 load failed (%s) — hybrid search disabled.", exc)
        else:
            logger.info(
                "No BM25 index found at %s. "
                "Run build_index.py with rank-bm25 installed to enable hybrid search.",
                bm25_path,
            )

    # ── Accessors ──────────────────────────────────────────────────────────────

    def is_ready(self) -> bool:
        return self._index is not None and self._metadata is not None

    @property
    def index(self) -> faiss.Index:
        if self._index is None:
            raise RuntimeError("FAISS index not loaded.")
        return self._index

    @property
    def metadata(self) -> list:
        if self._metadata is None:
            raise RuntimeError("Metadata not loaded.")
        return self._metadata

    @property
    def has_bm25(self) -> bool:
        return self._bm25 is not None

    def bm25_search(self, query: str, top_k: int) -> list[tuple[int, float]]:
        """
        Returns list of (chunk_index, normalised_score) sorted descending.
        Scores normalised to [0, 1] via score / (score + 1).
        """
        if not self.has_bm25:
            return []
        tokens = _simple_tokenize(query)
        raw_scores = self._bm25.get_scores(tokens)

        # Get top-k indices
        import numpy as np
        top_idx = np.argsort(raw_scores)[::-1][:top_k]
        results = []
        for idx in top_idx:
            s = float(raw_scores[idx])
            if s <= 0:
                break
            normalised = s / (s + 1.0)   # squeeze to (0, 1)
            results.append((int(idx), normalised))
        return results

    def chunks_for(self, pdf_index: str) -> list[str]:
        """Return all text chunks for a given pdf_index."""
        return [m["chunk"] for m in self.metadata if m["pdf_index"] == pdf_index]


# Shared singleton
IndexManager = _IndexManager()
