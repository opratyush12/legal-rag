"""
Shared fixtures for the legal-rag backend test suite.

IMPORTANT: Heavy native modules (faiss, sentence_transformers, etc.) are stubbed
in sys.modules BEFORE any app code is imported so tests run without the ML stack.
"""
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Stub out heavy native modules that may not be installed locally.
# Only stubs when the real module is not importable.
# ---------------------------------------------------------------------------
_STUB_MODULES = [
    "faiss",
    "sentence_transformers",
    "sentence_transformers.SentenceTransformer",
    "sentence_transformers.CrossEncoder",
    "groq",
    "edge_tts",
    "boto3",
    "pdfplumber",
    "fitz",          # PyMuPDF
    "rank_bm25",
    "numpy",
]

for _mod_name in _STUB_MODULES:
    if _mod_name not in sys.modules:
        try:
            __import__(_mod_name)
        except ImportError:
            _stub = types.ModuleType(_mod_name)
            _stub.__dict__.update({
                "SentenceTransformer": MagicMock,
                "CrossEncoder": MagicMock,
                "Groq": MagicMock,
                "BadRequestError": type("BadRequestError", (Exception,), {}),
                "Communicate": MagicMock,
                "read_index": MagicMock(return_value=MagicMock()),
                "Index": MagicMock,
                "BM25Okapi": MagicMock,
                "client": MagicMock(),
                # numpy stubs
                "array": MagicMock,
                "float32": "float32",
                "argsort": MagicMock(return_value=[0, 1, 2]),
                "ndarray": type("ndarray", (), {}),
                "vstack": MagicMock(return_value=MagicMock()),
                "concatenate": MagicMock(return_value=MagicMock()),
            })
            sys.modules[_mod_name] = _stub


# ---------------------------------------------------------------------------
# Sample data used across tests
# ---------------------------------------------------------------------------

SAMPLE_METADATA = [
    {"pdf_index": "100.pdf", "chunk": "This is a test chunk about property disputes in India."},
    {"pdf_index": "100.pdf", "chunk": "The court ruled that the plaintiff had valid ownership rights."},
    {"pdf_index": "200.pdf", "chunk": "Criminal case regarding section 302 IPC murder charges."},
    {"pdf_index": "200.pdf", "chunk": "The accused was found guilty under section 302 of the Indian Penal Code."},
    {"pdf_index": "300.pdf", "chunk": "Constitutional validity of reservation policy was challenged."},
]

SAMPLE_CASE_SUMMARY = {
    "pdf_index": "100.pdf",
    "relevance_score": 5.0,
    "confidence": "High",
    "summary": "Relevant to property dispute.",
    "snippet": "This is a test chunk about property disputes in India.",
    "available": True,
    "chunk_hits": 2,
}


def _chunks_for(pdf):
    return [m["chunk"] for m in SAMPLE_METADATA if m["pdf_index"] == pdf]


# ---------------------------------------------------------------------------
# All module paths where IndexManager is imported
# ---------------------------------------------------------------------------
_IM_TARGETS = [
    "app.core.index_manager.IndexManager",
    "app.main.IndexManager",
    "app.routers.search.IndexManager",
    "app.routers.chat.IndexManager",
    "app.routers.cases.IndexManager",
    "app.routers.upload.IndexManager",
    "app.services.search_service.IndexManager",
]

_STORAGE_TARGETS = [
    "app.core.storage.storage",
    "app.routers.cases.storage",
    "app.services.search_service.storage",
]


# ---------------------------------------------------------------------------
# IndexManager fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_index_manager():
    """Patch IndexManager everywhere to simulate loaded index."""
    mock_im = MagicMock()
    mock_im.is_ready.return_value = True
    mock_im.has_bm25 = True
    mock_im.metadata = SAMPLE_METADATA
    mock_im.chunks_for.side_effect = _chunks_for

    mock_index = MagicMock()
    mock_index.search.return_value = ([[0.9, 0.8, 0.7]], [[0, 1, 2]])
    mock_index.ntotal = 5
    mock_im.index = mock_index
    mock_im.bm25_search.return_value = [(0, 0.5), (2, 0.3)]
    mock_im.load = AsyncMock()

    patches = [patch(t, mock_im) for t in _IM_TARGETS]
    for p in patches:
        p.start()
    yield mock_im
    for p in patches:
        p.stop()


@pytest.fixture()
def mock_index_not_loaded():
    """Patch IndexManager everywhere to simulate NOT loaded."""
    mock_im = MagicMock()
    mock_im.is_ready.return_value = False
    mock_im.load = AsyncMock()

    patches = [patch(t, mock_im) for t in _IM_TARGETS]
    for p in patches:
        p.start()
    yield mock_im
    for p in patches:
        p.stop()


# ---------------------------------------------------------------------------
# Storage fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_storage():
    """Patch storage singleton everywhere."""
    mock_st = MagicMock()
    mock_st.exists.return_value = True
    mock_st.get_pdf_path.return_value = "/fake/path/100.pdf"

    patches = [patch(t, mock_st) for t in _STORAGE_TARGETS]
    for p in patches:
        p.start()
    yield mock_st
    for p in patches:
        p.stop()


# ---------------------------------------------------------------------------
# Groq service fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_groq():
    """Patch all groq_service functions at every import site."""
    with patch("app.services.groq_service.expand_query") as m1, \
         patch("app.services.groq_service.generate_relevance_summary") as m2, \
         patch("app.services.groq_service.chat_with_case") as m3, \
         patch("app.services.groq_service.general_legal_chat") as m4, \
         patch("app.routers.chat.chat_with_case") as m5, \
         patch("app.routers.assistant.general_legal_chat") as m6, \
         patch("app.services.search_service.expand_query") as m7, \
         patch("app.services.search_service.generate_relevance_summary") as m8:
        for m in (m1, m7):
            m.return_value = ["property dispute india", "land ownership case"]
        for m in (m2, m8):
            m.return_value = "This case is relevant to the query."
        for m in (m3, m5):
            m.return_value = "The court held that the plaintiff had valid ownership rights."
        for m in (m4, m6):
            m.return_value = "Article 21 protects the right to life and personal liberty."
        yield {
            "expand_query": m7,
            "generate_relevance_summary": m8,
            "chat_with_case": m5,
            "general_legal_chat": m6,
        }


# ---------------------------------------------------------------------------
# TTS fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_tts():
    """Patch TTS service at all import sites."""
    with patch("app.services.tts_service.synthesize", new_callable=AsyncMock) as s1, \
         patch("app.services.tts_service.list_voices", new_callable=AsyncMock) as v1, \
         patch("app.routers.voice.synthesize", new_callable=AsyncMock) as s2, \
         patch("app.routers.voice.list_voices", new_callable=AsyncMock) as v2:
        for m in (s1, s2):
            m.return_value = b"\xff\xfb\x90\x00" * 100
        voice_data = [{"short_name": "hi-IN-SwaraNeural", "friendly_name": "Swara",
                       "locale": "hi-IN", "gender": "Female"}]
        for m in (v1, v2):
            m.return_value = voice_data
        yield {"synthesize": s2, "list_voices": v2}


# ---------------------------------------------------------------------------
# ML model loaders fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_models():
    """Patch ML model loaders at all import sites."""
    with patch("app.core.model_loader.get_embed_model") as e1, \
         patch("app.core.model_loader.get_reranker") as r1, \
         patch("app.services.search_service.get_embed_model") as e2, \
         patch("app.services.search_service.get_reranker") as r2:
        embed = MagicMock()
        embed.encode.return_value = MagicMock(
            astype=MagicMock(return_value=[[0.1] * 384])
        )
        for m in (e1, e2):
            m.return_value = embed

        reranker = MagicMock()
        reranker.predict.return_value = [5.0, 3.0, 1.0]
        for m in (r1, r2):
            m.return_value = reranker

        yield {"embed": e2, "reranker": r2}


# ---------------------------------------------------------------------------
# Async test clients
# ---------------------------------------------------------------------------

@pytest.fixture()
async def client(mock_index_manager, mock_storage):
    """Async HTTP client with loaded index."""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture()
async def client_no_index(mock_index_not_loaded, mock_storage):
    """Async HTTP client with index NOT loaded — for 503 tests."""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
