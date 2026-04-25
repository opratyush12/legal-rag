# Legal RAG — Complete Project Documentation

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Backend Architecture](#3-backend-architecture)
4. [Frontend Architecture](#4-frontend-architecture)
5. [ML / Model Architecture](#5-ml--model-architecture)
6. [Search Pipeline — Step by Step](#6-search-pipeline--step-by-step)
7. [Index Building Process](#7-index-building-process)
8. [API Reference](#8-api-reference)
9. [AWS Deployment Architecture](#9-aws-deployment-architecture)
10. [Infrastructure as Code (Terraform)](#10-infrastructure-as-code-terraform)
11. [CI/CD & Deployment Flow](#11-cicd--deployment-flow)
12. [Cost Breakdown](#12-cost-breakdown)
13. [Configuration Reference](#13-configuration-reference)
14. [Local Development](#14-local-development)

---

## 1. Project Overview

**Legal RAG** (Retrieval-Augmented Generation) is a full-stack AI-powered legal research platform built for Indian law. It enables semantic search over **~12,000 Supreme Court of India judgments** (301,943 indexed text chunks), provides AI-generated relevance summaries, case-specific chat, a general legal assistant, text-to-speech, and PDF upload analysis.

### Key Capabilities

| Feature | Description |
|---------|-------------|
| **Semantic Search** | FAISS vector similarity search across 301,943 text chunks |
| **Query Expansion** | Groq LLM generates legal variants of user queries |
| **Hybrid Search** | Optional BM25 keyword search blended with semantic scores |
| **Cross-Encoder Reranking** | ms-marco reranker for precise final ranking |
| **AI Summaries** | Per-result relevance explanation via Groq LLM |
| **Case Chat** | Multi-turn conversation grounded in a specific case's text |
| **Legal Assistant** | General Indian constitutional law Q&A (VakilAI) |
| **Voice (TTS)** | Hindi & English text-to-speech via Edge neural voices |
| **PDF Upload** | Upload any PDF, extract text, search against the index |

### Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Zustand |
| **Backend** | Python 3.11, FastAPI, Uvicorn |
| **Vector DB** | FAISS (Facebook AI Similarity Search) |
| **Embeddings** | `BAAI/bge-small-en-v1.5` (384-dim, sentence-transformers) |
| **Reranker** | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| **LLM** | Groq Cloud — `llama-3.3-70b-versatile` with fallback chain |
| **TTS** | Microsoft Edge neural voices (`edge-tts`) |
| **Infra** | AWS ECS Fargate, ALB, S3, ECR, Secrets Manager, Terraform |
| **Containerization** | Docker, Docker Compose |

---

## 2. System Architecture

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                             │
│  React SPA (Vite + TypeScript + Tailwind)                        │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌────────────────────┐ │
│  │ SearchBar│ │ CaseCards│ │ ChatPanel │ │ AssistantPanel     │ │
│  └────┬─────┘ └────┬─────┘ └─────┬─────┘ └────────┬───────────┘ │
│       │             │             │                │             │
│       └─────────────┴─────────────┴────────────────┘             │
│                           │  Axios HTTP                          │
└───────────────────────────┼──────────────────────────────────────┘
                            │
                     ┌──────▼──────┐
                     │    Nginx    │  ← Static files + /api/ proxy
                     │  (port 80)  │
                     └──────┬──────┘
                            │ proxy_pass /api/*
                     ┌──────▼──────┐
                     │   FastAPI   │  ← Uvicorn ASGI server (port 8000)
                     │   Backend   │
                     └──┬───┬───┬──┘
                        │   │   │
            ┌───────────┘   │   └───────────┐
            ▼               ▼               ▼
     ┌──────────┐   ┌──────────┐   ┌──────────────┐
     │  FAISS   │   │  Groq    │   │  Edge TTS    │
     │  Index   │   │  Cloud   │   │  (Microsoft) │
     │ 301,943  │   │  LLM API │   │              │
     │ vectors  │   │          │   │              │
     └──────────┘   └──────────┘   └──────────────┘
```

### Data Flow — Search Request

```
User Query
    │
    ▼
[Query Expansion] ─── Groq LLM generates 3 legal variants
    │
    ▼
[FAISS Retrieval] ─── Encode query → search 301,943 vectors → top-200 chunks
    │
    ▼
[BM25 Retrieval] ──── Keyword match on tokenized chunks (optional)
    │
    ▼
[Score Aggregation] ── Weighted sum per PDF + chunk-count boost
    │
    ▼
[Top-20 Candidates] ── Preliminary ranking by aggregated score
    │
    ▼
[CrossEncoder Rerank] ─ ms-marco model scores (query, chunk_text) pairs
    │
    ▼
[Top-5 Results] ────── Final ranked results
    │
    ▼
[Groq Summaries] ───── Per-result AI relevance explanation
    │
    ▼
Response to Frontend
```

---

## 3. Backend Architecture

### Directory Structure

```
backend/
├── Dockerfile              # Multi-layer Docker image (Python 3.11-slim)
├── entrypoint.sh           # S3 sync → uvicorn startup
├── requirements.txt        # Python dependencies
├── pytest.ini              # Test configuration
├── app/
│   ├── main.py             # FastAPI app factory + lifespan (index loading)
│   ├── core/
│   │   ├── config.py       # Pydantic settings (env-driven configuration)
│   │   ├── index_manager.py # Singleton: FAISS index + metadata + BM25
│   │   ├── model_loader.py  # Lazy-loaded embedding + reranker models
│   │   └── storage.py       # Storage abstraction (Local ↔ S3)
│   ├── models/
│   │   └── schemas.py       # Pydantic request/response schemas
│   ├── routers/
│   │   ├── search.py        # POST /api/search
│   │   ├── cases.py         # GET /api/cases/{id}/download, /preview
│   │   ├── chat.py          # POST /api/chat (case-specific)
│   │   ├── assistant.py     # POST /api/assistant (general legal Q&A)
│   │   ├── voice.py         # POST /api/voice/tts, GET /api/voice/voices
│   │   └── upload.py        # POST /api/upload/pdf
│   └── services/
│       ├── search_service.py # 7-stage retrieval pipeline
│       ├── groq_service.py   # Groq LLM wrapper with fallback chain
│       └── tts_service.py    # Edge TTS with voice fallback chain
├── scripts/
│   ├── build_index.py        # Offline: CSV → FAISS + BM25 index builder
│   ├── s3_sync_index.py      # Runtime: download index from S3 at startup
│   └── get_indexed_pdfs.py   # Utility to list indexed PDFs
├── index_store/              # Local FAISS index files
└── tests/                    # 107 pytest tests (unit + integration)
```

### Core Components

#### `config.py` — Centralized Configuration

All settings are **environment-driven** using Pydantic `BaseSettings`. Reads from `.env` file or environment variables. Key groups:

- **Data**: CSV path, PDF storage backend (local/S3), S3 credentials
- **Index**: FAISS index directory, file names, max rows, chunking params
- **Models**: Embedding model name, reranker model name, batch size
- **Search**: FAISS retrieve K, candidate PDFs, top-K, hybrid weights, reranking params
- **Groq**: API key, model name, fallback models, temperature, token limits
- **TTS**: Default voice selection

#### `index_manager.py` — Singleton Index Manager

Loaded **once at FastAPI startup** via the `lifespan` context manager. Holds:

- `_index` — FAISS index object (301,943 vectors, 384 dimensions)
- `_metadata` — List of dicts per chunk: `{pdf_index, chunk, ...}`
- `_bm25` — Optional BM25Okapi object for keyword search
- `_bm25_chunks` — Corresponding text chunks for BM25

The `USE_BM25` setting gates BM25 loading. When disabled, the 598 MB pickle file is skipped entirely (both download from S3 and in-memory loading).

#### `model_loader.py` — Lazy Model Loading

Uses `@lru_cache(maxsize=1)` for both models — loaded exactly once per process on first use:

- **Embedding model**: `BAAI/bge-small-en-v1.5` — 384-dimensional dense vectors, ~33M parameters
- **Reranker**: `cross-encoder/ms-marco-MiniLM-L-6-v2` — cross-attention model for precise relevance scoring

#### `storage.py` — Storage Abstraction

Pluggable backend with two implementations:

| Backend | Config Value | Description |
|---------|-------------|-------------|
| `LocalStorage` | `local` | Reads PDFs from mounted directory. Path traversal protection. |
| `S3Storage` | `s3` | Downloads from S3 to `/tmp/pdf_cache/` on first access. Cached locally. |

Selected by `PDF_STORAGE_BACKEND` env var. Both implement `get_pdf_path()` and `exists()`.

---

## 4. Frontend Architecture

### Directory Structure

```
frontend/
├── Dockerfile          # Multi-stage: Node build → Nginx serve
├── nginx.conf          # Reverse proxy + security headers + SPA routing
├── package.json        # React 18 + Vite + Tailwind
├── src/
│   ├── App.tsx          # Router + global ChatPanel overlay
│   ├── main.tsx         # React entry point
│   ├── index.css        # Tailwind base styles
│   ├── components/
│   │   ├── search/      # Hero.tsx, SearchBar.tsx
│   │   ├── cases/       # CaseCard.tsx, ResultsList.tsx
│   │   ├── chat/        # ChatPanel.tsx, AssistantPanel.tsx
│   │   ├── layout/      # Layout.tsx
│   │   └── ui/          # ResultsSkeleton.tsx
│   ├── hooks/
│   │   ├── useSearch.ts  # Search state management hook
│   │   └── useVoice.ts   # TTS playback hook
│   ├── lib/
│   │   ├── api.ts        # Typed Axios client (mirrors backend schemas)
│   │   └── textUtils.ts  # Text formatting utilities
│   ├── pages/
│   │   └── HomePage.tsx   # Main search page
│   └── store/
│       ├── index.ts       # Store exports
│       └── store.ts       # Zustand stores (search results, active case)
```

### Nginx Configuration

The frontend Nginx server handles:

- **Static file serving** with aggressive caching (1 year for assets)
- **SPA routing** — all unknown routes fall back to `index.html`
- **API reverse proxy** — `/api/*` requests proxied to backend on port 8000
- **Rate limiting** — 10 requests/sec per IP on API endpoints (burst 20)
- **Security headers**: X-Frame-Options, CSP, HSTS, X-Content-Type-Options, Permissions-Policy
- **Gzip compression** for text-based assets

---

## 5. ML / Model Architecture

### 5.1 Embedding Model — `BAAI/bge-small-en-v1.5`

| Property | Value |
|----------|-------|
| **Architecture** | BERT-based bi-encoder |
| **Parameters** | ~33 million |
| **Dimensions** | 384 |
| **Max Sequence Length** | 512 tokens |
| **Training** | Contrastive learning on large-scale text pairs |
| **Normalization** | L2-normalized (unit vectors) |

**Why this model?**
- Small enough to run on CPU (no GPU required for inference)
- Top-tier performance on MTEB benchmark for its size class
- L2-normalized embeddings enable efficient cosine similarity via inner product
- 384 dimensions = good balance of quality vs. index size

**How it's used:**
1. **Index time**: Each text chunk → 384-dim vector, stored in FAISS
2. **Query time**: User query → 384-dim vector, searched against FAISS index

### 5.2 Reranker — `cross-encoder/ms-marco-MiniLM-L-6-v2`

| Property | Value |
|----------|-------|
| **Architecture** | Cross-encoder (full attention between query and document) |
| **Parameters** | ~22 million |
| **Input** | (query, document) pair → single relevance score |
| **Training** | MS MARCO passage ranking dataset |
| **Score Range** | Typically -10 to +10 |

**Why a reranker?**
Bi-encoders (like bge-small) encode query and document independently — fast but lose cross-attention. Cross-encoders process them jointly, capturing fine-grained interactions. This two-stage approach gives the speed of FAISS retrieval with the accuracy of cross-attention reranking.

**How it's used:**
After FAISS retrieves top-200 chunks and they're aggregated to top-20 candidate PDFs, the reranker scores each `(query, top_chunks_per_pdf)` pair. Final ranking is by reranker score.

### 5.3 FAISS Index

| Property | Value |
|----------|-------|
| **Index Type** | `IndexFlatIP` (inner product) |
| **Vectors** | 301,943 |
| **Dimensions** | 384 |
| **Index Size on Disk** | ~445 MB |
| **Search Type** | Exact nearest neighbor (brute force) |
| **Similarity** | Cosine similarity (via IP of L2-normalized vectors) |

Since embeddings are L2-normalized, inner product equals cosine similarity. `IndexFlatIP` provides exact (non-approximate) search. For 301K vectors at 384 dims, brute-force search is fast enough (< 100ms).

### 5.4 BM25 Index (Optional)

| Property | Value |
|----------|-------|
| **Algorithm** | BM25Okapi (rank-bm25 library) |
| **Chunks Indexed** | 301,943 |
| **Tokenization** | Simple alpha-only regex: `[a-zA-Z]{2,}` lowercased |
| **Index Size on Disk** | ~598 MB (bm25.pkl) |
| **In-Memory Size** | ~2-3 GB (sparse term-frequency arrays) |
| **Status** | Disabled in production (USE_BM25=false) due to memory constraints |

BM25 provides keyword-based retrieval that complements semantic search. When enabled, scores are blended:
- `final_score = semantic_score × 0.65 + bm25_score × 0.35`

Currently disabled in AWS deployment because the BM25 pickle expands to ~3 GB in RAM, exceeding the Fargate task's 2 GB memory limit.

### 5.5 Groq LLM — `llama-3.3-70b-versatile`

| Property | Value |
|----------|-------|
| **Provider** | Groq Cloud (inference API) |
| **Primary Model** | `llama-3.3-70b-versatile` |
| **Fallback Chain** | `llama-3.1-8b-instant` → `gemma2-9b-it` |
| **Max Tokens** | 1024 (chat), 350 (summaries) |
| **Temperature** | 0.2 (summaries), 0.3 (chat), 0.4 (assistant) |

**Used for three tasks:**

1. **Query Expansion**: Generate 3 legal variants of the user's search query
   - Input: `"fundamental rights violation"` 
   - Output: `["Article 14 rights", "Basic human rights India", "Part III constitutional rights"]`

2. **Relevance Summaries**: Per-result explanation of why a case is relevant
   - Receives: query + top chunks from the matched case
   - Returns: 2-3 sentence legal summary with article/section citations

3. **Chat / Assistant**: Multi-turn conversation with legal context
   - **Case Chat** (`/api/chat`): Grounded in a specific case's full text
   - **Legal Assistant** (`/api/assistant`): General Indian constitutional law Q&A
   - System prompt includes full Indian Constitution reference (key articles, amendments, landmark cases)

The Groq wrapper automatically handles model fallback — if the primary model is decommissioned or errors, it transparently switches to the next model in the chain.

### 5.6 Edge TTS — Microsoft Neural Voices

| Property | Value |
|----------|-------|
| **Library** | `edge-tts` (free, uses Microsoft Edge's TTS API) |
| **Default Voice** | `hi-IN-SwaraNeural` (Hindi, Female) |
| **Fallback Chain** | Hindi Female → Hindi Male → Indian English → US English |
| **Output Format** | MP3 audio bytes |

---

## 6. Search Pipeline — Step by Step

The search pipeline in `search_service.py` is a 7-stage process:

### Stage 1: Query Expansion (Groq LLM)

```
Input:  "can police arrest without warrant"
Output: ["can police arrest without warrant",
         "Section 41 CrPC cognizable offence arrest",
         "warrantless arrest procedure India",
         "preventive detention Article 22 safeguards"]
```

The LLM generates N legal reformulations, adding statutory section numbers, legal terminology, and constitutional article references. This dramatically improves recall.

### Stage 2: FAISS Semantic Retrieval

For **each** query variant (original + expanded):
1. Encode query → 384-dim vector using `bge-small-en-v1.5`
2. Search FAISS index → retrieve top-200 nearest chunks
3. Each chunk hit contributes `cosine_similarity × 0.65` to its parent PDF's score

### Stage 3: BM25 Keyword Retrieval (Optional)

For each query variant:
1. Tokenize query → `["police", "arrest", "without", "warrant"]`
2. BM25Okapi scores all 301,943 chunks → top-200
3. Each hit contributes `normalized_bm25_score × 0.35` to its parent PDF's score

Score normalization: `normalized = raw_score / (raw_score + 1)` → squeezes to (0, 1).

### Stage 4: Score Aggregation

Per PDF, accumulate:
- Sum of weighted semantic scores across all query variants
- Sum of weighted BM25 scores (if enabled)
- **Chunk-count boost**: `+0.15` per additional matching chunk beyond the first

This rewards cases with broad coverage across the query topic.

### Stage 5: Preliminary Ranking → Top-20 Candidates

Sort all PDFs by aggregated score. Take top-20 (`CANDIDATE_PDFS` setting).

### Stage 6: CrossEncoder Reranking

For each of the 20 candidates:
1. Take the top-4 chunks (`RERANK_CHUNKS`) concatenated
2. Score the pair `(original_query, concatenated_chunks)` with ms-marco cross-encoder
3. Sort by cross-encoder score → take top-5 (`TOP_K`)

Cross-encoder scores typically range -10 to +10. Mapped to confidence:
- **High**: score ≥ 4.0
- **Medium**: score ≥ 0.0
- **Low**: score < 0.0

### Stage 7: Groq AI Summaries

For each of the final 5 results, the Groq LLM generates a relevance explanation:
- Why this case is relevant to the user's query
- Key legal principles and article citations
- How the case's ratio decidendi applies

---

## 7. Index Building Process

The `scripts/build_index.py` script (run offline) processes the source CSV:

### Input
- CSV file: `supreme_court_clean_english.csv`
- Columns: `pdf_index` (e.g., `10116.pdf`), `text` (full judgment text)
- ~12,000 rows (configurable via `MAX_INDEX_ROWS`)

### Processing Steps

1. **Load & Sort**: Read CSV, sort by numeric PDF index deterministically
2. **Sentence-Aware Chunking**: 
   - Split text on sentence boundaries (`. ! ?`)
   - Pack sentences into chunks of ~1,200 characters with 200-char overlap
   - Discard chunks shorter than 100 characters
   - This preserves sentence integrity — no mid-sentence cuts
3. **Embed**: Batch-encode all chunks using `bge-small-en-v1.5` (batch size 128)
4. **Build FAISS Index**: Create `IndexFlatIP`, add all normalized vectors
5. **Build BM25 Index**: Tokenize all chunks, build `BM25Okapi`
6. **Save**:
   - `faiss.index` (~445 MB) — vector index
   - `metadata.pkl` (~314 MB) — chunk text + PDF mapping
   - `bm25.pkl` (~598 MB) — BM25 sparse index
   - `indexed_pdfs.csv` / `indexed_pdfs.txt` — list of indexed PDFs

### Output Statistics

| File | Size | Contents |
|------|------|----------|
| `faiss.index` | 445 MB | 301,943 × 384-dim float32 vectors |
| `metadata.pkl` | 314 MB | 301,943 chunk records with text + PDF mapping |
| `bm25.pkl` | 598 MB | BM25Okapi sparse term-frequency arrays |
| `indexed_pdfs.csv` | 0.12 MB | List of all indexed PDF identifiers |
| **Total** | **~1.35 GB** | |

---

## 8. API Reference

### `POST /api/search` — Semantic Case Search

**Request:**
```json
{
  "query": "fundamental rights violation by police",
  "top_k": 5
}
```

**Response:**
```json
{
  "query": "fundamental rights violation by police",
  "expanded_queries": [
    "fundamental rights violation by police",
    "Article 21 police brutality",
    "custodial violence constitutional remedy",
    "Section 197 CrPC sanction prosecution"
  ],
  "results": [
    {
      "pdf_index": "10116.pdf",
      "relevance_score": 3.65,
      "confidence": "Medium",
      "summary": "This case discusses the conflict between fundamental rights under Article 21...",
      "snippet": "available to any other human being...",
      "available": false,
      "chunk_hits": 16
    }
  ],
  "total_candidates_evaluated": 20
}
```

### `POST /api/chat` — Case-Specific Chat

**Request:**
```json
{
  "pdf_index": "10116.pdf",
  "messages": [
    {"role": "user", "content": "What was the main legal issue in this case?"}
  ]
}
```

### `POST /api/assistant` — General Legal Assistant

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "Explain Article 21 and its expanded interpretation"}
  ]
}
```

### `POST /api/voice/tts` — Text-to-Speech

**Request:**
```json
{
  "text": "Article 21 guarantees the right to life and personal liberty",
  "voice": "hi-IN-SwaraNeural"
}
```
**Response:** MP3 audio bytes (`audio/mpeg`)

### `GET /api/cases/{pdf_index}/preview` — Case Text Preview

Returns first 4,000 characters of the indexed case text.

### `GET /api/cases/{pdf_index}/download` — PDF Download

Returns the original PDF file if available in storage.

### `POST /api/upload/pdf` — PDF Upload & Search

Upload a PDF file. The backend extracts text (pdfplumber → PyMuPDF fallback), truncates to a query, and runs it through the search pipeline. The PDF is NOT added to the index.

### `GET /health` — Health Check

```json
{
  "status": "ok",
  "index_loaded": true,
  "model": "BAAI/bge-small-en-v1.5"
}
```

---

## 9. AWS Deployment Architecture

### Architecture Diagram

```
                              ┌─────────────────────────┐
                              │       Internet           │
                              └────────────┬────────────┘
                                           │
                              ┌────────────▼────────────┐
                              │    Application Load      │
                              │    Balancer (ALB)        │
                              │    Port 80 (HTTP)        │
                              └──────┬─────────┬────────┘
                                     │         │
                    Path: /api/*     │         │  Path: /* (default)
                    Path: /health    │         │
                                     │         │
                              ┌──────▼───┐  ┌──▼─────────┐
                              │ Backend  │  │ Frontend   │
                              │ Target   │  │ Target     │
                              │ Group    │  │ Group      │
                              │ :8000    │  │ :80        │
                              └──────┬───┘  └──┬─────────┘
                                     │         │
                    ┌────────────────┐│         │┌────────────────┐
                    │  ECS Fargate   ││         ││  ECS Fargate   │
                    │  Backend Task  │◄         ►│  Frontend Task │
                    │                │           │                │
                    │  1 vCPU        │           │  0.25 vCPU     │
                    │  2 GB RAM      │           │  512 MB RAM    │
                    │                │           │                │
                    │  Python 3.11   │           │  Nginx 1.27    │
                    │  FastAPI       │           │  React SPA     │
                    │  Uvicorn       │           │                │
                    └───────┬────────┘           └────────────────┘
                            │
                   ┌────────▼────────┐
                   │   S3 Bucket     │
                   │  (Index Store)  │
                   │                 │
                   │  faiss.index    │
                   │  metadata.pkl   │
                   │  bm25.pkl       │
                   └─────────────────┘
```

### AWS Resources

| Resource | Service | Details |
|----------|---------|---------|
| **VPC** | VPC | `10.0.0.0/16`, 2 public subnets, no NAT gateway |
| **ALB** | Elastic Load Balancing | Path-based routing: `/api/*` → backend, `/*` → frontend |
| **Backend** | ECS Fargate | 1 vCPU, 2 GB RAM, 1 task, public subnet |
| **Frontend** | ECS Fargate | 0.25 vCPU, 512 MB RAM, 1 task, public subnet |
| **ECR** | Elastic Container Registry | 2 repos (backend, frontend), lifecycle: keep last 5 images |
| **S3** | S3 | Index files (1.35 GB), versioning enabled, AES-256 encryption |
| **EFS** | Elastic File System | Provisioned (currently unused, kept for future use) |
| **Secrets** | Secrets Manager | GROQ_API_KEY stored securely, injected into task env |
| **Logs** | CloudWatch | 14-day retention, log groups per service |
| **IAM** | IAM | Execution role (ECR + logs + secrets), task role (S3 access) |

### Network Architecture

- **No NAT Gateway** — Fargate tasks run in public subnets with `assign_public_ip = true`. This saves ~$32/mo (NAT gateway cost).
- **Security Groups**: 
  - ALB SG: Inbound 80/443 from internet
  - Backend SG: Inbound 8000 from ALB + frontend SGs only
  - Frontend SG: Inbound 80 from ALB SG only
  - EFS SG: Inbound NFS (2049) from backend SG only
- All egress allowed (needed for S3, Groq API, ECR, etc.)

### Container Startup Flow (Backend)

```
Container Starts
    │
    ▼
entrypoint.sh
    │
    ├── python -m scripts.s3_sync_index
    │       │
    │       ├── Check USE_BM25 env var
    │       │       → false: skip bm25.pkl download (saves 598 MB)
    │       │
    │       ├── Download faiss.index (445 MB) from S3
    │       ├── Download metadata.pkl (314 MB) from S3
    │       ├── Download indexed_pdfs.csv from S3
    │       └── Download indexed_pdfs.txt from S3
    │       │
    │       └── Skip if file already exists with matching size
    │
    ▼
exec uvicorn app.main:app
    │
    ├── FastAPI lifespan: IndexManager.load()
    │       ├── Read faiss.index → FAISS index (301,943 vectors)
    │       ├── Read metadata.pkl → 301,943 chunk records
    │       └── BM25 disabled → skip
    │
    ├── Lazy-load models on first request:
    │       ├── bge-small-en-v1.5 (embedding)
    │       └── ms-marco-MiniLM-L-6-v2 (reranker)
    │
    └── Ready to serve on port 8000
```

Total startup time: ~30-40 seconds (S3 download ~15s + index loading ~15s).

---

## 10. Infrastructure as Code (Terraform)

### File Structure

```
infra/terraform/
├── main.tf                  # All resources (VPC, ALB, ECS, ECR, EFS, S3, IAM)
├── variables.tf             # Input variables with defaults
├── outputs.tf               # Output values (ALB URL, ECR repos, etc.)
├── terraform.tfvars         # Environment-specific values
└── terraform.tfvars.example # Template for new environments
```

### Key Terraform Resources

| Resource | Type | Purpose |
|----------|------|---------|
| `aws_vpc.main` | VPC | Isolated network for all resources |
| `aws_subnet.public[*]` | Subnets | 2 public subnets in different AZs (ALB requirement) |
| `aws_lb.main` | ALB | Load balancer with path-based routing |
| `aws_ecs_cluster.main` | ECS Cluster | Container orchestration cluster |
| `aws_ecs_task_definition.backend` | Task Def | Backend container spec (image, CPU, memory, env) |
| `aws_ecs_task_definition.frontend` | Task Def | Frontend container spec |
| `aws_ecs_service.backend` | ECS Service | Desired count, networking, LB attachment |
| `aws_ecs_service.frontend` | ECS Service | Frontend service config |
| `aws_ecr_repository.backend` | ECR | Docker image registry for backend |
| `aws_ecr_repository.frontend` | ECR | Docker image registry for frontend |
| `aws_s3_bucket.pdfs` | S3 | Index files + PDF archive |
| `aws_secretsmanager_secret.groq` | Secrets | GROQ_API_KEY secure storage |
| `aws_iam_openid_connect_provider.github` | OIDC | GitHub Actions authentication (no long-lived keys) |

### IAM Roles

| Role | Purpose | Permissions |
|------|---------|-------------|
| **ecs-execution** | Pull images, write logs, read secrets | `AmazonECSTaskExecutionRolePolicy` + Secrets Manager read |
| **ecs-task** | Runtime S3 access | `s3:GetObject`, `s3:ListBucket`, `s3:HeadObject` on index bucket |
| **github-actions** | CI/CD deployment | ECR push, ECS service update, IAM PassRole |

---

## 11. CI/CD & Deployment Flow

### GitHub Actions OIDC Authentication

Instead of long-lived AWS access keys, the project uses **OIDC federation**:

```
GitHub Actions  →  AssumeRoleWithWebIdentity  →  AWS IAM Role
                   (OIDC token from GitHub)       (scoped to repo:main)
```

Only the `main` branch of the configured repository can assume the deployment role.

### Deployment Process (Manual)

Current deployment is done manually via these steps:

```bash
# 1. Build Docker image
docker build -t legal-rag-backend:latest ./backend

# 2. Authenticate with ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com

# 3. Tag and push
docker tag legal-rag-backend:latest <account>.dkr.ecr.us-east-1.amazonaws.com/legal-rag-backend:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/legal-rag-backend:latest

# 4. Apply Terraform (updates task definition)
cd infra/terraform && terraform apply -auto-approve

# 5. Force new deployment (picks up new image)
aws ecs update-service --cluster legal-rag --service legal-rag-backend --task-definition legal-rag-backend:<revision> --force-new-deployment
```

### Health Checks

| Level | Endpoint | Interval | Details |
|-------|----------|----------|---------|
| **Docker** | `curl -f http://localhost:8000/health` | 30s | Start period: 120s (for model loading) |
| **ECS Task** | Same as Docker healthcheck | 30s | Start period: 180s |
| **ALB Target Group** | `GET /health` → HTTP 200 | 30s | Healthy threshold: 2, Unhealthy: 3 |

---

## 12. Cost Breakdown

### Monthly AWS Cost Estimate

| Resource | Specification | Est. Cost/Month |
|----------|---------------|-----------------|
| Fargate Backend | 1 vCPU, 2 GB RAM, 1 task, 24/7 | ~$14.25 |
| Fargate Frontend | 0.25 vCPU, 0.5 GB RAM, 1 task, 24/7 | ~$4.64 |
| ALB | 1 load balancer, low traffic | ~$3.60 |
| S3 | ~1.35 GB storage + minimal requests | ~$0.03 |
| ECR | 2 repos, < 2 GB total | Free tier |
| CloudWatch Logs | 14-day retention, minimal volume | ~$0.50 |
| Secrets Manager | 1 secret | ~$0.40 |
| **Total** | | **~$23.42/mo** |

### Cost Optimization Decisions

1. **No NAT Gateway**: Tasks in public subnets with public IPs. Saves ~$32/mo.
2. **No BM25**: Disabled to keep backend at 2 GB RAM (vs 4+ GB). Saves ~$14/mo.
3. **Container Insights Disabled**: Saves ~$3/mo.
4. **ECR Lifecycle Policy**: Keep only last 5 images — stays in free tier.
5. **S3 instead of EFS for Index**: Download once at startup. EFS costs $0.30/GB/mo + throughput charges.

---

## 13. Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | (required) | Groq Cloud API key |
| `INDEX_DIR` | `./index_store` | Path to FAISS index files |
| `PDF_STORAGE_BACKEND` | `local` | `local` or `s3` |
| `PDF_LOCAL_DIR` | `/data/pdfs` | Local PDF directory path |
| `EMBED_MODEL` | `BAAI/bge-small-en-v1.5` | HuggingFace embedding model |
| `RERANK_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Reranker model |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Primary Groq LLM |
| `USE_BM25` | `true` | Enable/disable BM25 hybrid search |
| `USE_QUERY_EXPANSION` | `true` | Enable/disable Groq query expansion |
| `FAISS_RETRIEVE_K` | `200` | Chunks per FAISS query |
| `CANDIDATE_PDFS` | `20` | PDFs sent to reranker |
| `TOP_K` | `5` | Final results returned |
| `SEMANTIC_WEIGHT` | `0.65` | FAISS score weight in hybrid |
| `BM25_WEIGHT` | `0.35` | BM25 score weight in hybrid |
| `CORS_ORIGINS` | `[]` | Allowed CORS origins |
| `UVICORN_WORKERS` | `1` | Uvicorn worker processes |
| `INDEX_S3_BUCKET` | (empty) | S3 bucket for index sync at startup |
| `INDEX_S3_PREFIX` | `index_store/` | S3 key prefix for index files |
| `TTS_VOICE` | `hi-IN-SwaraNeural` | Default TTS voice |

---

## 14. Local Development

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for running without Docker)
- Node.js 20+ (for frontend development)
- Groq API key (free at https://console.groq.com)

### Quick Start with Docker Compose

```bash
# 1. Clone the repository
git clone https://github.com/opratyush12/legal-rag.git
cd legal-rag

# 2. Create backend .env file
cp backend/.env.example backend/.env
# Edit backend/.env and add your GROQ_API_KEY

# 3. Ensure PDF directory exists
mkdir -p pdfs

# 4. Start everything
docker compose up -d

# 5. Access the app
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000/health
```

### Running Without Docker

```bash
# Backend
cd backend
pip install -r requirements.txt
python scripts/build_index.py     # Build FAISS index (run once)
uvicorn app.main:app --reload     # Start API server

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                        # Vite dev server at http://localhost:5173
```

### Running Tests

```bash
cd backend
pytest                             # Run all 107 tests
pytest -v                          # Verbose output
pytest tests/test_services/        # Run specific test directory
```

---

*Last updated: April 2026*
