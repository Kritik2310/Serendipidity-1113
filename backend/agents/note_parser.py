from __future__ import annotations
import csv
import json
import logging
import os
import re
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from groq import Groq

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

logger = logging.getLogger(__name__)

# Max notes sent to LLM per patient
MAX_NOTES = 10

# Priority order
CATEGORY_PRIORITY = ["Physician", "Nursing/Other", "Nursing"]

SYSTEM_PROMPT = """You are a clinical NLP specialist.
Extract structured medical findings from ICU notes.
Return ONLY a JSON array. Each object must contain:
{
  "symptom": "name",
  "severity": "mild | moderate | severe | critical | unknown",
  "category": "vital_sign | symptom | lab_result | medication | procedure | diagnosis | mental_status | fluid_output | other",
  "value": number or null,
  "unit": string or null,
  "trend": "improving | worsening | stable | new | unknown",
  "raw_text": "exact phrase from note"
}"""


#Data loading 

def _load_patient_notes(file_path: str, subject_id: int, hadm_id: int) -> list[dict]:
    """Load CSV, filter to one patient, drop errors, sort chronologically."""
    df = pd.read_csv(file_path, dtype={"subject_id": int, "hadm_id": int})

    # Filter to this patient only done before any other processing
    df = df[(df["subject_id"] == subject_id) & (df["hadm_id"] == hadm_id)]

    # Drop error flagged and empty notes
    df = df[df["iserror"] != 1]
    df = df[df["text"].notna() & (df["text"].str.strip() != "")]

    #Sort chronologically 
    df["charttime"] = pd.to_datetime(df["charttime"], errors="coerce")
    df = df.sort_values("charttime", ascending=True).reset_index(drop=True)

    return df.to_dict("records")


def _select_notes(notes: list[dict]) -> list[dict]:
    """
    Pick up to MAX_NOTES notes, prioritising by clinical weight.
    """
    buckets: dict[str, list] = {cat: [] for cat in CATEGORY_PRIORITY}
    other: list[dict] = []

    for note in notes:
        cat = note.get("category", "")
        if cat in buckets:
            buckets[cat].append(note)
        else:
            other.append(note)

    # Slots 
    limits = {"Physician": 4, "Nursing/Other": 3, "Nursing": 3}
    selected: list[dict] = []

    for cat in CATEGORY_PRIORITY:
        pool = buckets[cat]
        selected.extend(pool[-limits[cat]:]) 

    # Fill remaining slots with any uncategorised notes
    remaining = MAX_NOTES - len(selected)
    if remaining > 0:
        selected.extend(other[-remaining:])

    return selected[:MAX_NOTES]


#LLM extraction 
def _extract_findings(note: dict, client: Groq) -> list[dict]:
    """Send one note to Groq, parse JSON response. Returns [] on any failure."""
    user_msg = (
        f"Note Type: {note.get('category', 'Unknown')}\n"
        f"Timestamp: {note.get('charttime', '')}\n\n"
        f"NOTE:\n{note['text']}"
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0,
            max_tokens=1500,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
        )
        raw = response.choices[0].message.content.strip()
        return _parse_llm_response(raw, note)

    except Exception as e:
        logger.warning("Note %s skipped: %s", note.get("row_id"), e)
        return []

def _parse_llm_response(raw: str, note: dict) -> list[dict]:
    clean = re.sub(r"```json|```", "", raw).strip()

    try:
        data = json.loads(clean)
    except json.JSONDecodeError:
        logger.warning("JSON parse failed for note %s", note.get("row_id"))
        return []

    findings = []
    for item in data:
        if not isinstance(item, dict) or not item.get("symptom"):
            continue
        findings.append({
            "subject_id": note["subject_id"],
            "hadm_id":    note["hadm_id"],
            "timestamp":  str(note.get("charttime", "")),
            "note_type":  note.get("category", "Unknown"),
            "symptom":    item.get("symptom", "").lower().strip(),
            "severity":   item.get("severity", "unknown"),
            "category":   item.get("category", "other"),
            "value":      item.get("value"),
            "unit":       item.get("unit"),
            "trend":      item.get("trend", "unknown"),
            "raw_text":   item.get("raw_text", ""),
        })
    return findings

#Output assembly 
def _build_timeline(findings: list[dict]) -> list[dict]:
    """Group findings by timestamp into a chronological timeline."""
    slots: dict[str, dict] = {}

    for f in findings:
        ts = f["timestamp"]
        if ts not in slots:
            slots[ts] = {
                "timestamp": ts,
                "note_type": f["note_type"],
                "findings":  [],
            }
        slots[ts]["findings"].append({
            "symptom":  f["symptom"],
            "severity": f["severity"],
            "category": f["category"],
            "value":    f["value"],
            "unit":     f["unit"],
            "trend":    f["trend"],
            "raw_text": f["raw_text"],
        })

    return sorted(slots.values(), key=lambda x: x["timestamp"])
def _build_parsed_symptoms(findings: list[dict]) -> list[dict]:
    """Flat symptom list consumed by the RAG agent."""
    return [
        {
            "finding":   f["symptom"],
            "severity":  f["severity"],
            "raw_text":  f["raw_text"],
            "timestamp": f["timestamp"],
            "trend":     f["trend"],
        }
        for f in findings
    ]


def _build_flagged_risks(findings: list[dict]) -> list[str]:
    HIGH_SEVERITY = {"moderate", "severe", "critical"}
    seen, flagged = set(), []
    for f in findings:
        if f["severity"] in HIGH_SEVERITY and f["symptom"] not in seen:
            seen.add(f["symptom"])
            flagged.append(f["symptom"])
    return flagged


#Public entry point 
def run_parser(file_path: str, api_key: str, subject_id: int, hadm_id: int) -> dict:
    #load and filter to this patient
    all_notes = _load_patient_notes(file_path, subject_id, hadm_id)

    if not all_notes:
        logger.warning("No notes found for subject=%s hadm=%s", subject_id, hadm_id)
        return _empty_result(subject_id, hadm_id, reason="No notes found in CSV")
    #select up to max_notes by clinical priority
    selected = _select_notes(all_notes)
    logger.info("Processing %d/%d notes for subject=%s", len(selected), len(all_notes), subject_id)

    #extract findings from each note via Groq
    client = Groq(api_key=api_key)
    all_findings: list[dict] = []

    for i, note in enumerate(selected, 1):
        logger.info("  Note %d/%d — %s", i, len(selected), note.get("category"))
        findings = _extract_findings(note, client)
        all_findings.extend(findings)

    #assemble output
    timeline = _build_timeline(all_findings)
    parsed_symptoms = _build_parsed_symptoms(all_findings)
    flagged_risks = _build_flagged_risks(all_findings)

    return {
        "agent":      "note_parser",
        "subject_id": subject_id,
        "hadm_id":    hadm_id,
        "summary": {
            "total_findings":  len(all_findings),
            "notes_processed": len(selected),
            "notes_available": len(all_notes),
        },
        "patient_timelines": [
            {
                "patient_id":       subject_id,
                "admission_id":     hadm_id,
                "symptom_timeline": timeline,
            }
        ],
        "parsed_symptoms": parsed_symptoms,
        "flagged_risks":   flagged_risks,
    }
def _empty_result(subject_id: int, hadm_id: int, reason: str = "") -> dict:
    return {
        "agent":             "note_parser",
        "subject_id":        subject_id,
        "hadm_id":           hadm_id,
        "summary":           {"total_findings": 0, "notes_processed": 0, "notes_available": 0},
        "patient_timelines": [],
        "parsed_symptoms":   [],
        "flagged_risks":     [],
        "note":              reason,
    }


# Helper
def save_note_parser_output(result: dict, base_dir: str = "backend/outputs") -> Path:
    from datetime import datetime
    sid = result["subject_id"]
    hid = result["hadm_id"]
    ts  = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    out_dir = Path(base_dir) / "note_parser" / f"sub_{sid}" / f"hadm_{hid}"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / f"note_parser_{ts}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    logger.info("Saved: %s", out_file)
    return out_file
# Standalone run 
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")

    result = run_parser(
        file_path  = "backend/data/NOTEEVENTS1.csv",
        api_key    = os.getenv("GROQ_API_KEY"),
        subject_id = 10002,
        hadm_id    = 198765,
    )

    out_file = save_note_parser_output(result)
    print(json.dumps(result["summary"], indent=2))
    print(f"Flagged risks : {result['flagged_risks']}")
    print(f"Saved         : {out_file}")