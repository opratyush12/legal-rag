# ── Backend Dockerfile ──────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# System deps (FAISS needs libgomp; edge-tts needs network at runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/

# Index store volume mount point
RUN mkdir -p /app/index_store

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
