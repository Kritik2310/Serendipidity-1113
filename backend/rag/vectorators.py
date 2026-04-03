# vectorators.py
from __future__ import annotations

import os
from pathlib import Path

import chromadb

BASE_DIR        = Path(__file__).resolve().parents[1]
DEFAULT_DB_DIR  = Path(
    os.environ.get("CHROMA_DB_PATH", "").strip()
    or str(BASE_DIR / "data" / "chroma_db")
)
COLLECTION_NAME = "medical_guidelines_pdf"


def get_chroma_client(db_dir: str | Path | None = None) -> chromadb.PersistentClient:
    path = Path(db_dir or DEFAULT_DB_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(path))


def get_guideline_collection(db_dir: str | Path | None = None):
    """
    Returns the ChromaDB collection for medical guidelines.
    Creates it with cosine similarity if it doesn't exist yet.
    """
    client = get_chroma_client(db_dir)
    return client.get_or_create_collection(
        name               = COLLECTION_NAME,
        embedding_function = None,   # embeddings are pre-computed by embedder.py
        metadata           = {"hnsw:space": "cosine"},
    )