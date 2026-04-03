import csv
import json
import os
import re
from dotenv import load_dotenv
from groq import Groq

def load_notes_from_csv(file_path):
    notes = []
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            text = row.get("text", "").strip()

            if not text or row.get("iserror") == "1":
                continue

            notes.append({
                "row_id": row.get("row_id"),
                "subject_id": row.get("subject_id"),
                "hadm_id": row.get("hadm_id"),
                "note_type": row.get("category", "Unknown"),
                "timestamp": row.get("charttime") or row.get("chartdate"),
                "text": text
            })

    return notes


SYSTEM_PROMPT = """You are a clinical NLP specialist.

Extract structured medical findings from ICU notes.

Return ONLY a JSON array.

Each object must contain:
{
  "symptom": "name",
  "severity": "mild | moderate | severe | critical | unknown",
  "category": "vital_sign | symptom | lab_result | medication | procedure | diagnosis | mental_status | fluid_output | other",
  "value": number or null,
  "unit": string or null,
  "trend": "improving | worsening | stable | new | unknown",
  "raw_text": "exact phrase from note"
}
"""

def extract_findings(note, client):
    user_msg = f"""
Note Type: {note['note_type']}
Timestamp: {note['timestamp']}

NOTE:
{note['text']}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0,
        max_tokens=1500,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]
    )

    return response.choices[0].message.content.strip()

def parse_response(raw, note):
    clean = raw.strip()
    clean = re.sub(r"```json", "", clean)
    clean = re.sub(r"```", "", clean)

    try:
        data = json.loads(clean)
    except:
        return []
    
    findings = []

    for item in data:
        if not isinstance(item, dict):
            continue
        findings.append({
            "subject_id": note["subject_id"],
            "hadm_id": note["hadm_id"],
            "timestamp": note["timestamp"],
            "note_type": note["note_type"],
            "symptom": item.get("symptom", "").lower(),
            "severity": item.get("severity", "unknown"),
            "category": item.get("category", "other"),
            "value": item.get("value"),
            "unit": item.get("unit"),
            "trend": item.get("trend", "unknown"),
            "raw_text": item.get("raw_text", "")
        })

    return findings

def patient_timeline(findings):
    patients = {}
    for f in findings:
        key = f["subject_id"] + "_" + f["hadm_id"]
        if key not in patients:
            patients[key] = {
                "patient_id": f["subject_id"],
                "admission_id": f["hadm_id"],
                "symptom_timeline": {}
            }

        timeline = patients[key]["symptom_timeline"]
        ts = f["timestamp"]

        if ts not in timeline:
            timeline[ts] = {
                "timestamp": ts,
                "note_type": f["note_type"],
                "findings": []
            }

        timeline[ts]["findings"].append({
            "symptom": f["symptom"],
            "severity": f["severity"],
            "category": f["category"],
            "value": f["value"],
            "unit": f["unit"],
            "trend": f["trend"],
            "raw_text": f["raw_text"]
        })

    final_output = []

    for patient in patients.values():
        timeline_list = list(patient["symptom_timeline"].values())
        timeline_list.sort(key=lambda x: x["timestamp"])

        patient["symptom_timeline"] = timeline_list
        final_output.append(patient)

    return final_output

def summary(findings):
    return{
        "total_findings": len(findings),
        "unique_patients": len(set(f["subject_id"] for f in findings))
    }

def run_parser(file_path, api_key):
    notes = load_notes_from_csv(file_path)
    print(f"Loaded {len(notes)} notes from CSV.")

    if notes:
        print("Sample Note:", notes[0])

    client = Groq(api_key=api_key)

    all_findings = []

    for i, note in enumerate(notes):
        print(f"Processing {i+1}/{len(notes)}")

        try:
            raw = extract_findings(note, client)
            findings = parse_response(raw, note)

            print(f" - {len(findings)} findings")

            all_findings.extend(findings)

        except Exception as e:
            print("Error:", e)
            continue

    patient_data = patient_timeline(all_findings)

    result = {
        "agent": "note_parser",
        "summary": summary(all_findings),
        "patient_timelines": patient_data   
    }

    return result


if __name__ == "__main__":
    load_dotenv()
    FILE_PATH = "backend/data/NOTEEVENTS1.csv" 
    API_KEY = os.getenv("GROQ_API_KEY")
    result = run_parser(FILE_PATH, API_KEY)
    with open("note_parser_output.json", "w") as f:
        json.dump(result, f, indent=2)

    print("Done. Output saved to note_parser_output.json")
    print(json.dumps(result["summary"], indent=2))