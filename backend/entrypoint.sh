#!/bin/sh
# entrypoint.sh — download index from S3, then start uvicorn
set -e

echo "=== S3 index sync ==="
python -m scripts.s3_sync_index || echo "WARN: S3 sync failed or skipped — starting without index."

echo "=== Starting uvicorn ==="
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers "${UVICORN_WORKERS:-1}" \
  --timeout-keep-alive "${UVICORN_TIMEOUT_KEEP_ALIVE:-30}"
