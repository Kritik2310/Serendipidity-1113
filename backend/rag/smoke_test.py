from __future__ import annotations

import json

from rag.ingest import ingest_pdf_to_chroma
from rag.retriever import retrieve_guidelines


def main() -> None:
    ingest_pdf_to_chroma(reset=False)

    query = (
        "ICU patient with hypotension, altered mental status, oliguria, "
        "lactate 3.8 mmol/L, WBC 18.7 K/uL, and rising creatinine."
    )
    results = retrieve_guidelines(query, top_k=5)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
