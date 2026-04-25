"""
scripts/s3_sync_index.py
Download FAISS index files from S3 to local disk at container startup.
Skips files that already exist with matching size.

Env vars:
  INDEX_S3_BUCKET  – S3 bucket name  (required)
  INDEX_S3_PREFIX  – key prefix       (default: "index_store/")
  INDEX_DIR        – local directory  (default: "/data/index_store")
"""

import os
import logging
import boto3
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BUCKET = os.environ.get("INDEX_S3_BUCKET", "")
PREFIX = os.environ.get("INDEX_S3_PREFIX", "index_store/")
LOCAL_DIR = Path(os.environ.get("INDEX_DIR", "/data/index_store"))
USE_BM25 = os.environ.get("USE_BM25", "true").lower() in ("true", "1", "yes")

# Skip bm25.pkl when USE_BM25 is disabled — it's 598 MB and expands to ~3 GB in RAM
_ALL_FILES = ["faiss.index", "metadata.pkl", "bm25.pkl", "indexed_pdfs.csv", "indexed_pdfs.txt"]
INDEX_FILES = _ALL_FILES if USE_BM25 else [f for f in _ALL_FILES if f != "bm25.pkl"]


def sync() -> bool:
    if not BUCKET:
        logger.warning("INDEX_S3_BUCKET not set — skipping S3 index sync.")
        return False

    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    s3 = boto3.client("s3")

    for fname in INDEX_FILES:
        key = f"{PREFIX}{fname}"
        dest = LOCAL_DIR / fname

        # Check if file already exists with correct size
        try:
            head = s3.head_object(Bucket=BUCKET, Key=key)
            remote_size = head["ContentLength"]
        except s3.exceptions.ClientError:
            logger.warning("S3 key not found: s3://%s/%s — skipping.", BUCKET, key)
            continue

        if dest.exists() and dest.stat().st_size == remote_size:
            logger.info("Already up-to-date: %s (%d bytes)", fname, remote_size)
            continue

        logger.info("Downloading s3://%s/%s → %s (%d bytes) …", BUCKET, key, dest, remote_size)
        s3.download_file(BUCKET, key, str(dest))
        logger.info("Done: %s", fname)

    logger.info("S3 index sync complete.")
    return True


if __name__ == "__main__":
    sync()
