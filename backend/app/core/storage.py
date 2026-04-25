"""
app/core/storage.py
Storage abstraction — swap local ↔ S3 via PDF_STORAGE_BACKEND env var.
No other code needs to know which backend is active.
"""

from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Base interface ─────────────────────────────────────────────────────────────

class BaseStorage(ABC):
    """All storage backends must implement these two methods."""

    @abstractmethod
    def get_pdf_path(self, pdf_index: str) -> Optional[Path]:
        """Return a local Path to the PDF (downloading from remote if needed)."""

    @abstractmethod
    def exists(self, pdf_index: str) -> bool:
        """Return True if the file is accessible."""


# ── Local filesystem ───────────────────────────────────────────────────────────

class LocalStorage(BaseStorage):
    def __init__(self, base_dir: str):
        self.base = Path(base_dir).resolve()
        logger.info("LocalStorage root: %s", self.base)

    def _is_safe_path(self, p: Path) -> bool:
        """Prevent path traversal — resolved path must stay inside base dir."""
        try:
            return p.resolve().is_relative_to(self.base)
        except (ValueError, OSError):
            return False

    def get_pdf_path(self, pdf_index: str) -> Optional[Path]:
        # Ensure .pdf extension
        name = pdf_index if pdf_index.endswith(".pdf") else f"{pdf_index}.pdf"
        p = self.base / name
        if self._is_safe_path(p) and p.exists():
            return p
        # Try without extension if caller passed bare name
        p2 = self.base / pdf_index
        if self._is_safe_path(p2) and p2.exists():
            return p2
        if not self._is_safe_path(p):
            logger.warning("Path traversal blocked for: %s", pdf_index)
        else:
            logger.warning("PDF not found locally: %s", p)
        return None

    def exists(self, pdf_index: str) -> bool:
        return self.get_pdf_path(pdf_index) is not None


# ── AWS S3 ────────────────────────────────────────────────────────────────────

class S3Storage(BaseStorage):
    """
    Downloads PDFs from S3 to a local cache on first access.
    Subsequent requests are served from cache — no repeated downloads.
    """
    CACHE_DIR = Path("/tmp/pdf_cache")

    def __init__(self, bucket: str, prefix: str, region: str,
                 access_key: str = "", secret_key: str = ""):
        import boto3  # lazy import keeps boto3 optional for local dev
        self.bucket = bucket
        self.prefix = prefix.rstrip("/") + "/"
        self.s3 = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=access_key or None,
            aws_secret_access_key=secret_key or None,
        )
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("S3Storage: s3://%s/%s  cache=%s", bucket, prefix, self.CACHE_DIR)

    def _cache_path(self, pdf_index: str) -> Path:
        return self.CACHE_DIR / pdf_index

    def _is_safe_path(self, p: Path) -> bool:
        """Prevent path traversal — resolved path must stay inside cache dir."""
        try:
            return p.resolve().is_relative_to(self.CACHE_DIR.resolve())
        except (ValueError, OSError):
            return False

    def get_pdf_path(self, pdf_index: str) -> Optional[Path]:
        cached = self._cache_path(pdf_index)
        if not self._is_safe_path(cached):
            logger.warning("Path traversal blocked for S3 cache: %s", pdf_index)
            return None
        if cached.exists():
            return cached
        s3_key = self.prefix + pdf_index
        try:
            logger.info("S3 download: s3://%s/%s → %s", self.bucket, s3_key, cached)
            self.s3.download_file(self.bucket, s3_key, str(cached))
            return cached
        except Exception as exc:
            logger.error("S3 download failed for %s: %s", s3_key, exc)
            return None

    def exists(self, pdf_index: str) -> bool:
        if self._cache_path(pdf_index).exists():
            return True
        try:
            self.s3.head_object(Bucket=self.bucket, Key=self.prefix + pdf_index)
            return True
        except Exception:
            return False


# ── Factory ────────────────────────────────────────────────────────────────────

def build_storage() -> BaseStorage:
    backend = settings.PDF_STORAGE_BACKEND.lower()
    if backend == "s3":
        return S3Storage(
            bucket=settings.S3_BUCKET,
            prefix=settings.S3_PREFIX,
            region=settings.AWS_REGION,
            access_key=settings.AWS_ACCESS_KEY_ID,
            secret_key=settings.AWS_SECRET_ACCESS_KEY,
        )
    return LocalStorage(base_dir=settings.PDF_LOCAL_DIR)


# Module-level singleton — import `storage` wherever you need it
storage: BaseStorage = build_storage()
