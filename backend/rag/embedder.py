#embedding.py
from __future__ import annotations

import logging
import os
from typing import Optional

from sentence_transformers import SentenceTransformer


logger = logging.getLogger(__name__)
_embedding_model: Optional[SentenceTransformer] = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        model_name = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        _embedding_model = SentenceTransformer(model_name, local_files_only=False)
        logger.info("Embedding model loaded: %s", model_name)
    return _embedding_model


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedding_model()
    vectors = model.encode(texts, normalize_embeddings=True)
    return [vector.tolist() for vector in vectors]


def embed_query(query: str) -> list[float]:
    model = get_embedding_model()
    vector = model.encode([query], normalize_embeddings=True)[0]
    return vector.tolist()
