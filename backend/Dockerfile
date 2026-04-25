# ── Backend Dockerfile ──────────────────────────────────────────────────────
FROM python:3.11-slim AS base

WORKDIR /app

# System deps (FAISS needs libgomp; curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY entrypoint.sh ./entrypoint.sh

# Index store + data directory
RUN mkdir -p /app/index_store /data/index_store

# ── Security: run as non-root ──────────────────────────────────────────────
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser \
    && chown -R appuser:appuser /app /data
USER appuser

EXPOSE 8000

ENV UVICORN_WORKERS=1
ENV UVICORN_TIMEOUT_KEEP_ALIVE=30
ENV PORT=8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD ["curl", "-f", "http://localhost:8000/health"]

ENTRYPOINT ["sh", "entrypoint.sh"]
