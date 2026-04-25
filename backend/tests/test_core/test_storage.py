"""Tests for app.core.storage — local and S3 storage backends."""
from unittest.mock import patch
from pathlib import Path
import tempfile


class TestLocalStorage:
    """LocalStorage — serves PDFs from local filesystem."""

    def test_get_pdf_path_existing_file(self):
        """Returns Path when file exists."""
        from app.core.storage import LocalStorage
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fake PDF
            pdf_path = Path(tmpdir).resolve() / "100.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 fake")
            storage = LocalStorage(tmpdir)
            result = storage.get_pdf_path("100.pdf")
            assert result == pdf_path

    def test_get_pdf_path_missing_file(self):
        """Returns None when file doesn't exist."""
        from app.core.storage import LocalStorage
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(tmpdir)
            result = storage.get_pdf_path("missing.pdf")
            assert result is None

    def test_get_pdf_path_auto_appends_extension(self):
        """If passed without .pdf, it still finds the file."""
        from app.core.storage import LocalStorage
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir).resolve() / "100.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 fake")
            storage = LocalStorage(tmpdir)
            result = storage.get_pdf_path("100")
            assert result == pdf_path

    def test_exists_true(self):
        """exists() returns True when PDF is present."""
        from app.core.storage import LocalStorage
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "200.pdf").write_bytes(b"%PDF")
            storage = LocalStorage(tmpdir)
            assert storage.exists("200.pdf") is True

    def test_exists_false(self):
        """exists() returns False when PDF is missing."""
        from app.core.storage import LocalStorage
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(tmpdir)
            assert storage.exists("nope.pdf") is False


class TestBuildStorage:
    """Storage factory function."""

    def test_build_local_storage(self):
        """PDF_STORAGE_BACKEND=local → LocalStorage."""
        from app.core.storage import build_storage, LocalStorage
        with patch("app.core.storage.settings") as mock_settings:
            mock_settings.PDF_STORAGE_BACKEND = "local"
            mock_settings.PDF_LOCAL_DIR = "/tmp/test_pdfs"
            result = build_storage()
        assert isinstance(result, LocalStorage)

    def test_build_s3_storage(self):
        """PDF_STORAGE_BACKEND=s3 → S3Storage."""
        from app.core.storage import build_storage, S3Storage
        with patch("app.core.storage.settings") as mock_settings, \
             patch("boto3.client"):  # don't actually create S3 client
            mock_settings.PDF_STORAGE_BACKEND = "s3"
            mock_settings.S3_BUCKET = "test-bucket"
            mock_settings.S3_PREFIX = "pdfs/"
            mock_settings.AWS_REGION = "us-east-1"
            mock_settings.AWS_ACCESS_KEY_ID = "fake"
            mock_settings.AWS_SECRET_ACCESS_KEY = "fake"
            result = build_storage()
        assert isinstance(result, S3Storage)
