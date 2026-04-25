"""
app/services/search_service.py
Upgraded retrieval pipeline v2:
  1. Groq query expansion  — search with original + N legal variants
  2. FAISS semantic search — top-200 chunks per query variant
  3. BM25 keyword search   — blended with semantic via weighted scores
  4. Score aggregation     — sum scores per PDF + chunk-count boost
  5. CrossEncoder rerank   — full attention on top-20 candidates
  6. Groq summary          — per-result relevance explanation
  7. Confidence label      — High / Medium / Low based on reranker score
"""

from __future__ import annotations
import asyncio
import logging
from collections import defaultdict
from typing import List, Tuple

from app.core.config import settings
from app.core.index_manager import IndexManager
from app.core.model_loader import get_embed_model, get_reranker
from app.core.storage import storage
from app.models.schemas import SearchRequest, SearchResponse, CaseSummary
from app.services.groq_service import generate_relevance_summary, expand_query

logger = logging.getLogger(__name__)


# ── Confidence labelling ───────────────────────────────────────────────────────

def _confidence(score: float) -> str:
    """
    CrossEncoder ms-marco scores typically range ~ -10 to +10.
    Map to human-readable confidence.
    """
    if score >= settings.CONFIDENCE_HIGH_THRESHOLD:
        return "High"
    elif score >= settings.CONFIDENCE_MEDIUM_THRESHOLD:
        return "Medium"
    else:
        return "Low"


# ── Async entry point ──────────────────────────────────────────────────────────

async def run_search(request: SearchRequest) -> SearchResponse:
    """Async entry — CPU-heavy work runs in a thread pool."""
    results, n_candidates, expanded = await asyncio.to_thread(
        _sync_pipeline, request.query, request.top_k
    )
    return SearchResponse(
        query=request.query,
        expanded_queries=expanded,
        results=results,
        total_candidates_evaluated=n_candidates,
    )


# ── Main synchronous pipeline ──────────────────────────────────────────────────

def _sync_pipeline(
    query: str,
    top_k: int,
) -> Tuple[List[CaseSummary], int, List[str]]:

    embed_model = get_embed_model()

    # ── 1. Query expansion ─────────────────────────────────────────────────────
    if settings.USE_QUERY_EXPANSION and settings.GROQ_API_KEY:
        expanded_queries = expand_query(query, n=settings.QUERY_EXPANSION_VARIANTS)
        logger.info("Query expanded to %d variants: %s", len(expanded_queries), expanded_queries)
    else:
        expanded_queries = [query]

    # ── 2. Semantic + BM25 retrieval across all query variants ─────────────────
    pdf_score:  defaultdict[str, float] = defaultdict(float)
    pdf_chunks: defaultdict[str, List[str]] = defaultdict(list)
    pdf_chunk_count: defaultdict[str, int] = defaultdict(int)  # for chunk-count boost

    for q in expanded_queries:
        # Semantic search
        q_vec = embed_model.encode([q], normalize_embeddings=True).astype("float32")
        D, I_idx = IndexManager.index.search(q_vec, settings.FAISS_RETRIEVE_K)

        for dist, idx in zip(D[0], I_idx[0]):
            if idx < 0:
                continue
            meta = IndexManager.metadata[idx]
            pdf  = meta["pdf_index"]
            sem_score = float(dist)  # already cosine similarity (IP of normalised vecs)

            pdf_score[pdf]       += sem_score * settings.SEMANTIC_WEIGHT
            pdf_chunk_count[pdf] += 1
            if meta["chunk"] not in pdf_chunks[pdf]:
                pdf_chunks[pdf].append(meta["chunk"])

        # BM25 keyword search (if available)
        if settings.USE_BM25 and IndexManager.has_bm25:
            bm25_hits = IndexManager.bm25_search(q, top_k=settings.FAISS_RETRIEVE_K)
            for chunk_idx, bm25_score in bm25_hits:
                if chunk_idx >= len(IndexManager.metadata):
                    continue
                meta = IndexManager.metadata[chunk_idx]
                pdf  = meta["pdf_index"]
                pdf_score[pdf]       += bm25_score * settings.BM25_WEIGHT
                pdf_chunk_count[pdf] += 1
                if meta["chunk"] not in pdf_chunks[pdf]:
                    pdf_chunks[pdf].append(meta["chunk"])

    # ── 3. Chunk-count boost ────────────────────────────────────────────────────
    # Cases matched by many chunks get a boost — signals broader relevance.
    for pdf in pdf_score:
        extra_chunks = max(0, pdf_chunk_count[pdf] - 1)
        pdf_score[pdf] += extra_chunks * settings.CHUNK_COUNT_BOOST

    # ── 4. Preliminary rank → top-N candidates ─────────────────────────────────
    ranked     = sorted(pdf_score.items(), key=lambda x: x[1], reverse=True)
    candidates = [pdf for pdf, _ in ranked[: settings.CANDIDATE_PDFS]]
    logger.info(
        "Candidates after retrieval: %d  (BM25 active: %s)",
        len(candidates),
        IndexManager.has_bm25,
    )

    # ── 5. CrossEncoder reranking ───────────────────────────────────────────────
    reranker = get_reranker()
    pairs = [
        (query, " ".join(pdf_chunks[pdf][: settings.RERANK_CHUNKS]))
        for pdf in candidates
    ]
    ce_scores = reranker.predict(pairs)

    reranked = sorted(zip(candidates, ce_scores), key=lambda x: x[1], reverse=True)
    final    = reranked[:top_k]
    logger.info("Final results after reranking: %d", len(final))

    # ── 6. Build result objects ─────────────────────────────────────────────────
    summaries: List[CaseSummary] = []
    for pdf_index, score in final:
        chunks  = pdf_chunks[pdf_index]
        snippet = chunks[0][:500] if chunks else ""
        context = " ".join(chunks[: settings.RERANK_CHUNKS])

        summary = generate_relevance_summary(
            query=query,
            case_text=context,
            pdf_index=pdf_index,
        )

        summaries.append(CaseSummary(
            pdf_index=pdf_index,
            relevance_score=float(score),
            confidence=_confidence(float(score)),
            summary=summary,
            snippet=snippet,
            available=storage.exists(pdf_index),
            chunk_hits=pdf_chunk_count[pdf_index],
        ))

    return summaries, len(candidates), expanded_queries
