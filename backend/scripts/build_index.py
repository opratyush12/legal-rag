# """
# scripts/build_index.py
# Run once (or whenever the CSV changes) to build the FAISS + BM25 index.

# Improvements over v1:
#   1. Sentence-aware chunking  — no mid-sentence cuts
#   2. BM25 index built in parallel — enables hybrid search at query time
#   3. Chunks shorter than MIN_CHUNK_CHARS are discarded
#   4. IVFFlat auto-selected for large corpora (>100k chunks)

# Usage (from backend/ directory):
#     python scripts/build_index.py

# Quick dev build (2000 rows):
#     set MAX_INDEX_ROWS=2000 && python scripts/build_index.py   # Windows
#     MAX_INDEX_ROWS=2000 python scripts/build_index.py          # Linux/Mac
# """

# from __future__ import annotations
# import csv
# import logging
# import pickle
# import re
# import sys
# from pathlib import Path

# import faiss
# import numpy as np
# import pandas as pd
# from sentence_transformers import SentenceTransformer

# sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# from app.core.config import settings  # noqa: E402

# try:
#     csv.field_size_limit(sys.maxsize)
# except OverflowError:
#     csv.field_size_limit(10 ** 9)

# logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
# log = logging.getLogger(__name__)


# # ── Sentence-aware chunker ─────────────────────────────────────────────────────

# # Simple but effective: split on sentence boundaries first,
# # then pack sentences into chunks up to CHUNK_SIZE chars.
# _SENT_SPLIT = re.compile(r'(?<=[.!?])\s+')


# def sentence_chunk(text: str, size: int, overlap_chars: int, min_chars: int) -> list[str]:
#     """
#     Split text into chunks that always end at sentence boundaries.
#     - size:          target max characters per chunk
#     - overlap_chars: carry this many chars from end of previous chunk
#     - min_chars:     discard any chunk shorter than this
#     """
#     # Split into sentences; fall back to whitespace split for very long runs
#     raw_sentences = _SENT_SPLIT.split(text.strip())
#     sentences: list[str] = []
#     for s in raw_sentences:
#         if len(s) <= size:
#             sentences.append(s)
#         else:
#             # Sentence itself too long — split by word boundary
#             words = s.split()
#             buf = ""
#             for w in words:
#                 if len(buf) + len(w) + 1 <= size:
#                     buf = (buf + " " + w).strip()
#                 else:
#                     if buf:
#                         sentences.append(buf)
#                     buf = w
#             if buf:
#                 sentences.append(buf)

#     chunks: list[str] = []
#     current = ""
#     overlap_tail = ""

#     for sent in sentences:
#         candidate = (overlap_tail + " " + current + " " + sent).strip()
#         if len(candidate) <= size:
#             current = candidate
#         else:
#             if current and len(current) >= min_chars:
#                 chunks.append(current)
#                 # Carry overlap from the tail of the finished chunk
#                 overlap_tail = current[-overlap_chars:] if overlap_chars else ""
#             current = (overlap_tail + " " + sent).strip()
#             overlap_tail = ""

#     if current and len(current) >= min_chars:
#         chunks.append(current)

#     return chunks


# # ── BM25 helpers ──────────────────────────────────────────────────────────────

# def _simple_tokenize(text: str) -> list[str]:
#     """Lowercase alpha-only tokens — good enough for BM25 keyword matching."""
#     return re.findall(r'[a-zA-Z]{2,}', text.lower())


# def build_bm25(chunks: list[str]):
#     """Build and return a BM25Okapi index over the chunk list."""
#     try:
#         from rank_bm25 import BM25Okapi
#     except ImportError:
#         log.warning("rank-bm25 not installed — skipping BM25 index. Run: pip install rank-bm25")
#         return None

#     log.info("Tokenising %d chunks for BM25 …", len(chunks))
#     tokenised = [_simple_tokenize(c) for c in chunks]
#     bm25 = BM25Okapi(tokenised)
#     log.info("BM25 index built.")
#     return bm25


# # ── Main ──────────────────────────────────────────────────────────────────────

# def main() -> None:
#     # 1. Load CSV ──────────────────────────────────────────────────────────────
#     csv_path = Path(settings.CSV_PATH)
#     log.info("Loading CSV: %s", csv_path)
#     df = pd.read_csv(
#         csv_path,
#         usecols=["pdf_index", "text"],
#         engine="python",
#         encoding="utf-8",
#         on_bad_lines="skip",
#     )
#     log.info("Raw rows: %d", len(df))

#     # Sort deterministically by numeric PDF id
#     df["_num"] = (
#         df["pdf_index"]
#         .str.replace(r"\.pdf$", "", regex=True)
#         .str.extract(r"(\d+)$")[0]
#         .astype(float)
#     )
#     df = df.sort_values("_num").drop(columns=["_num"]).reset_index(drop=True)

#     if settings.MAX_INDEX_ROWS < len(df):
#         log.info("Limiting to %d rows (full: %d).", settings.MAX_INDEX_ROWS, len(df))
#         df = df.head(settings.MAX_INDEX_ROWS)

#     log.info("Rows to index: %d", len(df))

#     # 2. Sentence-aware chunking ───────────────────────────────────────────────
#     all_chunks: list[str] = []
#     metadata:   list[dict] = []
#     skipped_short = 0

#     for i, row in df.iterrows():
#         text      = str(row["text"]) if pd.notna(row["text"]) else ""
#         pdf_index = str(row["pdf_index"])

#         chunks = sentence_chunk(
#             text,
#             size=settings.CHUNK_SIZE,
#             overlap_chars=settings.OVERLAP,
#             min_chars=settings.MIN_CHUNK_CHARS,
#         )

#         if not chunks:
#             skipped_short += 1
#             continue

#         for chunk in chunks:
#             all_chunks.append(chunk)
#             metadata.append({"pdf_index": pdf_index, "chunk": chunk})

#         if i % 1000 == 0:
#             log.info("  chunked %d / %d rows …", i, len(df))

#     log.info("Total chunks: %d  (skipped %d empty docs)", len(all_chunks), skipped_short)

#     # 3. BM25 index ────────────────────────────────────────────────────────────
#     bm25 = build_bm25(all_chunks)

#     # 4. Embed ─────────────────────────────────────────────────────────────────
#     log.info("Loading embedding model: %s", settings.EMBED_MODEL)
#     model = SentenceTransformer(settings.EMBED_MODEL)

#     log.info("Encoding %d chunks (batch=%d) …", len(all_chunks), settings.EMBED_BATCH_SIZE)
#     embeddings = model.encode(
#         all_chunks,
#         batch_size=settings.EMBED_BATCH_SIZE,
#         show_progress_bar=True,
#         normalize_embeddings=True,   # L2-normalised → IP == cosine
#     ).astype("float32")
#     log.info("Embedding shape: %s", embeddings.shape)

#     # 5. Build FAISS ───────────────────────────────────────────────────────────
#     dim = embeddings.shape[1]
#     n   = len(all_chunks)

#     if n > 100_000:
#         log.info("Large corpus (%d chunks) — using IVFFlat index.", n)
#         n_lists   = min(4096, int(n ** 0.5))
#         quantizer = faiss.IndexFlatIP(dim)
#         index     = faiss.IndexIVFFlat(quantizer, dim, n_lists, faiss.METRIC_INNER_PRODUCT)
#         log.info("Training IVFFlat with %d lists …", n_lists)
#         index.train(embeddings)
#         index.nprobe = 64
#     else:
#         log.info("Using IndexFlatIP (exact search).")
#         index = faiss.IndexFlatIP(dim)

#     index.add(embeddings)
#     log.info("Vectors stored: %d", index.ntotal)

#     # 6. Save all ──────────────────────────────────────────────────────────────
#     idx_path  = settings.index_path
#     meta_path = settings.meta_path
#     bm25_path = settings.bm25_path
#     idx_path.parent.mkdir(parents=True, exist_ok=True)

#     faiss.write_index(index, str(idx_path))
#     log.info("Saved FAISS index → %s", idx_path)

#     with open(meta_path, "wb") as f:
#         pickle.dump(metadata, f)
#     log.info("Saved metadata   → %s", meta_path)

#     if bm25 is not None:
#         with open(bm25_path, "wb") as f:
#             pickle.dump({"bm25": bm25, "chunks": all_chunks}, f)
#         log.info("Saved BM25 index → %s", bm25_path)
#     else:
#         log.warning("BM25 index NOT saved (rank-bm25 not installed).")

#     log.info("Done. Unique PDFs indexed: %d", df["pdf_index"].nunique())
#     log.info("Avg chunks per PDF: %.1f", len(all_chunks) / max(df["pdf_index"].nunique(), 1))


# if __name__ == "__main__":
#     main()








"""
scripts/build_index.py
Run once (or whenever the CSV changes) to build the FAISS + BM25 index.

Improvements over v1:
  1. Sentence-aware chunking  — no mid-sentence cuts
  2. BM25 index built in parallel — enables hybrid search at query time
  3. Chunks shorter than MIN_CHUNK_CHARS are discarded
  4. IVFFlat auto-selected for large corpora (>100k chunks)
  5. CHECKPOINT SUPPORT — resume from where you left off!

Usage (from backend/ directory):
    python scripts/build_index.py

Quick dev build (2000 rows):
    set MAX_INDEX_ROWS=2000 && python scripts/build_index.py   # Windows
    MAX_INDEX_ROWS=2000 python scripts/build_index.py          # Linux/Mac

Resume after interruption:
    python scripts/build_index.py --resume

Force fresh build (ignore checkpoints):
    python scripts/build_index.py --fresh
"""

from __future__ import annotations
import argparse
import csv
import json
import logging
import pickle
import re
import sys
from pathlib import Path
from datetime import datetime

import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import settings  # noqa: E402

try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:
    csv.field_size_limit(10 ** 9)

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
log = logging.getLogger(__name__)


# ── Checkpoint paths ──────────────────────────────────────────────────────────
CHECKPOINT_DIR = Path(settings.INDEX_DIR) / "checkpoints"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
CHUNKS_CHECKPOINT = CHECKPOINT_DIR / "chunks_checkpoint.pkl"
METADATA_CHECKPOINT = CHECKPOINT_DIR / "metadata_checkpoint.pkl"
EMBEDDINGS_CHECKPOINT = CHECKPOINT_DIR / "embeddings_checkpoint.npy"
PROGRESS_CHECKPOINT = CHECKPOINT_DIR / "progress.json"


# ── Sentence-aware chunker ─────────────────────────────────────────────────────

_SENT_SPLIT = re.compile(r'(?<=[.!?])\s+')


def sentence_chunk(text: str, size: int, overlap_chars: int, min_chars: int) -> list[str]:
    """Split text into chunks that always end at sentence boundaries."""
    raw_sentences = _SENT_SPLIT.split(text.strip())
    sentences: list[str] = []
    for s in raw_sentences:
        if len(s) <= size:
            sentences.append(s)
        else:
            words = s.split()
            buf = ""
            for w in words:
                if len(buf) + len(w) + 1 <= size:
                    buf = (buf + " " + w).strip()
                else:
                    if buf:
                        sentences.append(buf)
                    buf = w
            if buf:
                sentences.append(buf)

    chunks: list[str] = []
    current = ""
    overlap_tail = ""

    for sent in sentences:
        candidate = (overlap_tail + " " + current + " " + sent).strip()
        if len(candidate) <= size:
            current = candidate
        else:
            if current and len(current) >= min_chars:
                chunks.append(current)
                overlap_tail = current[-overlap_chars:] if overlap_chars else ""
            current = (overlap_tail + " " + sent).strip()
            overlap_tail = ""

    if current and len(current) >= min_chars:
        chunks.append(current)

    return chunks


# ── BM25 helpers ──────────────────────────────────────────────────────────────

def _simple_tokenize(text: str) -> list[str]:
    """Lowercase alpha-only tokens — good enough for BM25 keyword matching."""
    return re.findall(r'[a-zA-Z]{2,}', text.lower())


def build_bm25(chunks: list[str]):
    """Build and return a BM25Okapi index over the chunk list."""
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        log.warning("rank-bm25 not installed — skipping BM25 index. Run: pip install rank-bm25")
        return None

    log.info("Tokenising %d chunks for BM25 …", len(chunks))
    tokenised = [_simple_tokenize(c) for c in chunks]
    bm25 = BM25Okapi(tokenised)
    log.info("BM25 index built.")
    return bm25


# ── Checkpoint functions ──────────────────────────────────────────────────────

def save_checkpoint(all_chunks: list[str], metadata: list[dict], embeddings: np.ndarray | None, 
                    processed_rows: int, total_rows: int, chunk_offset: int):
    """Save current progress to disk."""
    log.info("Saving checkpoint at %d chunks...", len(all_chunks))
    
    # Save chunks and metadata incrementally
    with open(CHUNKS_CHECKPOINT, "wb") as f:
        pickle.dump(all_chunks, f)
    
    with open(METADATA_CHECKPOINT, "wb") as f:
        pickle.dump(metadata, f)
    
    # Save embeddings if we have them
    if embeddings is not None and len(embeddings) > 0:
        np.save(EMBEDDINGS_CHECKPOINT, embeddings)
    
    # Save progress metadata
    progress = {
        "processed_rows": processed_rows,
        "total_rows": total_rows,
        "chunk_offset": chunk_offset,
        "num_chunks": len(all_chunks),
        "timestamp": datetime.now().isoformat(),
        "embeddings_shape": list(embeddings.shape) if embeddings is not None else None,
        "has_embeddings": embeddings is not None
    }
    with open(PROGRESS_CHECKPOINT, "w") as f:
        json.dump(progress, f, indent=2)
    
    log.info("Checkpoint saved.")


def load_checkpoint() -> tuple[list[str] | None, list[dict] | None, np.ndarray | None, dict | None]:
    """Load previous checkpoint if it exists."""
    if not PROGRESS_CHECKPOINT.exists():
        return None, None, None, None
    
    try:
        with open(PROGRESS_CHECKPOINT, "r") as f:
            progress = json.load(f)
        
        log.info(f"Found checkpoint from {progress['timestamp']}")
        log.info(f"  - {progress['num_chunks']} chunks processed")
        log.info(f"  - {progress['processed_rows']}/{progress['total_rows']} rows processed")
        
        # Load chunks and metadata
        all_chunks = None
        metadata = None
        embeddings = None
        
        if CHUNKS_CHECKPOINT.exists():
            with open(CHUNKS_CHECKPOINT, "rb") as f:
                all_chunks = pickle.load(f)
            log.info(f"  - Loaded {len(all_chunks)} chunks")
        
        if METADATA_CHECKPOINT.exists():
            with open(METADATA_CHECKPOINT, "rb") as f:
                metadata = pickle.load(f)
        
        if EMBEDDINGS_CHECKPOINT.exists() and progress.get("has_embeddings"):
            embeddings = np.load(EMBEDDINGS_CHECKPOINT)
            log.info(f"  - Loaded embeddings shape {embeddings.shape}")
        
        return all_chunks, metadata, embeddings, progress
        
    except Exception as e:
        log.warning(f"Failed to load checkpoint: {e}")
        return None, None, None, None


def clear_checkpoints():
    """Delete all checkpoint files for a fresh start."""
    log.info("Clearing checkpoints...")
    for f in [CHUNKS_CHECKPOINT, METADATA_CHECKPOINT, EMBEDDINGS_CHECKPOINT, PROGRESS_CHECKPOINT]:
        if f.exists():
            f.unlink()
            log.info(f"  Removed {f.name}")
    log.info("Checkpoints cleared.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Build FAISS + BM25 index with resume support")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    parser.add_argument("--fresh", action="store_true", help="Force fresh build (ignore checkpoints)")
    args = parser.parse_args()
    
    # Clear checkpoints if fresh build requested
    if args.fresh:
        clear_checkpoints()
    
    # ── 1. Load CSV ──────────────────────────────────────────────────────────
    csv_path = Path(settings.CSV_PATH)
    log.info("Loading CSV: %s", csv_path)
    df = pd.read_csv(
        csv_path,
        usecols=["pdf_index", "text"],
        engine="python",
        encoding="utf-8",
        on_bad_lines="skip",
    )
    log.info("Raw rows: %d", len(df))

    # Sort deterministically by numeric PDF id
    df["_num"] = (
        df["pdf_index"]
        .str.replace(r"\.pdf$", "", regex=True)
        .str.extract(r"(\d+)$")[0]
        .astype(float)
    )
    df = df.sort_values("_num").drop(columns=["_num"]).reset_index(drop=True)

    if settings.MAX_INDEX_ROWS < len(df):
        log.info("Limiting to %d rows (full: %d).", settings.MAX_INDEX_ROWS, len(df))
        df = df.head(settings.MAX_INDEX_ROWS)

    log.info("Rows to index: %d", len(df))
    total_rows = len(df)
    
    # ── 2. Try to resume from checkpoint ──────────────────────────────────────
    all_chunks: list[str] = []
    metadata: list[dict] = []
    existing_embeddings = None
    start_row = 0
    chunk_offset = 0
    
    if args.resume:
        loaded_chunks, loaded_metadata, loaded_embeddings, progress = load_checkpoint()
        if loaded_chunks is not None:
            all_chunks = loaded_chunks
            metadata = loaded_metadata if loaded_metadata is not None else []
            existing_embeddings = loaded_embeddings
            start_row = progress.get("processed_rows", 0) if progress else 0
            chunk_offset = len(all_chunks)
            log.info(f"Resuming from row {start_row} (already have {chunk_offset} chunks)")
        else:
            log.info("No valid checkpoint found. Starting fresh.")
    
    # ── 3. Sentence-aware chunking (resume from where we left off) ────────────
    skipped_short = 0
    
    for i in range(start_row, total_rows):
        row = df.iloc[i]
        text = str(row["text"]) if pd.notna(row["text"]) else ""
        pdf_index = str(row["pdf_index"])

        chunks = sentence_chunk(
            text,
            size=settings.CHUNK_SIZE,
            overlap_chars=settings.OVERLAP,
            min_chars=settings.MIN_CHUNK_CHARS,
        )

        if not chunks:
            skipped_short += 1
            continue

        for chunk in chunks:
            all_chunks.append(chunk)
            metadata.append({"pdf_index": pdf_index, "chunk": chunk})

        # Save checkpoint every 500 rows (adjust as needed)
        if (i + 1) % 500 == 0 or (i + 1) == total_rows:
            log.info("  chunked %d / %d rows (%d chunks so far)...", i + 1, total_rows, len(all_chunks))
            save_checkpoint(all_chunks, metadata, None, i + 1, total_rows, len(all_chunks) - len(chunks) if chunks else 0)

    log.info("Total chunks: %d  (skipped %d empty docs)", len(all_chunks), skipped_short)
    
    # Final checkpoint after chunking
    save_checkpoint(all_chunks, metadata, None, total_rows, total_rows, len(all_chunks))

    # ── 4. BM25 index ────────────────────────────────────────────────────────
    bm25 = build_bm25(all_chunks)

    # ── 5. Embed (with resume support) ───────────────────────────────────────
    log.info("Loading embedding model: %s", settings.EMBED_MODEL)
    model = SentenceTransformer(settings.EMBED_MODEL)
    
    # Determine how many chunks we still need to embed
    chunks_to_embed = all_chunks
    start_chunk_idx = 0
    existing_embeddings_list = []
    
    if existing_embeddings is not None and len(existing_embeddings) > 0:
        start_chunk_idx = existing_embeddings.shape[0]
        chunks_to_embed = all_chunks[start_chunk_idx:]
        existing_embeddings_list = [existing_embeddings]
        log.info(f"Resuming embedding: already have {start_chunk_idx} embeddings, need {len(chunks_to_embed)} more")
    
    if len(chunks_to_embed) > 0:
        log.info("Encoding %d chunks (batch=%d) ...", len(chunks_to_embed), settings.EMBED_BATCH_SIZE)
        
        # Process in sub-batches for better resume granularity
        SUB_BATCH_SIZE = 10000  # Save checkpoint every 10k chunks
        
        all_new_embeddings = []
        for sub_start in range(0, len(chunks_to_embed), SUB_BATCH_SIZE):
            sub_end = min(sub_start + SUB_BATCH_SIZE, len(chunks_to_embed))
            sub_batch = chunks_to_embed[sub_start:sub_end]
            
            log.info(f"  Encoding sub-batch {sub_start}-{sub_end}/{len(chunks_to_embed)}")
            sub_embeddings = model.encode(
                sub_batch,
                batch_size=settings.EMBED_BATCH_SIZE,
                show_progress_bar=True,
                normalize_embeddings=True,
            ).astype("float32")
            
            all_new_embeddings.append(sub_embeddings)
            
            # Save checkpoint after each sub-batch
            combined_embeddings = np.vstack(existing_embeddings_list + all_new_embeddings) if existing_embeddings_list or all_new_embeddings else None
            save_checkpoint(all_chunks, metadata, combined_embeddings, total_rows, total_rows, sub_end)
            log.info(f"  Checkpoint saved at {start_chunk_idx + sub_end}/{len(all_chunks)} chunks")
        
        # Combine all embeddings
        if all_new_embeddings:
            new_embeddings = np.vstack(all_new_embeddings)
            if existing_embeddings_list:
                embeddings = np.vstack(existing_embeddings_list + [new_embeddings])
            else:
                embeddings = new_embeddings
        else:
            embeddings = existing_embeddings
    else:
        embeddings = existing_embeddings
        log.info("All embeddings already computed. Skipping encoding.")
    
    log.info("Final embedding shape: %s", embeddings.shape)
    
    # Save final checkpoint with embeddings
    save_checkpoint(all_chunks, metadata, embeddings, total_rows, total_rows, len(all_chunks))

    # ── 6. Build FAISS ────────────────────────────────────────────────────────
    dim = embeddings.shape[1]
    n = len(all_chunks)

    if n > 100_000:
        log.info("Large corpus (%d chunks) — using IVFFlat index.", n)
        n_lists = min(4096, int(n ** 0.5))
        quantizer = faiss.IndexFlatIP(dim)
        index = faiss.IndexIVFFlat(quantizer, dim, n_lists, faiss.METRIC_INNER_PRODUCT)
        log.info("Training IVFFlat with %d lists …", n_lists)
        index.train(embeddings)
        index.nprobe = 64
    else:
        log.info("Using IndexFlatIP (exact search).")
        index = faiss.IndexFlatIP(dim)

    index.add(embeddings)
    log.info("Vectors stored: %d", index.ntotal)

    # ── 7. Save all ──────────────────────────────────────────────────────────
    idx_path = settings.index_path
    meta_path = settings.meta_path
    bm25_path = settings.bm25_path
    idx_path.parent.mkdir(parents=True, exist_ok=True)

    faiss.write_index(index, str(idx_path))
    log.info("Saved FAISS index → %s", idx_path)

    with open(meta_path, "wb") as f:
        pickle.dump(metadata, f)
    log.info("Saved metadata   → %s", meta_path)

    if bm25 is not None:
        with open(bm25_path, "wb") as f:
            pickle.dump({"bm25": bm25, "chunks": all_chunks}, f)
        log.info("Saved BM25 index → %s", bm25_path)
    else:
        log.warning("BM25 index NOT saved (rank-bm25 not installed).")

    log.info("Done. Unique PDFs indexed: %d", df["pdf_index"].nunique())
    log.info("Avg chunks per PDF: %.1f", len(all_chunks) / max(df["pdf_index"].nunique(), 1))
    
    # ── 8. Clean up checkpoints on success ────────────────────────────────────
    log.info("Build complete! Cleaning up checkpoints...")
    clear_checkpoints()


if __name__ == "__main__":
    main()