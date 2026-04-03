import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env")

from agents.rag_agent import run_rag_agent_with_mock
from rag.ingest import ingest_pdf_to_chroma
from rag.retriever import health_check, retrieve_by_category, retrieve_guidelines
from utils.llm_client import get_active_provider

logging.basicConfig(level=logging.WARNING)


def main() -> None:
    print("ICU PDF RAG test starting")
    ingest_pdf_to_chroma(reset=True)

    status = health_check()
    assert status["chromadb_connected"], "ChromaDB is not connected"
    assert status["guidelines_count"] > 10, "Expected more than 10 PDF chunks in Chroma"
    print("PASS health_check:", status)

    retrieval = retrieve_guidelines(
        "Patient with hypotension, lactate 3.8, oliguria, altered mental status, possible sepsis",
        top_k=4,
    )
    assert retrieval, "No retrieval results returned"
    assert any(item["category"] in {"sepsis", "sofa", "septic_shock"} for item in retrieval), (
        f"Expected sepsis-related evidence, got {[item['category'] for item in retrieval]}"
    )
    print("PASS retrieve_guidelines")
    print(retrieval[0])

    category_hits = retrieve_by_category("lab_thresholds", top_k=2)
    assert category_hits, "No lab_thresholds results found"
    print("PASS retrieve_by_category")

    key_env = "GROQ_API_KEY" if get_active_provider() == "groq" else "OPENAI_API_KEY"
    if not os.environ.get(key_env):
        print(f"SKIP run_rag_agent_with_mock because {key_env} is missing")
        return

    rag_output = run_rag_agent_with_mock()
    assert rag_output["citations"], "RAG agent returned no citations"
    risk_flags = {item["risk_flag"] for item in rag_output["citations"]}
    assert "SEPSIS_RISK" in risk_flags, f"Expected SEPSIS_RISK in {risk_flags}"
    assert "AKI_RISK" in risk_flags, f"Expected AKI_RISK in {risk_flags}"
    assert any(item["source"] and item["category"] for item in rag_output["citations"]), (
        "Expected cited guideline sources and categories for each flagged risk"
    )
    print("PASS run_rag_agent_with_mock")
    print("query_used:", rag_output["query_used"])
    for item in rag_output["citations"]:
        print(item)


if __name__ == "__main__":
    main()
