# orchestrator.py
from __future__ import annotations

import json
import threading
import datetime
from pathlib import Path

from backend.agents.note_parser import run_parser
from backend.agents.lab_mapper  import run_lab_mapper
from backend.agents.rag_agent   import run_rag_agent

OUTPUT_BASE = Path("backend/outputs")

# ── Config: point to your CSV/PDF files ───────────────────────────────────────
NOTEEVENTS_PATH  = "backend/data/NOTEEVENTS1.csv"
LABEVENTS_PATH   = "backend/data/LABEVENTS.csv"   
ICUSTAYS_PATH    = "backend/data/ICUSTAYS.csv"    
GUIDELINES_PATH  = "backend/data/icu_clinical_guidelines.pdf" 


class OrchestratorAgent:
    """
    Step-by-step pipeline
    ──────────────────────
    1. Receive subject_id + hadm_id
    2. Run NoteParser  (NOTEEVENTS1.csv) ──┐
       Run LabMapper   (LABEVENTS.csv   ──┤── parallel threads
                      + ICUSTAYS.csv)     ┘
    3. Extract flagged risks from both outputs
    4. Send parsed_symptoms + critical_values to RAG agent
    5. Assemble unified JSON → Chief Agent
    """

    def __init__(self, groq_api_key: str):
        self.groq_api_key = groq_api_key

    # ── STEP 2: parallel execution ─────────────────────────────────────────────

    def _run_note_parser(
        self, subject_id: int, hadm_id: int,
        results: dict, errors: dict
    ):
        """
        Thread target for NoteParser.
        run_parser(file_path, api_key) → full result dict
        Then we filter down to this patient's timelines.
        """
        try:
            full_result = run_parser(NOTEEVENTS_PATH, self.groq_api_key)

            # Filter to only this patient's timelines
            patient_timelines = [
                pt for pt in full_result.get("patient_timelines", [])
                if (
                    str(pt.get("patient_id"))   == str(subject_id) and
                    str(pt.get("admission_id")) == str(hadm_id)
                )
            ]

            # Flatten symptoms for RAG — note_parser stores findings per timestamp
            parsed_symptoms = []
            for pt in patient_timelines:
                for slot in pt.get("symptom_timeline", []):
                    for finding in slot.get("findings", []):
                        parsed_symptoms.append({
                            "finding":   finding.get("symptom", ""),
                            "severity":  finding.get("severity", "unknown"),
                            "raw_text":  finding.get("raw_text", ""),
                            "timestamp": slot.get("timestamp"),
                            "trend":     finding.get("trend", "unknown"),
                        })

            results["note_parser"] = {
                "agent":            "note_parser",
                "subject_id":       subject_id,
                "hadm_id":          hadm_id,
                "summary":          full_result.get("summary", {}),
                "patient_timelines": patient_timelines,
                # ← this key is what orchestrator hands to RAG
                "parsed_symptoms":  parsed_symptoms,
                # flagged_risks: symptoms with severity moderate/severe/critical
                "flagged_risks": [
                    s["finding"] for s in parsed_symptoms
                    if s.get("severity") in ("moderate", "severe", "critical")
                ],
            }

        except Exception as e:
            errors["note_parser"] = str(e)
            results["note_parser"] = None

    def _run_lab_mapper(
        self, subject_id: int, hadm_id: int,
        results: dict, errors: dict
    ):
        """
        Thread target for LabMapper.
        run_lab_mapper({"subject_id": ..., "hadm_id": ...}) → result dict
        LabMapperAgent reads its own CSV paths internally.
        """
        try:
            result = run_lab_mapper({
                "subject_id": subject_id,
                "hadm_id":    hadm_id,
            })
            results["lab_mapper"] = result

        except Exception as e:
            errors["lab_mapper"] = str(e)
            results["lab_mapper"] = None

    def run_parallel(
        self, subject_id: int, hadm_id: int
    ) -> tuple[dict, dict]:
        """Fire both agents simultaneously, block until both finish."""
        results: dict = {}
        errors:  dict = {}

        t1 = threading.Thread(
            target=self._run_note_parser,
            args=(subject_id, hadm_id, results, errors)
        )
        t2 = threading.Thread(
            target=self._run_lab_mapper,
            args=(subject_id, hadm_id, results, errors)
        )

        t1.start(); t2.start()
        t1.join();  t2.join()

        return results, errors

    # ── STEP 3: build RAG inputs from both outputs ─────────────────────────────

    def _build_rag_inputs(
        self,
        note_output: dict | None,
        lab_output:  dict | None,
    ) -> tuple[list[dict], list[dict]]:
        """
        RAG agent signature:
            run_rag_agent(parsed_symptoms: list, critical_values: list) -> dict

        parsed_symptoms  ← note_parser's flattened findings
        critical_values  ← lab_mapper's critical_values list
        """
        parsed_symptoms = (
            note_output.get("parsed_symptoms", [])
            if note_output else []
        )

        # lab_mapper already produces critical_values in the exact shape RAG expects:
        # [{"test": str, "value": float, "direction": "high"|"low", ...}, ...]
        critical_values = (
            lab_output.get("critical_values", [])
            if lab_output else []
        )

        # Also promote abnormal values that aren't already in critical_values
        # so RAG has richer context (e.g. mild AKI signals)
        seen_tests = {cv["test"] for cv in critical_values}
        for av in (lab_output.get("abnormal_values", []) if lab_output else []):
            if av["test"] not in seen_tests:
                critical_values.append({
                    "test":      av["test"],
                    "value":     av["value"],
                    "direction": av["type"],          # "high" or "low"
                    "timestamp": av["timestamp"],
                    "is_outlier": av.get("is_outlier", False),
                })
                seen_tests.add(av["test"])

        return parsed_symptoms, critical_values

    def extract_flagged_risks(
        self,
        note_output: dict | None,
        lab_output:  dict | None,
    ) -> list[dict]:
        """
        Merged human-readable risk signals for the Chief Agent.
        (Separate from the RAG inputs above — this goes into the unified JSON)
        """
        flagged = []

        if note_output:
            for symptom in note_output.get("flagged_risks", []):
                flagged.append({
                    "source":  "note_parser",
                    "type":    "symptom",
                    "signal":  symptom,
                })

        if lab_output:
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

            for entry in lab_output.get("outlier_flags", []):
                flagged.append({
                    "source":    "lab_mapper",
                    "type":      "outlier_flag",
                    "signal":    entry["test"],
                    "value":     entry["value"],
                    "z_score":   entry["z_score"],
                    "timestamp": entry["timestamp"],
                })

            # AKI signals from timeline
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

        # Deduplicate by (source, signal)
        seen, unique = set(), []
        for f in flagged:
            key = (f["source"], f["signal"])
            if key not in seen:
                seen.add(key); unique.append(f)

        return unique

    # ── STEP 4: RAG retrieval ──────────────────────────────────────────────────

    def run_rag(
        self,
        parsed_symptoms: list[dict],
        critical_values: list[dict],
    ) -> dict:
        """
        Calls run_rag_agent with the exact signature it expects.
        Graceful fallback if both lists are empty.
        """
        if not parsed_symptoms and not critical_values:
            return {
                "agent":               "guideline_rag",
                "query_used":          "",
                "citations":           [],
                "guidelines_retrieved": 0,
                "top_relevance_score": 0,
                "note":                "No findings to query — RAG skipped",
            }

        return run_rag_agent(parsed_symptoms, critical_values)

    # ── STEP 5: assemble unified JSON ─────────────────────────────────────────

    def assemble_unified_output(
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
                "orchestrator":     "OrchestratorAgent v1.1",
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

            # ── Three agent outputs ──────────────────────────────────────────
            "note_parser_output":  note_output or {
                "agent": "note_parser", "status": "failed"
            },
            "lab_mapper_output":   lab_output  or {
                "agent": "lab_mapper",  "status": "failed"
            },
            "rag_guidelines_output": rag_output,

            # ── Merged signals for Chief Agent ───────────────────────────────
            "flagged_risks": flagged_risks,

            # ── Outlier gate — Chief Agent reads this first ──────────────────
            "outlier_flags": (
                lab_output.get("outlier_flags", []) if lab_output else []
            ),

            # ── Data completeness ────────────────────────────────────────────
            "data_completeness": {
                "note_parser_available": note_output  is not None,
                "lab_mapper_available":  lab_output   is not None,
                "rag_available": bool(
                    rag_output.get("citations") or
                    rag_output.get("retrieved_guidelines")
                ),
                "sofa_coverage_pct":   (
                    lab_output.get("sofa_coverage_pct", 0.0) if lab_output else 0.0
                ),
                "labs_available":      (
                    lab_output.get("labs_available", []) if lab_output else []
                ),
                "total_flagged_risks": len(flagged_risks),
                "outlier_flags_active": len(
                    lab_output.get("outlier_flags", []) if lab_output else []
                ),
                "guidelines_retrieved": rag_output.get("guidelines_retrieved", 0),
            },

            # ── Safety ───────────────────────────────────────────────────────
            # "safety": {
            #     "disclaimer": (
            #         "All outputs are AI-generated clinical decision support only. "
            #         "They do not constitute a diagnosis and must be reviewed by "
            #         "a qualified clinician before influencing patient care."
            #     ),
            #     "outlier_hold_active": bool(
            #         lab_output and lab_output.get("outlier_flags")
            #     ),
            # },
        }

    # ── Save ───────────────────────────────────────────────────────────────────

    def save(self, unified: dict) -> Path:
        sid  = unified["pipeline_run"]["subject_id"]
        hid  = unified["pipeline_run"]["hadm_id"]
        ts   = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        out_dir = (
            OUTPUT_BASE / "orchestrator"
            / f"sub_{sid}" / f"hadm_{hid}"
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"unified_{ts}.json"
        with open(out_file, "w") as f:
            json.dump(unified, f, indent=2, default=str)
        print(f"[Orchestrator] Saved → {out_file}")
        return out_file

    # ── Main entry point ───────────────────────────────────────────────────────

    def run(self, subject_id: int, hadm_id: int) -> dict:
        start_time = datetime.datetime.utcnow()
        print(f"[Orchestrator] subject={subject_id}  hadm={hadm_id}")

        # 1 + 2: parallel agents
        print("[Orchestrator] Step 1/2 — NoteParser + LabMapper in parallel...")
        results, errors = self.run_parallel(subject_id, hadm_id)

        note_output = results.get("note_parser")
        lab_output  = results.get("lab_mapper")
        print(
            f"[Orchestrator] ✓ NoteParser={'OK' if note_output else 'FAILED'} | "
            f"LabMapper={'OK' if lab_output else 'FAILED'}"
        )
        if errors:
            print(f"[Orchestrator] ⚠ Errors: {errors}")

        # 3: build RAG inputs
        parsed_symptoms, critical_values = self._build_rag_inputs(
            note_output, lab_output
        )
        print(
            f"[Orchestrator] Step 3 — RAG inputs: "
            f"{len(parsed_symptoms)} symptoms, {len(critical_values)} lab values"
        )

        # 4: extract merged flagged risks (for Chief Agent JSON)
        flagged_risks = self.extract_flagged_risks(note_output, lab_output)
        print(f"[Orchestrator] {len(flagged_risks)} unique flagged risks.")

        # 5: RAG
        print("[Orchestrator] Step 4 — Querying RAG against guidelines.pdf...")
        rag_output = self.run_rag(parsed_symptoms, critical_values)
        print(
            f"[Orchestrator] RAG → "
            f"{rag_output.get('guidelines_retrieved', 0)} citations | "
            f"top score={rag_output.get('top_relevance_score', 0)}"
        )

        # 6: assemble
        print("[Orchestrator] Step 5 — Assembling unified JSON...")
        unified = self.assemble_unified_output(
            subject_id, hadm_id,
            note_output, lab_output, rag_output,
            flagged_risks, errors, start_time,
        )

        self.save(unified)
        print(
            f"[Orchestrator] Done in "
            f"{unified['pipeline_run']['duration_ms']}ms"
        )
        return unified


# ── Convenience runner ─────────────────────────────────────────────────────────

def run_pipeline(subject_id: int, hadm_id: int, groq_api_key: str) -> dict:
    return OrchestratorAgent(groq_api_key).run(subject_id, hadm_id)


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()

    result = run_pipeline(
        subject_id=42321,
        hadm_id=114648,
        groq_api_key=os.getenv("GROQ_API_KEY"),
    )
    print(json.dumps(result["data_completeness"], indent=2))