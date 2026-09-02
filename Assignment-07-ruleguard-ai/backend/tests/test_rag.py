"""RAG pipeline tests: load -> split -> embed -> index -> retrieve -> build_context.

Uses a deterministic hashed bag-of-words embedder instead of the real Gemini
embeddings API, so these tests run offline, free, and fast, while still exercising
the real LangChain document loader, real text splitter, and real FAISS index
build/save/load/similarity_search. Only the embedding call itself is faked — same
"mock the provider, not your own logic" principle as test_gemini_service.py, applied
to the embeddings provider instead of the chat model.
"""
import hashlib
import math
import shutil
import tempfile
from collections import Counter
from pathlib import Path

import pytest
from langchain_core.embeddings import Embeddings

from app.core.config import settings
from app.services import rag_service


class FakeEmbeddings(Embeddings):
    """Deterministic hashed bag-of-words vectors. Similarity still tracks shared
    vocabulary, so retrieval tests can assert real relevance, not just shape."""

    DIM = 256

    def _vector(self, text: str) -> list:
        tokens = (w.lower().strip(".,:;()\"'") for w in text.split())
        counts = Counter(t for t in tokens if t.isalpha())
        vec = [0.0] * self.DIM
        for word, count in counts.items():
            idx = int(hashlib.md5(word.encode()).hexdigest(), 16) % self.DIM
            vec[idx] += count
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts):
        return [self._vector(t) for t in texts]

    def embed_query(self, text):
        return self._vector(text)


@pytest.fixture(autouse=True)
def _fake_index(monkeypatch):
    """Every test gets a fresh temp FAISS dir and a fake embedder — nothing touches
    the real data/faiss_index/ or the network."""
    monkeypatch.setattr(rag_service, "_get_embeddings", lambda: FakeEmbeddings())
    rag_service._vector_store = None

    temp_dir = Path(tempfile.mkdtemp())
    monkeypatch.setattr(settings, "faiss_index_dir", temp_dir)

    yield

    rag_service._vector_store = None
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_build_index_creates_index_files():
    rag_service.build_index()
    assert (settings.faiss_index_dir / "index.faiss").exists()
    assert (settings.faiss_index_dir / "index.pkl").exists()


def test_build_index_loads_all_kb_files():
    docs = rag_service._load_kb_documents()
    sources = {Path(d.metadata["source"]).name for d in docs}
    assert sources == {
        "authentication.md", "authorization.md", "api_security.md",
        "input_validation.md", "rate_limiting.md", "sensitive_data.md",
    }


async def test_retrieve_returns_top_k_chunks():
    rag_service.build_index()
    chunks = await rag_service.retrieve(
        "Allow a user to reset a password after verifying account ownership.", top_k=4
    )
    assert 1 <= len(chunks) <= 4
    assert all(isinstance(c, str) and c for c in chunks)


async def test_retrieve_finds_relevant_authentication_rule():
    rag_service.build_index()
    chunks = await rag_service.retrieve("password reset ownership verification", top_k=3)
    joined = " ".join(chunks).lower()
    assert "password reset" in joined


async def test_retrieve_without_index_raises_runtime_error():
    with pytest.raises(RuntimeError):
        await rag_service.retrieve("anything")


def test_build_context_formats_numbered_chunks():
    ctx = rag_service.build_context(["Rule A", "Rule B"])
    assert ctx == "[1] Rule A\n\n[2] Rule B"


def test_build_context_handles_no_results():
    ctx = rag_service.build_context([])
    assert "No directly relevant" in ctx
