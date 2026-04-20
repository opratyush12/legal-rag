# LexSearch — Supreme Court Case Intelligence

AI-powered semantic search over 34,137 Supreme Court judgments.  
Search by scenario → ranked results with AI summaries → chat with any case via Groq LLM → TTS/STT voice support.

---

## Stack

| Layer     | Technology                                      |
|-----------|-------------------------------------------------|
| Frontend  | React 18 + Vite + TypeScript + Tailwind CSS     |
| Backend   | FastAPI + Uvicorn                               |
| Vectors   | FAISS (IndexFlatIP / IVFFlat for large corpora) |
| Embedding | `BAAI/bge-small-en-v1.5` (Sentence-Transformers)|
| Reranking | `cross-encoder/ms-marco-MiniLM-L-6-v2`          |
| LLM       | Groq (`llama3-70b-8192`)                        |
| TTS       | edge-tts (free Microsoft Edge neural voices)    |
| STT       | Web Speech API (browser-native, free)           |
| Storage   | Local filesystem (swap to S3 via env var)       |
| Container | Docker + Docker Compose                         |

---

## Project Structure

```
legal-rag/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py          # All settings — env-driven
│   │   │   ├── index_manager.py   # FAISS singleton
│   │   │   ├── model_loader.py    # Embed + reranker singletons
│   │   │   └── storage.py        # Local / S3 abstraction
│   │   ├── models/
│   │   │   └── schemas.py         # Pydantic request/response types
│   │   ├── routers/
│   │   │   ├── search.py          # POST /api/search
│   │   │   ├── cases.py           # GET  /api/cases/{id}/download|preview
│   │   │   ├── chat.py            # POST /api/chat
│   │   │   └── voice.py           # POST /api/voice/tts
│   │   ├── services/
│   │   │   ├── search_service.py  # FAISS → rerank → Groq summary
│   │   │   ├── groq_service.py    # LLM summaries + chat
│   │   │   └── tts_service.py     # edge-tts synthesis
│   │   └── main.py                # FastAPI app + lifespan
│   ├── scripts/
│   │   └── build_index.py         # One-time index builder
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/Layout.tsx
│   │   │   ├── search/SearchBar.tsx
│   │   │   ├── search/Hero.tsx
│   │   │   ├── cases/CaseCard.tsx
│   │   │   ├── cases/ResultsList.tsx
│   │   │   ├── chat/ChatPanel.tsx
│   │   │   └── ui/ResultsSkeleton.tsx
│   │   ├── hooks/
│   │   │   ├── useSearch.ts       # Search logic + state
│   │   │   └── useVoice.ts        # STT (Web Speech) + TTS (edge-tts)
│   │   ├── lib/api.ts             # Typed axios API client
│   │   ├── store/index.ts         # Zustand global state
│   │   ├── pages/HomePage.tsx
│   │   └── App.tsx
│   ├── Dockerfile
│   └── nginx.conf
└── docker-compose.yml
```

---

## Setup — Local Development

### Prerequisites
- Python 3.11+
- Node.js 20+
- Git

### 1. Clone and configure

```bash
git clone <your-repo>
cd legal-rag

# Copy and fill in your config
cp backend/.env.example backend/.env
```

Edit `backend/.env`:
```env
CSV_PATH=C:\Users\PratyushOjha\Documents\projectPractice\supream_court_data\supreme_court_clean_engilsh.csv
PDF_LOCAL_DIR=C:\Users\PratyushOjha\Documents\projectPractice\supream_court_data\processed_data
GROQ_API_KEY=your_groq_api_key_here
MAX_INDEX_ROWS=34137        # use 2000 for a quick dev test
```

### 2. Backend — build the index (run ONCE)

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt

# Build FAISS index (takes ~10-30 min for 34k rows on first run)
# For a quick test first: set MAX_INDEX_ROWS=2000 in .env
python scripts/build_index.py
```

You'll see progress bars. When done:
```
Saved FAISS index → ./index_store/faiss.index
Saved metadata   → ./index_store/metadata.pkl
Done. Unique PDFs indexed: 34137
```

### 3. Start the backend server

```bash
# Still inside backend/ with venv active
uvicorn app.main:app --reload --port 8000
```

Visit http://localhost:8000/docs to verify the API is live.

### 4. Start the frontend

```bash
cd ../frontend
npm install
npm run dev
```

Open http://localhost:5173 — you're live!

---

## Setup — Docker (recommended for deployment)

```bash
# Copy env file
cp backend/.env.example backend/.env
# Fill in GROQ_API_KEY and paths in backend/.env

# Build and start everything
docker-compose up --build

# On first run, build the index inside the container:
docker-compose exec backend python scripts/build_index.py
```

- Frontend: http://localhost:3000
- Backend:  http://localhost:8000
- API docs: http://localhost:8000/docs

---

## Switching to AWS S3 (when ready)

Only change these values in `.env` — zero code changes:

```env
PDF_STORAGE_BACKEND=s3
S3_BUCKET=my-supreme-court-pdfs
S3_PREFIX=processed_data/
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=ap-south-1
```

PDFs are downloaded from S3 to a local cache on first access.

---

## Improving Accuracy

The pipeline has multiple levers — all tunable via `.env`:

| Setting            | Default | Effect                                      |
|--------------------|---------|---------------------------------------------|
| `FAISS_RETRIEVE_K` | 200     | More candidates → better recall, slower     |
| `CANDIDATE_PDFS`   | 20      | More PDFs fed to reranker → better, slower  |
| `TOP_K`            | 5       | Final results shown                         |
| `CHUNK_SIZE`       | 1200    | Larger = more context per chunk             |
| `OVERLAP`          | 200     | More overlap = fewer missed passage borders |
| `EMBED_MODEL`      | bge-small | Swap to `bge-large-en-v1.5` for +3% recall |
| `RERANK_MODEL`     | MiniLM-L-6 | Swap to `ms-marco-MiniLM-L-12` for +2% |

For large corpora, the index builder automatically uses **IVFFlat** (10× faster queries) when chunk count exceeds 100k.

---

## API Reference

| Method | Endpoint                          | Description                  |
|--------|-----------------------------------|------------------------------|
| POST   | `/api/search`                     | Semantic search              |
| GET    | `/api/cases/{id}/preview`         | Case text preview            |
| GET    | `/api/cases/{id}/download`        | Download PDF                 |
| POST   | `/api/chat`                       | Chat with a case via Groq    |
| POST   | `/api/voice/tts`                  | Text → MP3 (edge-tts)        |
| GET    | `/api/voice/voices`               | List available TTS voices    |
| GET    | `/health`                         | Health + index status        |

Full interactive docs: http://localhost:8000/docs

---

## Extending the App

The architecture is intentionally loosely coupled:

- **Swap the LLM**: edit `app/services/groq_service.py` — the search and chat routers don't care which LLM is used.
- **Swap the embedding model**: change `EMBED_MODEL` in `.env` and re-run `build_index.py`.
- **Add a new storage backend**: implement `BaseStorage` in `app/core/storage.py` and register in `build_storage()`.
- **Add new routes**: create a file in `app/routers/` and include it in `app/main.py`.
- **Add auth**: drop in FastAPI middleware — all routes inherit it.
