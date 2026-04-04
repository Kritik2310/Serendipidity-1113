from __future__ import annotations
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.llm_client import get_active_provider, get_llm
from backend.utils.outlier_rules import Z_THRESHOLD, IMPLAUSIBLE_LIMITS, check_delta
from backend.utils.mongo_client import ensure_indexes          # ← NEW
from backend.utils.mongo_store import save_chief_report        # ← NEW

from backend.utils.mongo_client import ensure_indexes
from backend.utils.mongo_store import save_chief_report

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

logger       = logging.getLogger(__name__)
OUTPUT_BASE  = Path("backend/outputs/chief_agent")
HISTORY_FILE = Path("backend/data/PATIENT_HISTORY.csv")


SYSTEM_PROMPT = """You are the Chief Clinical Synthesis Agent in an ICU decision-support system.
You receive structured clinical findings after outlier removal.
Produce a clean, doctor-facing diagnostic support report.

Rules:
- This is decision support only — never state a final diagnosis.
- Use RAG guideline citations as primary evidence where available.
- Be concise, clinically precise, and structured.
- Return only valid JSON — no markdown, no preamble."""

HUMAN_PROMPT = """Patient: subject_id={subject_id}  hadm_id={hadm_id}

Symptom findings (from clinical notes):
{symptoms_summary}

Clean lab findings (outliers removed):
{labs_summary}

Flagged clinical risks:
{flagged_risks_summary}

Guideline citations (RAG):
{rag_summary}

Outliers excluded from this analysis:
{outlier_summary}

Return a JSON object with exactly these keys:
- primary_concern          (string)
- clinical_summary         (string — 3 to 5 sentences)
- prioritized_risks        (array of objects: risk_flag, status, guideline_source, explanation, threshold)
- recommended_actions      (array of strings)
- doctor_handoff           (string — what the clinician must review next)
- disease_progression      (array of objects: period, observation)"""


FAMILY_LANGUAGE      = os.getenv("FAMILY_REGIONAL_LANGUAGE", "Hindi")
FAMILY_LANGUAGE_CODE = os.getenv("FAMILY_REGIONAL_LANGUAGE_CODE", "hi")

FAMILY_SYSTEM_PROMPT = """You are the Family Communication Assistant in an ICU decision-support system.
You convert a technical ICU update into a compassionate, jargon-free explanation for the patient's family.

Rules:
- Speak as if explaining to a worried non-medical family member.
- Focus only on the last 12 hours.
- Be honest, calm, and compassionate.
- Avoid unexplained medical jargon, abbreviations, and acronyms.
- Do not overstate certainty or give false reassurance.
- Mention what changed, what the care team is watching, and what happens next.
- Return only valid JSON."""

FAMILY_HUMAN_PROMPT = """Patient: subject_id={subject_id} hadm_id={hadm_id}
Regional language: {regional_language} ({regional_language_code})

Technical clinical summary:
{clinical_summary}

Technical prioritized risks:
{prioritized_risks}

Recommended actions:
{recommended_actions}

Doctor handoff:
{doctor_handoff}

Last 12 hours of retained findings:
{recent_findings}

Excluded outliers:
{excluded_outliers}

Return a JSON object with exactly these keys:
- english_summary
- regional_summary"""

def _load_patient_history(subject_id: int, hadm_id: int) -> dict:
    if not HISTORY_FILE.exists():
        logger.warning("PATIENT_HISTORY.csv not found — historical check skipped")
        return {}

    hist  = pd.read_csv(HISTORY_FILE)
    prior = hist[
        (hist["subject_id"] == subject_id) &
        (hist["hadm_id"]    != hadm_id)
    ]

    if prior.empty:
        return {}

    baselines: dict[str, list] = {}
    for _, row in prior.iterrows():
        lab = row["lab_name"]
        if lab not in baselines:
            baselines[lab] = []
        baselines[lab].append(float(row["mean_value"]))

    result = {}
    for lab, means in baselines.items():
        arr = pd.Series(means)
        result[lab] = {
            "historical_mean":  round(float(arr.mean()), 3),
            "historical_std":   round(float(arr.std(ddof=0)) if len(means) > 1 else 0.0, 3),
            "prior_admissions": len(means),
        }

    logger.info(
        "Historical baselines loaded for subject=%s — %d labs from prior admissions",
        subject_id, len(result),
    )
    return result


def is_confirmed_outlier(test, value, timestamp, timeline):
    """
    Return True if the flagged value is corroborated by at least one other
    reading (anywhere in the timeline) within 20% tolerance.
    Uses proper datetime comparison instead of raw string comparison.
    """
    anchor = _parse_iso_timestamp(timestamp)
    if anchor is None:
        return False

    for entry in timeline:
        ts  = _parse_iso_timestamp(entry.get("timestamp"))
        val = entry.get("value")

        if ts is None or not isinstance(val, (int, float)):
            continue
        if ts == anchor:
            continue  # skip the flagged reading itself
        if abs(val - value) / max(abs(value), 1) < 0.2:
            return True

    return False

def _detect_outliers_chief(
    lab_mapper_output: dict,
    subject_id: int,
    hadm_id: int,
) -> tuple[list[dict], list[dict]]:
    clean_labs:        list[dict] = []
    excluded_outliers: list[dict] = []

    critical_values  = lab_mapper_output.get("critical_values", [])
    timeline_by_test = lab_mapper_output.get("timeline_by_test", {})

    history = _load_patient_history(subject_id, hadm_id)

    for item in critical_values:
        test      = item.get("test", "")
        value     = item.get("value", 0.0)
        timestamp = item.get("timestamp", "")
        timeline  = timeline_by_test.get(test, [])
        exclusion: dict | None = None

        limits = IMPLAUSIBLE_LIMITS.get(test)
        if limits and not (limits[0] < value < limits[1]):
            exclusion = {
                "layer":     "physiological",
                "test":      test,
                "value":     value,
                "timestamp": timestamp,
                "z_score":   None,
                "reason": (
                    f"Physiologically implausible — {test} value {value} is outside "
                    f"survivable range ({limits[0]}–{limits[1]}). "
                    f"Probable specimen error. Immediate redraw required. "
                    f"(Guidelines Section 15.1)"
                ),
                "status":              "pending_confirmation",
                "historical_baseline": history.get(test),
            }
        if not exclusion:
            current_values = [
                e["value"] for e in timeline
                if isinstance(e.get("value"), (int, float))
            ]
            if len(current_values) >= 3:
                arr  = np.array(current_values)
                mean = arr.mean()
                std  = arr.std(ddof=0)
                if std > 0:
                    z = round(float((value - mean) / std), 3)
                    if abs(z) > Z_THRESHOLD:
                        exclusion = {
                            "layer":        "current_admission",
                            "test":         test,
                            "value":        value,
                            "timestamp":    timestamp,
                            "z_score":      z,
                            "rolling_mean": round(mean, 3),
                            "rolling_std":  round(std, 3),
                            "reason": (
                                f"Statistical outlier vs current admission history — "
                                f"{test} z-score={z} exceeds threshold {Z_THRESHOLD}. "
                                f"Rolling mean={round(mean,3)}, std={round(std,3)}. "
                                f"Redraw recommended before updating clinical assessment."
                            ),
                            "status":              "pending_confirmation",
                            "historical_baseline": history.get(test),
                        }
        if not exclusion and test in history:
            h      = history[test]
            h_std  = h["historical_std"]
            h_mean = h["historical_mean"]
            if h_std > 0:
                hist_z = round(float((value - h_mean) / h_std), 3)
                if abs(hist_z) > Z_THRESHOLD:
                    exclusion = {
                        "layer":            "historical_baseline",
                        "test":             test,
                        "value":            value,
                        "timestamp":        timestamp,
                        "z_score":          hist_z,
                        "historical_mean":  h_mean,
                        "historical_std":   h_std,
                        "prior_admissions": h["prior_admissions"],
                        "reason": (
                            f"Outlier vs patient's own history — {test} value {value} "
                            f"deviates from baseline across {h['prior_admissions']} "
                            f"prior admission(s) (hist_mean={h_mean}, hist_z={hist_z}). "
                            f"Investigate clinical change vs measurement error."
                        ),
                        "status":              "pending_confirmation",
                        "historical_baseline": h,
                    }

        if not exclusion:
            delta_flag = check_delta(test, value, timestamp, timeline)
            if delta_flag:
                exclusion = {
                    "layer":               "realtime_delta",
                    "test":                test,
                    "value":               value,
                    "timestamp":           timestamp,
                    "z_score":             None,
                    "delta":               delta_flag["delta"],
                    "prior_value":         delta_flag["prior_value"],
                    "prior_ts":            delta_flag["prior_ts"],
                    "reason":              delta_flag["reason"],
                    "historical_baseline": history.get(test),
                    "status":              "pending_confirmation",
                }

        if exclusion:
            if is_confirmed_outlier(test, value, timestamp, timeline):
                logger.info(
                    "Outlier confirmed by repeat — %s=%.2f [%s] now accepted",
                    test, value, timestamp,
                )
                clean_labs.append(item)
            else:
                exclusion["status"] = "pending_confirmation"
                excluded_outliers.append(exclusion)
                logger.info(
                    "Outlier pending confirmation — %s=%.2f [%s]",
                    test, value, timestamp,
                )
        else:
            clean_labs.append(item)

    logger.info(
        "Outlier detection complete — %d clean | %d excluded",
        len(clean_labs), len(excluded_outliers),
    )
    return clean_labs, excluded_outliers

def _build_clean_context(unified: dict, subject_id: int, hadm_id: int) -> dict:
    """Build clean LLM input after outlier removal across all four layers."""
    lab_output = unified.get("lab_mapper_output", {})
    clean_labs, excluded_outliers = _detect_outliers_chief(
        lab_output, subject_id, hadm_id
    )

    excluded_signals = {e["test"] for e in excluded_outliers}
    symptoms         = unified.get("note_parser_output", {}).get("parsed_symptoms", [])

    clean_risks = [
        r for r in unified.get("flagged_risks", [])
        if r.get("signal") not in excluded_signals
    ]

    clean_citations = [
        c for c in unified.get("rag_guidelines_output", {}).get("citations", [])
        if not any(s in c.get("matched_findings", []) for s in excluded_signals)
    ]

    return {
        "symptoms":          symptoms,
        "clean_labs":        clean_labs,
        "clean_risks":       clean_risks,
        "clean_citations":   clean_citations,
        "excluded_outliers": excluded_outliers,
    }


def _call_llm(subject_id: int, hadm_id: int, ctx: dict) -> dict:
    llm    = get_llm(provider=get_active_provider(), request_timeout=60)
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human",  HUMAN_PROMPT),
    ])
    chain = prompt | llm | StrOutputParser()

    raw = chain.invoke({
        "subject_id":            subject_id,
        "hadm_id":               hadm_id,
        "symptoms_summary":      _to_json(ctx["symptoms"]),
        "labs_summary":          _to_json(ctx["clean_labs"]),
        "flagged_risks_summary": _to_json(ctx["clean_risks"]),
        "rag_summary":           _to_json(ctx["clean_citations"]),
        "outlier_summary":       _to_json(ctx["excluded_outliers"]),
    })

    return _parse_llm_response(raw)


def _parse_llm_response(raw: str) -> dict:
    clean = raw.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        start, end = clean.find("{"), clean.rfind("}")
        if start != -1 and end > start:
            return json.loads(clean[start:end + 1])
        raise


def _parse_iso_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y, %H:%M:%S"):
            try:
                return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


def _filter_last_12_hours(ctx: dict) -> list[dict]:
    latest_seen: datetime | None = None
    recent_events: list[dict]    = []

    for symptom in ctx.get("symptoms", []):
        ts = _parse_iso_timestamp(symptom.get("timestamp"))
        if ts and (latest_seen is None or ts > latest_seen):
            latest_seen = ts

    for lab in ctx.get("clean_labs", []):
        ts = _parse_iso_timestamp(lab.get("timestamp"))
        if ts and (latest_seen is None or ts > latest_seen):
            latest_seen = ts

    if latest_seen is None:
        latest_seen = datetime.now(timezone.utc)
    cutoff = latest_seen - timedelta(hours=12)

    for symptom in ctx.get("symptoms", []):
        ts = _parse_iso_timestamp(symptom.get("timestamp"))
        if ts and ts >= cutoff:
            recent_events.append({
                "type":      "symptom",
                "timestamp": ts.isoformat(),
                "finding":   symptom.get("finding", ""),
                "severity":  symptom.get("severity", "unknown"),
                "trend":     symptom.get("trend", "unknown"),
            })

    for lab in ctx.get("clean_labs", []):
        ts = _parse_iso_timestamp(lab.get("timestamp"))
        if ts and ts >= cutoff:
            recent_events.append({
                "type":      "lab",
                "timestamp": ts.isoformat(),
                "test":      lab.get("test", ""),
                "value":     lab.get("value"),
                "direction": lab.get("direction", ""),
            })

    recent_events.sort(key=lambda item: item["timestamp"])
    return recent_events


def _plain_risk_label(risk_flag: str) -> str:
    labels = {
        "SEPSIS_RISK":              "a serious body-wide infection concern",
        "SEPTIC_SHOCK_RISK":        "low blood pressure related to severe infection",
        "AKI_RISK":                 "strain on the kidneys",
        "EARLY_WARNING_ESCALATION": "a need for very close monitoring",
        "COAGULOPATHY_RISK":        "blood clotting problems",
        "ARDS_RISK":                "breathing-related complications",
    }
    return labels.get(risk_flag, risk_flag.replace("_", " ").lower())


def _plain_risk_label_hindi(risk_flag: str) -> str:
    labels = {
        "SEPSIS_RISK":              "पूरे शरीर में गंभीर संक्रमण की चिंता",
        "SEPTIC_SHOCK_RISK":        "गंभीर संक्रमण के कारण बहुत कम रक्तचाप",
        "AKI_RISK":                 "गुर्दों पर दबाव या कमजोरी",
        "EARLY_WARNING_ESCALATION": "बहुत नज़दीकी निगरानी की ज़रूरत",
        "COAGULOPATHY_RISK":        "खून जमने से जुड़ी समस्या",
        "ARDS_RISK":                "सांस से जुड़ी गंभीर जटिलता",
    }
    return labels.get(risk_flag, risk_flag.replace("_", " ").lower())


def _fallback_hindi_summary(
    plain_risks: list[str],
    lab_highlights: list[str],
    symptom_highlights: list[str],
) -> str:
    parts = [
        "पिछले 12 घंटों में डॉक्टरों की टीम आपके परिवार के सदस्य की हालत पर बहुत नज़दीकी से नज़र रख रही है।"
    ]
    if symptom_highlights:
        parts.append(f"हमने कुछ महत्वपूर्ण बदलाव देखे हैं, जैसे {', '.join(symptom_highlights)}।")
    if lab_highlights:
        parts.append(f"कुछ खून की जाँचों में भी बदलाव दिखे हैं, जिनमें {', '.join(lab_highlights)} शामिल हैं।")
    if plain_risks:
        parts.append(f"इस समय टीम की सबसे बड़ी चिंता {', '.join(plain_risks)} है।")
    parts.append(
        "डॉक्टर लगातार निगरानी कर रहे हैं, ज़रूरी जाँच दोहरा रहे हैं, "
        "और मरीज की प्रतिक्रिया के अनुसार इलाज समायोजित कर रहे हैं।"
    )
    parts.append(
        "आने वाले कुछ घंटे महत्वपूर्ण हैं, और टीम किसी भी सुधार या बिगड़ने के संकेतों पर ध्यान रखेगी।"
    )
    return " ".join(parts)


def _family_fallback_summary(report: dict, recent_events: list[dict]) -> dict:
    supported_risk_flags = [
        risk.get("risk_flag", "")
        for risk in report.get("prioritized_risks", [])
        if risk.get("status", "").lower() == "supported"
    ]
    supported_risks       = [_plain_risk_label(f)       for f in supported_risk_flags]
    supported_risks_hindi = [_plain_risk_label_hindi(f) for f in supported_risk_flags]

    lab_highlights: list[str] = []
    seen_labs: set[str]       = set()
    for event in recent_events:
        if event.get("type") != "lab":
            continue
        test = str(event.get("test", "")).strip()
        if not test or test in seen_labs:
            continue
        seen_labs.add(test)
        lab_highlights.append(f"{test} {event.get('value')}")
        if len(lab_highlights) == 3:
            break

    symptom_highlights = [
        event["finding"]
        for event in recent_events
        if event.get("type") == "symptom"
    ][:3]

    parts = ["In the last 12 hours, the team has been closely watching your family member's condition."]
    if symptom_highlights:
        parts.append(f"We have seen changes such as {', '.join(symptom_highlights)}.")
    if lab_highlights:
        parts.append(f"Recent blood test changes being watched include {', '.join(lab_highlights)}.")
    if supported_risks:
        parts.append(f"Right now, the main concerns are {', '.join(supported_risks)}.")
    parts.append(
        "The doctors are continuing close monitoring, repeating important tests, "
        "and adjusting treatment based on how the patient responds."
    )
    parts.append(
        "The next few hours are important, and the team will keep watching for signs of improvement or any worsening."
    )

    english_summary  = " ".join(parts)
    regional_summary = (
        _fallback_hindi_summary(supported_risks_hindi, lab_highlights, symptom_highlights)
        if FAMILY_LANGUAGE_CODE.lower() == "hi"
        else f"[{FAMILY_LANGUAGE}] {english_summary}"
    )
    return {
        "time_window_hours":      12,
        "regional_language":      FAMILY_LANGUAGE,
        "regional_language_code": FAMILY_LANGUAGE_CODE,
        "english_summary":        english_summary,
        "regional_summary":       regional_summary,
        "generated_at":           datetime.now(timezone.utc).isoformat(),
    }


def _generate_family_communication(
    subject_id: int, hadm_id: int, report: dict, ctx: dict
) -> dict:
    recent_events = _filter_last_12_hours(ctx)

    try:
        llm    = get_llm(provider=get_active_provider(), request_timeout=60)
        prompt = ChatPromptTemplate.from_messages([
            ("system", FAMILY_SYSTEM_PROMPT),
            ("human",  FAMILY_HUMAN_PROMPT),
        ])
        chain = prompt | llm | StrOutputParser()
        raw   = chain.invoke({
            "subject_id":             subject_id,
            "hadm_id":                hadm_id,
            "regional_language":      FAMILY_LANGUAGE,
            "regional_language_code": FAMILY_LANGUAGE_CODE,
            "clinical_summary":       report.get("clinical_summary", ""),
            "prioritized_risks":      _to_json(report.get("prioritized_risks", [])),
            "recommended_actions":    _to_json(report.get("recommended_actions", [])),
            "doctor_handoff":         report.get("doctor_handoff", ""),
            "recent_findings":        _to_json(recent_events),
            "excluded_outliers":      _to_json(ctx.get("excluded_outliers", [])),
        })
        parsed           = _parse_llm_response(raw)
        english_summary  = str(parsed.get("english_summary", "")).strip()
        regional_summary = str(parsed.get("regional_summary", "")).strip()

        if not english_summary or not regional_summary:
            raise ValueError("Family summary came back empty")

        return {
            "time_window_hours":      12,
            "regional_language":      FAMILY_LANGUAGE,
            "regional_language_code": FAMILY_LANGUAGE_CODE,
            "english_summary":        english_summary,
            "regional_summary":       regional_summary,
            "generated_at":           datetime.now(timezone.utc).isoformat(),
        }

    except Exception as exc:
        logger.warning("Family communication generation failed — using fallback. Error: %s", exc)
        return _family_fallback_summary(report, recent_events)


# ── Fallback report (no LLM) ──────────────────────────────────────────────────

def _fallback_report(ctx: dict) -> dict:
    prioritized = [
        {
            "risk_flag":        c["risk_flag"],
            "status":           "supported" if c.get("criteria_met") else "possible",
            "guideline_source": c["source"],
            "explanation":      c["rationale"],
            "threshold":        c["threshold"],
        }
        for c in ctx["clean_citations"]
    ]

    lab_text = ", ".join(
        f"{i['test']} {i['value']} ({i['direction']})"
        for i in ctx["clean_labs"]
    ) or "No retained critical labs"

    return {
        "primary_concern": prioritized[0]["risk_flag"] if prioritized else "Undetermined",
        "clinical_summary": (
            f"Report generated from structured agent outputs after outlier removal. "
            f"Retained lab evidence: {lab_text}. LLM synthesis unavailable."
        ),
        "prioritized_risks":   prioritized,
        "recommended_actions": [
            "Review prioritized risks with attending clinician.",
            "Cross-check retained labs against bedside observation.",
            "Reassess on next clinical review cycle.",
        ],
        "doctor_handoff": (
            "LLM synthesis failed — report built from structured data only. "
            "Manual review of raw agent outputs is advised."
        ),
        "disease_progression": [],
    }


def _to_json(value) -> str:
    """Serialize value to a JSON string. Nothing else — no dead code here."""
    return json.dumps(value, indent=2, default=str)


def run_chief_agent(unified_input: dict | str | Path) -> dict:
    """
    Chief Agent pipeline:
      1. Load unified JSON from orchestrator
      2. Detect and remove outliers (four-layer check)
      3. Call LLM with clean context
      4. Attach metadata
      5. Persist to MongoDB   ← was dead code inside _to_json; now correctly placed
      6. Return final report
    """
    if isinstance(unified_input, (str, Path)):
        with open(unified_input, "r", encoding="utf-8") as f:
            unified = json.load(f)
    else:
        unified = unified_input

    subject_id = unified["pipeline_run"]["subject_id"]
    hadm_id    = unified["pipeline_run"]["hadm_id"]

    ctx = _build_clean_context(unified, subject_id, hadm_id)
    logger.info(
        "Chief Agent — %d symptoms | %d clean labs | %d outliers excluded",
        len(ctx["symptoms"]), len(ctx["clean_labs"]), len(ctx["excluded_outliers"]),
    )

    try:
        report = _call_llm(subject_id, hadm_id, ctx)
    except Exception as e:
        logger.warning("LLM call failed — using fallback. Error: %s", e)
        report = _fallback_report(ctx)

    family_communication = _generate_family_communication(
        subject_id=subject_id,
        hadm_id=hadm_id,
        report=report,
        ctx=ctx,
    )

    report.update({
        "agent":             "chief_agent",
        "subject_id":        subject_id,
        "hadm_id":           hadm_id,
        "generated_at":      datetime.now(timezone.utc).isoformat(),
        "excluded_outliers": ctx["excluded_outliers"],
        "outlier_summary": {
            "total_checked":  len(ctx["clean_labs"]) + len(ctx["excluded_outliers"]),
            "total_excluded": len(ctx["excluded_outliers"]),
            "by_layer": {
                "physiological":       sum(1 for e in ctx["excluded_outliers"] if e["layer"] == "physiological"),
                "current_admission":   sum(1 for e in ctx["excluded_outliers"] if e["layer"] == "current_admission"),
                "historical_baseline": sum(1 for e in ctx["excluded_outliers"] if e["layer"] == "historical_baseline"),
                "realtime_delta":      sum(1 for e in ctx["excluded_outliers"] if e["layer"] == "realtime_delta"),
            },
        },
        "data_quality": {
            "note_parser_available":  unified["data_completeness"]["note_parser_available"],
            "lab_mapper_available":   unified["data_completeness"]["lab_mapper_available"],
            "rag_available":          unified["data_completeness"]["rag_available"],
            "outliers_removed_count": len(ctx["excluded_outliers"]),
            "sofa_coverage_pct":      unified["data_completeness"]["sofa_coverage_pct"],
        },
        "family_communication": family_communication,
    })

    try:
        ensure_indexes()
        mongo_id = save_chief_report(report)
        report["mongo_id"] = mongo_id
        logger.info("Report persisted to MongoDB with _id=%s", mongo_id)
    except Exception as exc:
        logger.error(
            "MongoDB persistence failed — report still returned. Error: %s", exc
        )
        report["mongo_id"] = None

    return report


def save_chief_output(report: dict) -> Path:
    sid = report["subject_id"]
    hid = report["hadm_id"]
    ts  = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    out_dir = OUTPUT_BASE / f"sub_{sid}" / f"hadm_{hid}"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / f"chief_report_{ts}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info("Chief report saved → %s", out_file)
    return out_file


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")

    root  = Path("backend/outputs/orchestrator")
    files = sorted(root.rglob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError("No orchestrator output found. Run orchestrator first.")

    report   = run_chief_agent(files[0])
    out_file = save_chief_output(report)
    print(json.dumps(report, indent=2))
    print(f"\nSaved to disk → {out_file}")
    print(f"Saved to MongoDB → _id={report.get('mongo_id')}")