
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.llm_client import get_active_provider, get_llm


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

OUTPUT_BASE = Path("backend/outputs/chief_agent")

SYSTEM_PROMPT = """You are the Chief Clinical Synthesis Agent in an ICU decision-support system.
You are given unified JSON produced by upstream agents.
Your task is to create a clean doctor-facing generalized report after excluding outlier-tainted values.

Rules:
- Treat this as decision support only, not a final diagnosis.
- Do not use excluded outlier values in your reasoning.
- Prefer evidence from rag_guidelines_output citations when available.
- Return only valid JSON.
- Be clinically clear, concise, and structured."""

HUMAN_PROMPT = """Patient identifiers:
subject_id={subject_id}
hadm_id={hadm_id}

Clean symptom findings:
{symptoms_summary}

Clean lab findings:
{labs_summary}

Flagged risks:
{flagged_risks_summary}

RAG guideline citations:
{rag_summary}

Excluded outliers:
{outlier_summary}

Return a JSON object with exactly these keys:
- agent
- subject_id
- hadm_id
- generated_at
- primary_concern
- clinical_summary
- prioritized_risks
- recommended_actions
- excluded_outliers
- data_quality
- doctor_handoff

Where prioritized_risks is a JSON array of objects with:
- risk_flag
- status
- guideline_source
- explanation
- threshold

Where data_quality is a JSON object with:
- note_parser_available
- lab_mapper_available
- rag_available
- outliers_removed_count
- sofa_coverage_pct"""


def run_chief_agent(unified_input: dict | str | Path) -> dict:
    unified = _load_unified_input(unified_input)
    subject_id = unified["pipeline_run"]["subject_id"]
    hadm_id = unified["pipeline_run"]["hadm_id"]

    clean_context = _build_clean_context(unified)

    try:
        llm = get_llm(provider=get_active_provider(), request_timeout=45)
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", HUMAN_PROMPT),
        ])
        chain = prompt | llm | StrOutputParser()

        raw = chain.invoke(
            {
                "subject_id": subject_id,
                "hadm_id": hadm_id,
                "symptoms_summary": _to_json(clean_context["symptoms"]),
                "labs_summary": _to_json(clean_context["clean_labs"]),
                "flagged_risks_summary": _to_json(clean_context["clean_flagged_risks"]),
                "rag_summary": _to_json(clean_context["rag_citations"]),
                "outlier_summary": _to_json(clean_context["excluded_outliers"]),
            }
        )
        report = _parse_report(raw)
    except Exception:
        report = _build_fallback_report(unified, clean_context)

    report["agent"] = "chief_agent"
    report["subject_id"] = subject_id
    report["hadm_id"] = hadm_id
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    report["excluded_outliers"] = clean_context["excluded_outliers"]
    report["data_quality"] = {
        "note_parser_available": unified["data_completeness"]["note_parser_available"],
        "lab_mapper_available": unified["data_completeness"]["lab_mapper_available"],
        "rag_available": unified["data_completeness"]["rag_available"],
        "outliers_removed_count": len(clean_context["excluded_outliers"]),
        "sofa_coverage_pct": unified["data_completeness"]["sofa_coverage_pct"],
    }

    return report


def save_chief_output(report: dict) -> Path:
    subject_id = report["subject_id"]
    hadm_id = report["hadm_id"]
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = OUTPUT_BASE / f"sub_{subject_id}" / f"hadm_{hadm_id}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"chief_report_{ts}.json"
    with open(out_file, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
    return out_file


def _load_unified_input(unified_input: dict | str | Path) -> dict:
    if isinstance(unified_input, dict):
        return unified_input
    path = Path(unified_input)
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def _build_clean_context(unified: dict) -> dict:
    outlier_flags = unified.get("outlier_flags", [])
    outlier_signals = {entry.get("signal") or entry.get("test") for entry in outlier_flags}

    symptoms = unified.get("note_parser_output", {}).get("parsed_symptoms", [])
    clean_labs = []
    for item in unified.get("lab_mapper_output", {}).get("critical_values", []):
        if item.get("is_outlier"):
            continue
        if item.get("test") in outlier_signals:
            continue
        clean_labs.append(item)

    clean_flagged_risks = []
    for risk in unified.get("flagged_risks", []):
        if risk.get("signal") in outlier_signals:
            continue
        clean_flagged_risks.append(risk)

    rag_citations = []
    for citation in unified.get("rag_guidelines_output", {}).get("citations", []):
        if any(signal in citation.get("matched_findings", []) for signal in outlier_signals):
            continue
        rag_citations.append(citation)

    excluded_outliers = []
    for item in outlier_flags:
        excluded_outliers.append(
            {
                "signal": item.get("signal") or item.get("test"),
                "value": item.get("value"),
                "timestamp": item.get("timestamp"),
                "reason": f"Excluded due to outlier flag (z_score={item.get('z_score')})",
            }
        )

    return {
        "symptoms": symptoms,
        "clean_labs": clean_labs,
        "clean_flagged_risks": clean_flagged_risks,
        "rag_citations": rag_citations,
        "excluded_outliers": excluded_outliers,
    }


def _parse_report(raw: str) -> dict:
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        start = clean.find("{")
        end = clean.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(clean[start:end + 1])
        raise


def _build_fallback_report(unified: dict, clean_context: dict) -> dict:
    rag_citations = clean_context["rag_citations"]
    prioritized = []
    for citation in rag_citations:
        prioritized.append(
            {
                "risk_flag": citation["risk_flag"],
                "status": "supported" if citation.get("criteria_met") else "possible",
                "guideline_source": citation["source"],
                "explanation": citation["rationale"],
                "threshold": citation["threshold"],
            }
        )

    primary_concern = "No major supported risk identified"
    if prioritized:
        primary_concern = prioritized[0]["risk_flag"]

    clean_lab_text = ", ".join(
        f"{item['test']} {item['value']} ({item['direction']})"
        for item in clean_context["clean_labs"]
    ) or "No retained critical labs"

    return {
        "primary_concern": primary_concern,
        "clinical_summary": (
            f"Patient summary generated from unified agent outputs after excluding outlier-tainted values. "
            f"Retained lab evidence: {clean_lab_text}."
        ),
        "prioritized_risks": prioritized,
        "recommended_actions": [
            "Review prioritized risks with a clinician.",
            "Cross-check retained labs against the bedside picture.",
            "Reassess any trend changes in the next review cycle.",
        ],
        "doctor_handoff": (
            "This report is a decision-support summary. Review the cited guideline evidence and retained labs before acting."
        ),
    }


def _to_json(value) -> str:
    return json.dumps(value, indent=2, default=str)


def _latest_unified_json() -> Path:
    root = Path("backend/outputs/orchestrator")
    files = sorted(root.rglob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError("No unified orchestrator JSON found in backend/outputs/orchestrator")
    return files[0]


if __name__ == "__main__":
    unified_path = _latest_unified_json()
    report = run_chief_agent(unified_path)
    out_file = save_chief_output(report)
    print(json.dumps(report, indent=2))
    print(f"Saved: {out_file}")
