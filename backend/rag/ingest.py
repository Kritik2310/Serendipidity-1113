from __future__ import annotations

import argparse
import logging
from pathlib import Path

from rag.embedder import embed_texts
from rag.loader import DEFAULT_PDF_PATH, build_pdf_guideline_chunks
from rag.vectorators import DEFAULT_DB_DIR, get_guideline_collection


logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)


def ingest_pdf_to_chroma(
    pdf_path: str | Path = DEFAULT_PDF_PATH,
    db_dir: str | Path = DEFAULT_DB_DIR,
    reset: bool = False,
) -> dict:
    chunks = build_pdf_guideline_chunks(pdf_path)
    if not chunks:
        raise ValueError("No chunks extracted from ICU guideline PDF.")

    collection = get_guideline_collection(db_dir)
    if reset and collection.count() > 0:
        existing = collection.get(include=[])
        if existing["ids"]:
            collection.delete(ids=existing["ids"])

    ids = [chunk["id"] for chunk in chunks]
    documents = [chunk["text"] for chunk in chunks]
    metadatas = [chunk["metadata"] for chunk in chunks]
    embeddings = embed_texts(documents)

    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings,
    )

    summary = {
        "pdf_path": str(Path(pdf_path).resolve()),
        "db_dir": str(Path(db_dir).resolve()),
        "chunks_loaded": len(chunks),
        "collection_size": collection.count(),
    }
    logger.info("PDF ingestion complete: %s", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest ICU guideline PDF into ChromaDB.")
    parser.add_argument("--pdf", default=str(DEFAULT_PDF_PATH), help="Path to the PDF knowledge base")
    parser.add_argument("--db-dir", default=str(DEFAULT_DB_DIR), help="Chroma persistence directory")
    parser.add_argument("--reset", action="store_true", help="Reset collection before ingest")
    args = parser.parse_args()

    ingest_pdf_to_chroma(pdf_path=args.pdf, db_dir=args.db_dir, reset=args.reset)


if __name__ == "__main__":
    main()
