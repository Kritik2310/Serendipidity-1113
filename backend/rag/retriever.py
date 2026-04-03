from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from rag.embedder import embed_query
from rag.vectorators import COLLECTION_NAME, DEFAULT_DB_DIR, get_guideline_collection


load_dotenv(Path(__file__).resolve().parents[1] / ".env")
logger = logging.getLogger(__name__)


def build_findings_query(parsed_symptoms: list, critical_values: list) -> str:
    symptom_parts = []
    for symptom in parsed_symptoms:
        severity = symptom.get("severity", "").strip().lower()
        if severity not in {"moderate", "severe"}:
            continue
        finding = symptom.get("finding", "unknown finding").strip()
        raw_text = symptom.get("raw_text", "").strip()
        if raw_text:
            symptom_parts.append(f"{finding} ({severity}; {raw_text})")
        else:
            symptom_parts.append(f"{finding} ({severity})")

    lab_parts = []
    for lab in critical_values:
        direction = lab.get("direction", "").strip().lower()
        if direction not in {"high", "low"}:
            continue
        test = lab.get("test", "unknown test").strip()
        value = lab.get("value", "?")
        unit = lab.get("unit", "").strip()
        direction_word = "elevated" if direction == "high" else "decreased"
        unit_text = f" {unit}" if unit else ""
        lab_parts.append(f"{test} {value}{unit_text} {direction_word}")

    parts = []
    if symptom_parts:
        parts.append("Symptoms: " + ", ".join(symptom_parts) + ".")
    if lab_parts:
        parts.append("Abnormal labs: " + ", ".join(lab_parts) + ".")

    parts.append(
        "Retrieve the most relevant ICU clinical guideline evidence, thresholds, and diagnostic criteria for the flagged risks."
    )
    return " ".join(parts).strip()


def retrieve_guidelines(query: str, top_k: int = 4, min_relevance: float = 0.2) -> list[dict]:
    collection = get_guideline_collection()
    if collection.count() == 0:
        logger.warning("Guideline collection is empty. Run python -m rag.ingest --reset first.")
        return []

    query_vector = embed_query(query)
    fetch_k = min(max(top_k * 3, top_k), collection.count())

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=fetch_k,
        include=["documents", "metadatas", "distances"],
    )

    output = []
    seen = set()
    for document, metadata, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        relevance = round(max(0.0, 1.0 - float(distance)), 3)
        key = (metadata.get("source"), metadata.get("page"), document[:80])
        if relevance < min_relevance or key in seen:
            continue

        seen.add(key)
        output.append(
            {
                "source": metadata.get("source", "Unknown Source"),
                "page": metadata.get("page"),
                "section": metadata.get("section"),
                "category": metadata.get("category", "general"),
                "passage": document,
                "relevance_score": relevance,
            }
        )

        if len(output) >= top_k:
            break

    return output


def retrieve_by_category(category: str, top_k: int = 2) -> list[dict]:
    collection = get_guideline_collection()
    if collection.count() == 0:
        return []

    query_vector = embed_query(category)
    try:
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where={"category": category},
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        return []

    output = []
    for document, metadata, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        output.append(
            {
                "source": metadata.get("source", "Unknown Source"),
                "page": metadata.get("page"),
                "section": metadata.get("section"),
                "category": metadata.get("category", category),
                "passage": document,
                "relevance_score": round(max(0.0, 1.0 - float(distance)), 3),
            }
        )

    return output


def health_check() -> dict:
    try:
        collection = get_guideline_collection()
        count = collection.count()
        return {
            "chromadb_connected": True,
            "collection_name": COLLECTION_NAME,
            "guidelines_count": count,
            "chroma_db_path": str(DEFAULT_DB_DIR),
            "embedding_model": os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            "ready": count > 0,
        }
    except Exception as exc:
        return {
            "chromadb_connected": False,
            "collection_name": COLLECTION_NAME,
            "guidelines_count": 0,
            "chroma_db_path": str(DEFAULT_DB_DIR),
            "embedding_model": os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            "ready": False,
            "error": str(exc),
        }
