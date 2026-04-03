# main.py
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import asyncio
from fastapi.responses import StreamingResponse

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from backend.agents.chief_agent import run_chief_agent, save_chief_output
    from backend.agents.orchestra import run_pipeline
except ModuleNotFoundError:
    from agents.chief_agent import run_chief_agent, save_chief_output
    from agents.orchestra import run_pipeline

load_dotenv(Path(__file__).resolve().parents[0] / ".env")

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ICU Clinical Decision Support API",
    description="Multi-agent pipeline: NoteParser → LabMapper → RAG → Chief Agent",
    version="1.0.0",
)

# Frontend connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUTS_BASE = Path("backend/outputs")
@app.get("/stream/{subject_id}/{hadm_id}")
async def stream_patient(subject_id: int, hadm_id: int):
    """
    Server-Sent Events stream for a patient.
    Frontend connects once — server pushes updates when new data arrives.
    Shows the judge that the system is truly real-time.
    """
    async def event_generator():
        last_report_time = None

        while True:
            # Check if a newer chief report exists on disk
            report = _latest_chief_report(subject_id, hadm_id)

            if report:
                report_time = report.get("generated_at", "")
                if report_time != last_report_time:
                    last_report_time = report_time
                    # Push the update to frontend
                    payload = json.dumps({
                        "subject_id":     subject_id,
                        "hadm_id":        hadm_id,
                        "primary_concern": report.get("primary_concern", ""),
                        "generated_at":   report_time,
                        "data_quality":   report.get("data_quality", {}),
                    })
                    yield f"data: {payload}\n\n"

            # Heartbeat every 5s so connection stays alive
            yield f": heartbeat\n\n"
            await asyncio.sleep(5)
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


#Request/Response schemas
class AnalyzeRequest(BaseModel):
    subject_id: int
    hadm_id:    int

class AnalyzeResponse(BaseModel):
    subject_id:       int
    hadm_id:          int
    status:           str          
    agents_succeeded: list[str]
    agents_failed:    list[str]
    primary_concern:  str
    clinical_summary: str
    prioritized_risks: list[dict]
    recommended_actions: list[str]
    excluded_outliers:   list[dict]
    data_quality:        dict
    doctor_handoff:      str
    generated_at:        str
    disease_timeline:    list[dict]   
    safety_disclaimer:   str


#Helpers 

def _build_disease_timeline(unified: dict) -> list[dict]:
    """
    Merge note symptoms + lab timeline into one chronological list.
    This is deliverable 2 — disease progression timeline.
    """
    events: list[dict] = []

    # Symptom events from NoteParser
    for pt in unified.get("note_parser_output", {}).get("patient_timelines", []):
        for slot in pt.get("symptom_timeline", []):
            events.append({
                "timestamp":  slot["timestamp"],
                "source":     "clinical_note",
                "note_type":  slot.get("note_type", ""),
                "findings":   slot.get("findings", []),
            })

    # Lab events from LabMapper 
    for test, timeline in unified.get("lab_mapper_output", {}).get("timeline_by_test", {}).items():
        for entry in timeline:
            events.append({
                "timestamp": entry["timestamp"],
                "source":    "lab_result",
                "test":      test,
                "value":     entry["value"],
                "unit":      entry.get("unit", ""),
                "trend":     entry.get("trend", "stable"),
                "above_normal": entry.get("above_normal", False),
                "below_normal": entry.get("below_normal", False),
                "is_outlier":   entry.get("outlier", {}).get("is_outlier", False),
                "aki_stage":    entry.get("aki_stage"),
            })

    # Sort everything chronologically
    events.sort(key=lambda x: x["timestamp"])
    return events


def _latest_chief_report(subject_id: int, hadm_id: int) -> dict | None:
    """Read the most recently saved chief report for this patient from disk."""
    report_dir = OUTPUTS_BASE / "chief_agent" / f"sub_{subject_id}" / f"hadm_{hadm_id}"
    if not report_dir.exists():
        return None
    files = sorted(report_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        return None
    with open(files[0], "r", encoding="utf-8") as f:
        return json.load(f)


def _build_response(chief_report: dict, unified: dict) -> AnalyzeResponse:
    """Assemble the final API response from chief report + unified pipeline output."""
    pipeline = unified.get("pipeline_run", {})

    return AnalyzeResponse(
        subject_id          = chief_report["subject_id"],
        hadm_id             = chief_report["hadm_id"],
        status              = (
            "success" if pipeline.get("agents_failed") == []
            else "partial" if pipeline.get("agents_succeeded")
            else "failed"
        ),
        agents_succeeded    = pipeline.get("agents_succeeded", []),
        agents_failed       = pipeline.get("agents_failed", []),
        primary_concern     = chief_report.get("primary_concern", ""),
        clinical_summary    = chief_report.get("clinical_summary", ""),
        prioritized_risks   = chief_report.get("prioritized_risks", []),
        recommended_actions = chief_report.get("recommended_actions", []),
        excluded_outliers   = chief_report.get("excluded_outliers", []),
        data_quality        = chief_report.get("data_quality", {}),
        doctor_handoff      = chief_report.get("doctor_handoff", ""),
        generated_at        = chief_report.get("generated_at", ""),
        disease_timeline    = _build_disease_timeline(unified),
        safety_disclaimer   = (
            "⚠ DECISION SUPPORT ONLY — All outputs are AI-generated and must be "
            "reviewed by a qualified clinician before influencing patient care. "
            "This system does not provide a clinical diagnosis."
        ),
    )


#Routes 
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ICU Clinical Decision Support API"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_patient(req: AnalyzeRequest):
    groq_api_key = os.getenv("GROQ_API_KEY", "")
    if not groq_api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured.")

    logger.info("POST /analyze — subject=%s hadm=%s", req.subject_id, req.hadm_id)

    #run orchestrator
    try:
        unified = run_pipeline(
            subject_id   = req.subject_id,
            hadm_id      = req.hadm_id,
            groq_api_key = groq_api_key,
        )
    except Exception as e:
        logger.error("Orchestrator failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Orchestrator error: {e}")

    #run Chief Agent
    try:
        chief_report = run_chief_agent(unified)
        save_chief_output(chief_report)
    except Exception as e:
        logger.error("Chief Agent failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Chief Agent error: {e}")

    return _build_response(chief_report, unified)


@app.get("/report/{subject_id}/{hadm_id}", response_model=AnalyzeResponse)
def get_cached_report(subject_id: int, hadm_id: int):
    """
    Returns the latest saved chief report for this patient instantly.
    """
    logger.info("GET /report — subject=%s hadm=%s", subject_id, hadm_id)

    chief_report = _latest_chief_report(subject_id, hadm_id)
    if not chief_report:
        raise HTTPException(
            status_code=404,
            detail=f"No report found for subject={subject_id} hadm={hadm_id}. Run /analyze first."
        )

    # Reconstruct unified for timeline
    orchestrator_dir = (
        OUTPUTS_BASE / "orchestrator" / f"sub_{subject_id}" / f"hadm_{hadm_id}"
    )
    unified: dict = {}
    if orchestrator_dir.exists():
        files = sorted(
            orchestrator_dir.glob("*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if files:
            with open(files[0], "r", encoding="utf-8") as f:
                unified = json.load(f)

    return _build_response(chief_report, unified)


@app.get("/patients")
def list_analyzed_patients():
    """
    Returns all patient IDs that have been analyzed and have saved reports.
    Frontend uses this to populate the patient list sidebar.
    """
    chief_base = OUTPUTS_BASE / "chief_agent"
    patients = []

    if not chief_base.exists():
        return {"patients": []}

    for sub_dir in sorted(chief_base.iterdir()):
        if not sub_dir.is_dir() or not sub_dir.name.startswith("sub_"):
            continue
        subject_id = sub_dir.name.replace("sub_", "")
        for hadm_dir in sorted(sub_dir.iterdir()):
            if not hadm_dir.is_dir() or not hadm_dir.name.startswith("hadm_"):
                continue
            hadm_id = hadm_dir.name.replace("hadm_", "")
            files = sorted(hadm_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
            if files:
                patients.append({
                    "subject_id":   int(subject_id),
                    "hadm_id":      int(hadm_id),
                    "last_analyzed": files[0].stat().st_mtime,
                })

    return {"patients": sorted(patients, key=lambda x: x["last_analyzed"], reverse=True)}
