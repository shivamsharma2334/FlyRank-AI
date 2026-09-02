"""RAG: load the KB, build/load a FAISS index, retrieve relevant rule chunks.
Index is built offline (scripts/build_index.py); the API only ever loads and searches it.
"""
from __future__ import annotations

import asyncio
from typing import List, Optional

from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings

_embeddings: Optional[GoogleGenerativeAIEmbeddings] = None
_vector_store: Optional[FAISS] = None


def _get_embeddings() -> GoogleGenerativeAIEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = GoogleGenerativeAIEmbeddings(
            model=settings.embedding_model,
            google_api_key=settings.gemini_api_key,
        )
    return _embeddings


def _load_kb_documents() -> list:
    docs = []
    for path in sorted(settings.kb_dir.glob("*.md")):
        docs.extend(TextLoader(str(path), encoding="utf-8").load())
    return docs


def build_index() -> None:
    documents = _load_kb_documents()
    if not documents:
        raise RuntimeError(f"No .md files found in {settings.kb_dir}")

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(documents)

    store = FAISS.from_documents(chunks, _get_embeddings())
    settings.faiss_index_dir.mkdir(parents=True, exist_ok=True)
    store.save_local(str(settings.faiss_index_dir))


def _load_store() -> FAISS:
    global _vector_store
    if _vector_store is None:
        if not (settings.faiss_index_dir / "index.faiss").exists():
            raise RuntimeError("FAISS index not found. Run `python scripts/build_index.py` first.")
        _vector_store = FAISS.load_local(
            str(settings.faiss_index_dir),
            _get_embeddings(),
            allow_dangerous_deserialization=True,  # safe: we only ever load our own local build
        )
    return _vector_store


async def retrieve(request_text: str, top_k: Optional[int] = None) -> List[str]:
    store = _load_store()
    k = top_k or settings.rag_top_k
    results = await asyncio.to_thread(store.similarity_search, request_text, k=k)
    return [doc.page_content.strip() for doc in results]


def build_context(chunks: List[str]) -> str:
    if not chunks:
        return "No directly relevant internal rules were retrieved."
    return "\n\n".join(f"[{i + 1}] {c}" for i, c in enumerate(chunks))
