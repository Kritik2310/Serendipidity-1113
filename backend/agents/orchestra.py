from __future__ import annotations
import datetime
import json
import logging
import threading
from pathlib import Path
from backend.agents.note_parser import run_parser
from backend.agents.lab_mapper  import run_lab_mapper
from backend.agents.rag_agent   import run_rag_agent

logger = logging.getLogger(__name__)

OUTPUT_BASE      = Path("backend/outputs")
NOTEEVENTS_PATH  = "backend/data/NOTEEVENTS1.csv"
LABEVENTS_PATH   = "backend/data/LABEVENTS.csv"
ICUSTAYS_PATH    = "backend/data/ICUSTAYS.csv"
GUIDELINES_PATH  = "backend/data/icu_clinical_guidelines.pdf"


class OrchestratorAgent:

    def __init__(self, groq_api_key: str):
        self.groq_api_key = groq_api_key

    #parallel agent execution
    def _run_note_parser(
        self, subject_id: int, hadm_id: int,
        results: dict, errors: dict,
    ) -> None:
        """Thread target — runs NoteParser for this patient only."""
        try:
            results["note_parser"] = run_parser(
                file_path  = NOTEEVENTS_PATH,
                api_key    = self.groq_api_key,
                subject_id = subject_id,
                hadm_id    = hadm_id,
            )
        except Exception as e:
            logger.error("NoteParser failed: %s", e)
            errors["note_parser"] = str(e)
            results["note_parser"] = None

    def _run_lab_mapper(
        self, subject_id: int, hadm_id: int,
        results: dict, errors: dict,
    ) -> None:
        """Thread target — runs LabMapper for this patient only."""
        try:
            results["lab_mapper"] = run_lab_mapper({
                "subject_id": subject_id,
                "hadm_id":    hadm_id,
            })
        except Exception as e:
            logger.error("LabMapper failed: %s", e)
            errors["lab_mapper"] = str(e)
            results["lab_mapper"] = None

    def _run_parallel(
        self, subject_id: int, hadm_id: int,
    ) -> tuple[dict, dict]:
        """Fire both agents simultaneously, block until both finish."""
        results: dict = {}
        errors:  dict = {}

        t1 = threading.Thread(
            target=self._run_note_parser,
            args=(subject_id, hadm_id, results, errors),
        )
        t2 = threading.Thread(
            target=self._run_lab_mapper,
            args=(subject_id, hadm_id, results, errors),
        )

        t1.start(); t2.start()
        t1.join();  t2.join()

        return results, errors

    #build RAG inputs 
    def _build_rag_inputs(
        self,
        note_output: dict | None,
        lab_output:  dict | None,
    ) -> tuple[list[dict], list[dict]]:
        parsed_symptoms = note_output.get("parsed_symptoms", []) if note_output else []

        critical_values = lab_output.get("critical_values", []) if lab_output else []
        # Add abnormal values not already in critical_values
        seen = {cv["test"] for cv in critical_values}
        for av in (lab_output.get("abnormal_values", []) if lab_output else []):
            if av["test"] not in seen:
                critical_values.append({
                    "test":       av["test"],
                    "value":      av["value"],
                    "direction":  av["type"],
                    "timestamp":  av["timestamp"],
                    "is_outlier": False,
                })
                seen.add(av["test"])

        return parsed_symptoms, critical_values

    #merge flagged risks for Chief Agent
    def _build_flagged_risks(
        self,
        note_output: dict | None,
        lab_output:  dict | None,
    ) -> list[dict]:
        """
        Single deduplicated risk list from both agents.
        """
        flagged: list[dict] = []

        # Symptom-based risks from NoteParser
        for symptom in (note_output.get("flagged_risks", []) if note_output else []):
            flagged.append({
                "source": "note_parser",
                "type":   "symptom",
                "signal": symptom,
            })

        if lab_output:
            # Critical lab values 
            for cv in lab_output.get("critical_values", []):
                if not cv.get("is_outlier", False):
                    flagged.append({
                        "source":    "lab_mapper",
                        "type":      "critical_lab",
                        "signal":    cv["test"],
                        "value":     cv["value"],
                        "direction": cv["direction"],
                        "timestamp": cv["timestamp"],
                    })

            # Statistical outliers 
            for entry in lab_output.get("outlier_flags", []):
                flagged.append({
                    "source":    "lab_mapper",
                    "type":      "outlier_flag",
                    "signal":    entry["test"],
                    "value":     entry["value"],
                    "z_score":   entry["z_score"],
                    "timestamp": entry["timestamp"],
                })

            # AKI stage signals from lab timeline
            for lab, timeline in lab_output.get("timeline_by_test", {}).items():
                for entry in timeline:
                    stage = entry.get("aki_stage")
                    if stage and stage != "No AKI":
                        flagged.append({
                            "source":    "lab_mapper",
                            "type":      "aki_stage",
                            "signal":    f"AKI {stage}",
                            "value":     entry["value"],
                            "timestamp": entry["timestamp"],
                        })

        # Deduplicate by source,signal
        seen, unique = set(), []
        for f in flagged:
            key = (f["source"], f["signal"])
            if key not in seen:
                seen.add(key)
                unique.append(f)

        return unique

    #assemble unified JSON 
    def _assemble(
        self,
        subject_id:    int,
        hadm_id:       int,
        note_output:   dict | None,
        lab_output:    dict | None,
        rag_output:    dict,
        flagged_risks: list[dict],
        errors:        dict,
        start_time:    datetime.datetime,
    ) -> dict:

        duration_ms = int(
            (datetime.datetime.utcnow() - start_time).total_seconds() * 1000
        )

        return {
            "pipeline_run": {
                "orchestrator":     "OrchestratorAgent v1.2",
                "subject_id":       subject_id,
                "hadm_id":          hadm_id,
                "run_timestamp":    start_time.isoformat() + "Z",
                "duration_ms":      duration_ms,
                "agents_succeeded": [
                    k for k, v in {
                        "note_parser": note_output,
                        "lab_mapper":  lab_output,
                        "rag_agent":   rag_output,
                    }.items() if v is not None
                ],
                "agents_failed": list(errors.keys()),
                "errors":        errors,
            },
            "note_parser_output":    note_output or {"agent": "note_parser", "status": "failed"},
            "lab_mapper_output":     lab_output  or {"agent": "lab_mapper",  "status": "failed"},
            "rag_guidelines_output": rag_output,
            "flagged_risks":         flagged_risks,
            "outlier_flags": (
                lab_output.get("outlier_flags", []) if lab_output else []
            ),
            "data_completeness": {
                "note_parser_available": note_output is not None,
                "lab_mapper_available":  lab_output  is not None,
                "rag_available": bool(rag_output.get("citations")),
                "sofa_coverage_pct":    (
                    lab_output.get("sofa_coverage_pct", 0.0) if lab_output else 0.0
                ),
                "labs_available":       (
                    lab_output.get("labs_available", []) if lab_output else []
                ),
                "total_flagged_risks":  len(flagged_risks),
                "outlier_flags_active": len(
                    lab_output.get("outlier_flags", []) if lab_output else []
                ),
                "guidelines_retrieved": rag_output.get("guidelines_retrieved", 0),
            },
        }

    #Save 
    def _save(self, unified: dict) -> Path:
        sid = unified["pipeline_run"]["subject_id"]
        hid = unified["pipeline_run"]["hadm_id"]
        ts  = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

        out_dir = OUTPUT_BASE / "orchestrator" / f"sub_{sid}" / f"hadm_{hid}"
        out_dir.mkdir(parents=True, exist_ok=True)

        out_file = out_dir / f"unified_{ts}.json"
        with open(out_file, "w") as f:
            json.dump(unified, f, indent=2, default=str)

        logger.info("Saved → %s", out_file)
        return out_file

    #Main entry point 

    def run(self, subject_id: int, hadm_id: int) -> dict:
        start_time = datetime.datetime.utcnow()
        logger.info("Pipeline start — subject=%s  hadm=%s", subject_id, hadm_id)

        #Run NoteParser + LabMapper in parallel
        results, errors = self._run_parallel(subject_id, hadm_id)
        note_output = results.get("note_parser")
        lab_output  = results.get("lab_mapper")

        logger.info(
            "Agents done — NoteParser=%s | LabMapper=%s",
            "OK" if note_output else "FAILED",
            "OK" if lab_output  else "FAILED",
        )

        #Build RAG inputs from merged findings
        parsed_symptoms, critical_values = self._build_rag_inputs(
            note_output, lab_output
        )
        logger.info(
            "RAG inputs — %d symptoms, %d lab values",
            len(parsed_symptoms), len(critical_values),
        )

        #Build deduplicated flagged risks
        flagged_risks = self._build_flagged_risks(note_output, lab_output)
        logger.info("%d unique flagged risks", len(flagged_risks))

        #RAG
        if parsed_symptoms or critical_values:
            rag_output = run_rag_agent(parsed_symptoms, critical_values)
        else:
            # No findings from either agent —skip RAG 
            rag_output = {
                "agent":               "guideline_rag",
                "query_used":          "",
                "citations":           [],
                "guidelines_retrieved": 0,
                "top_relevance_score": 0,
                "note": "Skipped — no findings available",
            }

        logger.info(
            "RAG done — %d citations, top_score=%s",
            rag_output.get("guidelines_retrieved", 0),
            rag_output.get("top_relevance_score", 0),
        )
        # Assemble unified JSON
        unified = self._assemble(
            subject_id, hadm_id,
            note_output, lab_output, rag_output,
            flagged_risks, errors, start_time,
        )
        self._save(unified)
        logger.info(
            "Pipeline complete — %dms", unified["pipeline_run"]["duration_ms"]
        )
        return unified
    
#Convenience runner 
def run_pipeline(subject_id: int, hadm_id: int, groq_api_key: str) -> dict:
    return OrchestratorAgent(groq_api_key).run(subject_id, hadm_id)

if __name__ == "__main__":
    import os
    logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
    from dotenv import load_dotenv
    load_dotenv()

    result = run_pipeline(
        subject_id    = 10002,
        hadm_id       = 198765,
        groq_api_key  = os.getenv("GROQ_API_KEY"),
    )
    print(json.dumps(result["data_completeness"], indent=2))