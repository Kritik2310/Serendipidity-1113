from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag.retriever import build_findings_query, retrieve_by_category, retrieve_guidelines
from utils.lab_ranges import SOFA_LABS

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
logger = logging.getLogger(__name__)

#Risk rules 
RISK_RULES = [
    {
        "risk_flag":      "SEPSIS_RISK",
        "category":       "sepsis",
        "query":          "sepsis guideline infection organ dysfunction sofa hypotension lactate oliguria altered mental status",
        "threshold":      "Sepsis-3: suspected infection plus acute SOFA increase >= 2",
        "criteria_mode":  "min_matches",
        "criteria_value": 3,
        "checks": [
            {"type": "symptom",  "name": "hypotension",            "label": "hypotension"},
            {"type": "symptom",  "name": "altered mental status",  "label": "altered mental status"},
            {"type": "symptom",  "name": "oliguria",               "label": "oliguria"},
            {"type": "lab_high", "name": "lactate",    "min_value": 2.0,  "label": "lactate > 2 mmol/L"},
            {"type": "lab_high", "name": "wbc",        "min_value": 12.0, "label": "WBC > 12 K/uL"},
            {"type": "lab_high", "name": "creatinine", "min_value": 1.2,  "label": "creatinine elevated"},
        ],
    },
    {
        "risk_flag":      "SEPTIC_SHOCK_RISK",
        "category":       "septic_shock",
        "query":          "septic shock vasopressor map 65 lactate refractory hypotension fluid resuscitation",
        "threshold":      "Septic shock: vasopressor-dependent MAP >= 65 with lactate > 2 mmol/L after fluids",
        "criteria_mode":  "min_matches",
        "criteria_value": 2,
        "checks": [
            {"type": "symptom",  "name": "hypotension", "label": "persistent hypotension"},
            {"type": "lab_high", "name": "lactate",     "min_value": 2.0, "label": "lactate > 2 mmol/L"},
        ],
    },
    {
        "risk_flag":      "AKI_RISK",
        "category":       "aki",
        "query":          "acute kidney injury kdigo creatinine urine output oliguria stage classification",
        "threshold":      "KDIGO AKI: creatinine rise >= 0.3 mg/dL in 48h or urine output < 0.5 mL/kg/hr for >= 6h",
        "criteria_mode":  "min_matches",
        "criteria_value": 1,
        "checks": [
            {"type": "symptom",  "name": "oliguria",    "label": "oliguria"},
            {"type": "lab_high", "name": "creatinine",  "min_value": 1.5, "label": "creatinine elevated"},
        ],
    },
    {
        "risk_flag":      "HEPATIC_DYSFUNCTION_RISK",
        "category":       "hepatic",
        "query":          "liver dysfunction bilirubin jaundice sofa hepatic failure icu",
        "threshold":      "SOFA liver score >= 1: bilirubin > 1.2 mg/dL",
        "criteria_mode":  "min_matches",
        "criteria_value": 1,
        "checks": [
            {"type": "lab_high", "name": "bilirubin", "min_value": 2.0, "label": "bilirubin elevated"},
            {"type": "symptom",  "name": "jaundice",  "label": "jaundice"},
        ],
    },
    {
        "risk_flag":      "ANAEMIA_RISK",
        "category":       "anaemia",
        "query":          "anaemia haemoglobin transfusion threshold icu critical care guideline",
        "threshold":      "Transfusion threshold: Hemoglobin < 7 g/dL in stable ICU patients",
        "criteria_mode":  "min_matches",
        "criteria_value": 1,
        "checks": [
            {"type": "lab_low", "name": "hemoglobin", "max_value": 7.0, "label": "Hemoglobin < 7 g/dL"},
        ],
    },
    {
        "risk_flag":      "COAGULOPATHY_RISK",
        "category":       "coagulopathy",
        "query":          "thrombocytopenia platelets coagulopathy icu bleeding sofa coagulation",
        "threshold":      "SOFA coag score >= 1: platelets < 150 K/uL",
        "criteria_mode":  "min_matches",
        "criteria_value": 1,
        "checks": [
            {"type": "lab_low", "name": "platelets", "max_value": 100.0, "label": "Platelets < 100 K/uL"},
        ],
    },
    {
        "risk_flag":      "EARLY_WARNING_ESCALATION",
        "category":       "early_warning",
        "query":          "news2 early warning score rapid response team urgent clinician review deterioration",
        "threshold":      "NEWS2 high risk: score >= 7 or any single severe parameter",
        "criteria_mode":  "min_matches",
        "criteria_value": 2,
        "checks": [
            {"type": "symptom", "name": "hypotension",           "label": "hypotension"},
            {"type": "symptom", "name": "altered mental status", "label": "altered mental status"},
            {"type": "symptom", "name": "tachycardia",           "label": "tachycardia"},
        ],
    },
]
#Public entry point
def run_rag_agent(parsed_symptoms: list, critical_values: list, api_key: str = "") -> dict:
    """
    For each detected clinical risk, retrieve the strongest matching
    guideline passage from ChromaDB and return structured citations.
    """
    query         = build_findings_query(parsed_symptoms, critical_values)
    flagged_risks = _detect_flagged_risks(parsed_symptoms, critical_values)

    citations: list[dict] = []
    seen_keys: set        = set()

    for risk in flagged_risks:
        evidence = _retrieve_for_risk(risk, parsed_symptoms, critical_values)
        if not evidence:
            continue

        key = (risk["risk_flag"], evidence["source"], evidence.get("page"))
        if key in seen_keys:
            continue
        seen_keys.add(key)

        citations.append({
            "risk_flag":       risk["risk_flag"],
            "source":          evidence["source"],
            "category":        evidence["category"],
            "page":            evidence.get("page"),
            "rationale":       _build_rationale(risk, evidence),
            "criteria_met":    risk["criteria_met"],
            "threshold":       risk["threshold"],
            "matched_findings": risk["matched_findings"],
        })
    #fallback 
    if not citations:
        broad_hits = retrieve_guidelines(query, top_k=3)
        citations = [
            {
                "risk_flag":       "GENERAL_CLINICAL_RISK",
                "source":          item["source"],
                "category":        item["category"],
                "page":            item.get("page"),
                "rationale":       item["passage"][:260],
                "criteria_met":    False,
                "threshold":       "See retrieved passage",
                "matched_findings": [],
            }
            for item in broad_hits
        ]
    top_score = 0
    if citations:
        top_matches = retrieve_guidelines(query, top_k=1)
        top_score   = top_matches[0]["relevance_score"] if top_matches else 0

    return {
        "agent":               "guideline_rag",
        "query_used":          query,
        "citations":           citations,
        "guidelines_retrieved": len(citations),
        "top_relevance_score": top_score,
    }
#Risk detection 
def _detect_flagged_risks(parsed_symptoms: list, critical_values: list) -> list[dict]:
    """Match findings against RISK_RULES — returns only rules with >= 1 match."""
    symptom_names = {
        item.get("finding", "").strip().lower()
        for item in parsed_symptoms
    }
    # Normalise lab names to lowercase 
    labs = {
        item.get("test", "").strip().lower(): {
            "value":     item.get("value"),
            "unit":      item.get("unit", ""),
            "direction": item.get("direction", "").strip().lower(),
        }
        for item in critical_values
    }

    risks = []
    for rule in RISK_RULES:
        matched = _evaluate_rule(rule, symptom_names, labs)
        if not matched:
            continue

        criteria_met = (
            len(matched) >= rule["criteria_value"]
            if rule["criteria_mode"] == "min_matches"
            else False
        )
        risks.append({
            "risk_flag":       rule["risk_flag"],
            "category":        rule["category"],
            "query":           rule["query"],
            "threshold":       rule["threshold"],
            "criteria_met":    criteria_met,
            "matched_findings": matched,
        })

    return risks
def _evaluate_rule(rule: dict, symptom_names: set, labs: dict) -> list[str]:
    matched = []
    for check in rule["checks"]:
        if check["type"] == "symptom":
            if check["name"] in symptom_names:
                matched.append(check["label"])

        elif check["type"] == "lab_high":
            if _lab_exceeds(labs, check["name"], check["min_value"]):
                matched.append(check["label"])

        elif check["type"] == "lab_low":
            if _lab_below(labs, check["name"], check["max_value"]):
                matched.append(check["label"])

    return matched


def _lab_exceeds(labs: dict, test_name: str, min_value: float) -> bool:
    """True if lab is flagged high and value >= min_value."""
    entry = labs.get(test_name.lower())
    if not entry:
        return False
    try:
        return entry["direction"] == "high" and float(entry["value"]) >= min_value
    except (TypeError, ValueError):
        return False


def _lab_below(labs: dict, test_name: str, max_value: float) -> bool:
    """True if lab is flagged low and value <= max_value."""
    entry = labs.get(test_name.lower())
    if not entry:
        return False
    try:
        return entry["direction"] == "low" and float(entry["value"]) <= max_value
    except (TypeError, ValueError):
        return False


def _retrieve_for_risk(
    risk: dict,
    parsed_symptoms: list,
    critical_values: list,
) -> dict | None:
    """Category-constrained retrieval first, broad semantic fallback second."""
    hits = retrieve_by_category(risk["category"], top_k=2)
    if hits:
        return hits[0]

    combined = risk["query"] + " " + build_findings_query(parsed_symptoms, critical_values)
    broad    = retrieve_guidelines(combined, top_k=3)
    return broad[0] if broad else None

def _build_rationale(risk: dict, evidence: dict) -> str:
    matched = ", ".join(risk["matched_findings"]) or "clinical findings"
    passage = evidence["passage"][:180].strip()
    return (
        f"{risk['risk_flag']} matched: {matched}. "
        f"Guideline from {evidence['source']} supports this risk. "
        f"Evidence: {passage}"
    )


# Mockrunner for isolated testing 
def run_rag_agent_with_mock() -> dict:
    mock_symptoms = [
        {"finding": "hypotension",           "severity": "moderate", "raw_text": "BP 92/58"},
        {"finding": "altered mental status",  "severity": "moderate", "raw_text": "confused and drowsy"},
        {"finding": "oliguria",              "severity": "severe",   "raw_text": "urine output 15 mL/hr"},
    ]
    mock_labs = [
        {"test": "Lactate",    "value": 3.8,  "unit": "mmol/L", "direction": "high"},
        {"test": "Creatinine", "value": 1.9,  "unit": "mg/dL",  "direction": "high"},
        {"test": "WBC",        "value": 18.7, "unit": "K/uL",   "direction": "high"},
        {"test": "Bilirubin",  "value": 2.4,  "unit": "mg/dL",  "direction": "high"},
        {"test": "Platelets",  "value": 88.0, "unit": "K/uL",   "direction": "low"},
        {"test": "Hemoglobin", "value": 6.8,  "unit": "g/dL",   "direction": "low"},
    ]
    return run_rag_agent(mock_symptoms, mock_labs)

def save_rag_output(output: dict, output_path: str = "rag_output.json") -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
        
if __name__ == "__main__":
    result = run_rag_agent_with_mock()
    save_rag_output(result)
    print(json.dumps(result, indent=2))