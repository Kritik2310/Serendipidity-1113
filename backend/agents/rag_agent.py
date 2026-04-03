from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag.retriever import build_findings_query, retrieve_by_category, retrieve_guidelines
from utils.llm_client import get_active_provider


load_dotenv(Path(__file__).resolve().parents[1] / ".env")
logger = logging.getLogger(__name__)

RISK_RULES = [
    {
        "risk_flag": "SEPSIS_RISK",
        "category": "sepsis",
        "query": "sepsis guideline infection organ dysfunction sofa hypotension lactate oliguria altered mental status",
        "threshold": "Sepsis-3: suspected infection plus acute SOFA increase >= 2",
        "criteria_mode": "min_matches",
        "criteria_value": 3,
        "checks": [
            {"type": "symptom", "name": "hypotension", "label": "hypotension"},
            {"type": "symptom", "name": "altered mental status", "label": "altered mental status"},
            {"type": "symptom", "name": "oliguria", "label": "oliguria"},
            {"type": "lab_high", "name": "lactate", "min_value": 2.0, "label": "lactate > 2 mmol/L"},
            {"type": "lab_high", "name": "wbc", "min_value": 12.0, "label": "WBC > 12 K/uL"},
            {"type": "lab_high", "name": "creatinine", "min_value": 1.2, "label": "creatinine elevated"},
        ],
    },
    {
        "risk_flag": "SEPTIC_SHOCK_RISK",
        "category": "septic_shock",
        "query": "septic shock guideline hypotension vasopressor map 65 lactate > 2 despite fluids",
        "threshold": "Septic shock: vasopressor-dependent hypotension with MAP >= 65 and lactate > 2 mmol/L after fluids",
        "criteria_mode": "min_matches",
        "criteria_value": 2,
        "checks": [
            {"type": "symptom", "name": "hypotension", "label": "persistent hypotension"},
            {"type": "lab_high", "name": "lactate", "min_value": 2.0, "label": "lactate > 2 mmol/L"},
        ],
    },
    {
        "risk_flag": "AKI_RISK",
        "category": "aki",
        "query": "aki kdigo creatinine urine output oliguria acute kidney injury guideline",
        "threshold": "KDIGO AKI: creatinine rise >= 0.3 mg/dL in 48h or urine output < 0.5 mL/kg/hr for >= 6h",
        "criteria_mode": "min_matches",
        "criteria_value": 1,
        "checks": [
            {"type": "symptom", "name": "oliguria", "label": "oliguria"},
            {"type": "lab_high", "name": "creatinine", "min_value": 1.5, "label": "creatinine elevated"},
        ],
    },
    {
        "risk_flag": "EARLY_WARNING_ESCALATION",
        "category": "early_warning",
        "query": "news2 early warning score hypotension altered mental status urgent clinician review",
        "threshold": "NEWS2 high risk: score >= 7 or severe parameter abnormalities requiring urgent review",
        "criteria_mode": "min_matches",
        "criteria_value": 2,
        "checks": [
            {"type": "symptom", "name": "hypotension", "label": "hypotension"},
            {"type": "symptom", "name": "altered mental status", "label": "altered mental status"},
        ],
    },
]


def run_rag_agent(parsed_symptoms: list, critical_values: list, api_key: str = "") -> dict:
    """
    Retrieve specific guideline evidence for each flagged clinical risk.
    """
    query = build_findings_query(parsed_symptoms, critical_values)

    # Convert the findings into explicit clinical risks
    flagged_risks = _detect_flagged_risks(parsed_symptoms, critical_values)

    citations = []
    seen_keys = set()

    for risk in flagged_risks:
        # Retrieve the strongest evidence for this specific risk category first
        evidence = _retrieve_for_risk(risk, parsed_symptoms, critical_values)
        if not evidence:
            continue

        key = (risk["risk_flag"], evidence["source"], evidence.get("page"))
        if key in seen_keys:
            continue
        seen_keys.add(key)

        citations.append(
            {
                "risk_flag": risk["risk_flag"],
                "source": evidence["source"],
                "category": evidence["category"],
                "page": evidence.get("page"),
                "rationale": _build_rationale(risk, evidence),
                "criteria_met": risk["criteria_met"],
                "threshold": risk["threshold"],
                "matched_findings": risk["matched_findings"],
            }
        )

    if not citations:
        # Graceful degradation: if no per-risk mapping succeeds, still return the
        broad_hits = retrieve_guidelines(query, top_k=3)
        citations = [
            {
                "risk_flag": "GENERAL_CLINICAL_RISK",
                "source": item["source"],
                "category": item["category"],
                "page": item.get("page"),
                "rationale": item["passage"][:260],
                "criteria_met": False,
                "threshold": "See retrieved passage",
                "matched_findings": [],
            }
            for item in broad_hits
        ]

    top_score = 0
    if citations:
        top_matches = retrieve_guidelines(query, top_k=1)
        top_score = top_matches[0]["relevance_score"] if top_matches else 0

    return {
        "agent": "guideline_rag",
        "query_used": query,
        "citations": citations,
        "guidelines_retrieved": len(citations),
        "top_relevance_score": top_score,
    }


def run_rag_agent_with_mock() -> dict:
    mock_symptoms = [
        {"finding": "hypotension", "severity": "moderate", "raw_text": "BP 92/58"},
        {"finding": "altered mental status", "severity": "moderate", "raw_text": "confused and drowsy"},
        {"finding": "oliguria", "severity": "severe", "raw_text": "urine output 15 mL/hr"},
    ]
    mock_labs = [
        {"test": "Lactate", "value": 3.8, "unit": "mmol/L", "direction": "high"},
        {"test": "Creatinine", "value": 1.9, "unit": "mg/dL", "direction": "high"},
        {"test": "WBC", "value": 18.7, "unit": "K/uL", "direction": "high"},
    ]
    return run_rag_agent(mock_symptoms, mock_labs)


def save_rag_output(output: dict, output_path: str = "rag_output.json") -> None:
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(output, file, indent=2)


def _detect_flagged_risks(parsed_symptoms: list, critical_values: list) -> list[dict]:
    # Normalize findings
    symptom_names = {item.get("finding", "").strip().lower() for item in parsed_symptoms}
    labs = {
        item.get("test", "").strip().lower(): {
            "value": item.get("value"),
            "unit": item.get("unit", ""),
            "direction": item.get("direction", "").strip().lower(),
        }
        for item in critical_values
    }

    risks = []
    for rule in RISK_RULES:
        matched_findings = _evaluate_rule(rule, symptom_names, labs)
        if not matched_findings:
            continue

        criteria_met = False
        if rule["criteria_mode"] == "min_matches":
            criteria_met = len(matched_findings) >= rule["criteria_value"]

        risks.append(
            {
                "risk_flag": rule["risk_flag"],
                "category": rule["category"],
                "query": rule["query"],
                "threshold": rule["threshold"],
                "criteria_met": criteria_met,
                "matched_findings": matched_findings,
            }
        )

    return risks


def _retrieve_for_risk(risk: dict, parsed_symptoms: list, critical_values: list) -> dict | None:
    # Prefer category-constrained retrieval 
    category_hits = retrieve_by_category(risk["category"], top_k=2)
    if category_hits:
        return category_hits[0]

    # Fall back to a richer semantic query 
    combined_query = risk["query"] + " " + build_findings_query(parsed_symptoms, critical_values)
    broad_hits = retrieve_guidelines(combined_query, top_k=3)
    if broad_hits:
        return broad_hits[0]
    return None


def _build_rationale(risk: dict, evidence: dict) -> str:
    matched = ", ".join(risk["matched_findings"]) if risk["matched_findings"] else "clinical findings"
    passage = evidence["passage"][:180].strip()
    return (
        f"{risk['risk_flag']} matched findings: {matched}. "
        f"Retrieved guideline from {evidence['source']} supports this risk. "
        f"Relevant evidence: {passage}"
    )


def _evaluate_rule(rule: dict, symptom_names: set[str], labs: dict) -> list[str]:
    matched = []
    for check in rule["checks"]:
        if check["type"] == "symptom" and check["name"] in symptom_names:
            matched.append(check["label"])
        elif check["type"] == "lab_high" and _lab_is_high(labs, check["name"], check["min_value"]):
            matched.append(check["label"])
    return matched


def _lab_is_high(labs: dict, test_name: str, min_value: float) -> bool:
    if test_name not in labs:
        return False
    entry = labs[test_name]
    try:
        value = float(entry.get("value"))
    except (TypeError, ValueError):
        return False
    return entry.get("direction") == "high" and value >= min_value


if __name__ == "__main__":
    result = run_rag_agent_with_mock()
    save_rag_output(result)
    print(json.dumps(result, indent=2))
