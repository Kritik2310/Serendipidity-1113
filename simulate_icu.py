# simulate_icu.py
from __future__ import annotations

import csv
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

LAB_FILE      = Path("backend/data/LABEVENTS.csv")
HISTORY_FILE  = Path("backend/data/PATIENT_HISTORY.csv")
PROG_FILE     = Path("backend/outputs/disease_progression.json")
SUBJECT_ID    = 10002
HADM_ID       = 198765
INTERVAL      = 30
API_URL       = "http://localhost:8000/analyze"

LAB_PROFILES = [
    {"itemid": 50912, "name": "Creatinine", "value": 1.4,  "drift": 0.15, "unit": "mg/dL",   "direction_bias": 0.70, "min": 0.4,  "max": 6.0},
    {"itemid": 50813, "name": "Lactate",    "value": 2.2,  "drift": 0.20, "unit": "mmol/L",  "direction_bias": 0.65, "min": 0.5,  "max": 8.0},
    {"itemid": 51300, "name": "WBC",        "value": 13.0, "drift": 0.80, "unit": "K/uL",    "direction_bias": 0.65, "min": 1.0,  "max": 35.0},
    {"itemid": 50885, "name": "Bilirubin",  "value": 1.8,  "drift": 0.10, "unit": "mg/dL",   "direction_bias": 0.60, "min": 0.1,  "max": 12.0},
    {"itemid": 51265, "name": "Platelets",  "value": 95.0, "drift": 5.0,  "unit": "K/uL",    "direction_bias": 0.35, "min": 20.0, "max": 400.0},
    {"itemid": 51222, "name": "Hemoglobin", "value": 8.2,  "drift": 0.20, "unit": "g/dL",    "direction_bias": 0.40, "min": 4.0,  "max": 18.0},
]

NORMAL_RANGES = {
    "Creatinine":  (0.6,  1.2),
    "Lactate":     (0.5,  2.0),
    "WBC":         (4.5,  11.0),
    "Bilirubin":   (0.1,  1.2),
    "Platelets":   (150.0, 400.0),
    "Hemoglobin":  (12.0, 17.5),
}

LAB_WEIGHTS = {
    "Lactate":    0.30,
    "Creatinine": 0.25,
    "WBC":        0.20,
    "Platelets":  0.12,
    "Bilirubin":  0.08,
    "Hemoglobin": 0.05,
}

# Live state — drifts each round
state = {p["itemid"]: p["value"] for p in LAB_PROFILES}
# Map itemid → profile for quick lookup
_profile_map = {p["itemid"]: p for p in LAB_PROFILES}


def _log(message: str) -> None:
    """Keep simulator logs safe for Windows consoles without altering data files."""
    safe = message.encode("cp1252", errors="replace").decode("cp1252")
    print(safe)


# ── Value evolution ────────────────────────────────────────────────────────────

def _next_value(profile: dict) -> float:
    itemid  = profile["itemid"]
    current = state[itemid]
    bias    = profile["direction_bias"]

    # 5% spike chance — demonstrates real-time outlier detection
    if random.random() < 0.05:
        spike = min(current * random.uniform(2.5, 4.0), profile["max"])
        print(f"    ⚡ SPIKE: {profile['name']} → {round(spike, 2)} (Chief Agent should flag)")
        return round(spike, 2)   # spike does NOT update state baseline

    direction = 1 if random.random() < bias else -1
    noise     = random.uniform(0, profile["drift"])
    new_val   = round(current + direction * noise, 2)
    new_val   = max(profile["min"], min(profile["max"], new_val))
    state[itemid] = new_val
    return new_val


# ── Disease severity score ─────────────────────────────────────────────────────

def _compute_score() -> float:
    score = 0.0
    for profile in LAB_PROFILES:
        name        = profile["name"]
        value       = state[profile["itemid"]]
        weight      = LAB_WEIGHTS.get(name, 0.0)
        low, high   = NORMAL_RANGES[name]

        if name in ("Platelets", "Hemoglobin"):
            deviation = max(0.0, (low - value) / low) if value < low else 0.0
        else:
            deviation = max(0.0, (value - high) / high) if value > high else 0.0

        score += min(deviation, 1.0) * weight * 100

    return round(min(score, 100.0), 1)


def _classify_stage(score: float) -> str:
    if score >= 70:
        return "Sepsis With Septic Shock And Acute Kidney Injury"
    if score >= 50:
        return "Moderate Sepsis — Organ Dysfunction Developing"
    if score >= 30:
        return "Early Sepsis — Monitoring Required"
    return "Stable — Low Risk"


def _classify_trend(timeline: list[dict]) -> str:
    if len(timeline) < 2:
        return "stable"
    delta = timeline[-1]["score"] - timeline[-2]["score"]
    if delta > 2:
        return "worsening"
    if delta < -2:
        return "improving"
    return "stable"


def _build_summary() -> str:
    creat = round(state[50912], 2)
    lact  = round(state[50813], 2)
    wbc   = round(state[51300], 2)
    plt   = round(state[51265], 2)
    return (
        f"Patient presents with progressive sepsis markers including leukocytosis "
        f"(WBC {wbc} K/uL), lactic acidosis ({lact} mmol/L), and acute kidney injury "
        f"(Creat {creat} mg/dL). Thrombocytopenia ({plt} K/uL) suggests multi-organ "
        f"dysfunction consistent with Sepsis-3 criteria."
    )


def _status(name: str, value: float) -> str:
    low, high = NORMAL_RANGES[name]
    if name in ("Platelets", "Hemoglobin"):
        if value < low * 0.5: return "critical"
        if value < low:       return "watch"
        return "normal"
    if value > high * 2: return "critical"
    if value > high:     return "watch"
    return "normal"


# ── Historical baseline from PATIENT_HISTORY.csv ──────────────────────────────

def _load_historical() -> list[dict]:
    if not HISTORY_FILE.exists():
        print("  No PATIENT_HISTORY.csv found — skipping historical baseline")
        return []

    try:
        import pandas as pd
        hist    = pd.read_csv(HISTORY_FILE)
        patient = hist[hist["subject_id"] == SUBJECT_ID]
        prior   = patient[patient["hadm_id"] != HADM_ID]

        if prior.empty:
            return []

        entries = []
        for hadm_id, group in prior.groupby("hadm_id"):
            score = 0.0
            for _, row in group.iterrows():
                name   = row["lab_name"]
                value  = float(row["mean_value"])
                weight = LAB_WEIGHTS.get(name, 0.0)
                low, high = NORMAL_RANGES.get(name, (0, 1))
                if name in ("Platelets", "Hemoglobin"):
                    dev = max(0.0, (low - value) / low) if value < low else 0.0
                else:
                    dev = max(0.0, (value - high) / high) if value > high else 0.0
                score += min(dev, 1.0) * weight * 100

            entries.append({
                "time":    f"Adm {int(hadm_id)}",
                "score":   round(min(score, 100.0), 1),
                "source":  "Historical",
                "summary": f"Prior admission {int(hadm_id)} — derived from lab averages",
            })

        entries.sort(key=lambda x: x["time"])
        return entries[-3:]

    except Exception as e:
        print(f"  History load error: {e}")
        return []


# ── CSV append ─────────────────────────────────────────────────────────────────

def _next_row_id() -> int:
    with open(LAB_FILE, "r") as f:
        return sum(1 for _ in f)


def _append_lab_row(profile: dict, value: float, timestamp: str) -> None:
    row = {
        "row_id":     _next_row_id(),
        "subject_id": SUBJECT_ID,
        "hadm_id":    HADM_ID,
        "itemid":     profile["itemid"],
        "charttime":  timestamp,
        "value":      value,
        "valuenum":   value,
        "valueuom":   profile["unit"],
        "flag":       "abnormal" if value > NORMAL_RANGES[profile["name"]][1] else "",
    }
    with open(LAB_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        writer.writerow(row)

    flag = "⚠" if row["flag"] == "abnormal" else "✓"
    print(f"    {flag} {profile['name']}: {value} {profile['unit']}")


# ── Write progression JSON for frontend ───────────────────────────────────────

def _load_session_historic_insights() -> list[dict]:
    """
    Group log entries by session_id.
    All sessions except the current one become historic insight entries.
    """
    log_file = PROG_FILE.parent / "simulation_session_log.json"
    if not log_file.exists():
        return []

    try:
        log = json.loads(log_file.read_text())
    except Exception:
        return []

    if not log:
        return []

    # Group by session_id
    from collections import defaultdict
    sessions: dict[str, list[dict]] = defaultdict(list)
    for entry in log:
        sid = entry.get("session_id", "unknown")
        sessions[sid].append(entry)

    # Exclude the current running session
    past_session_ids = [
        sid for sid in sessions
        if sid != _current_session_id
    ]

    # Sort by session_id (which is a timestamp string — sorts chronologically)
    past_session_ids.sort()

    insights = []
    for i, sid in enumerate(past_session_ids):
        session = sessions[sid]
        scores  = [e["score"] for e in session if "score" in e]
        times   = [e.get("time", "") for e in session if e.get("time")]

        if not scores:
            continue

        avg_score = round(sum(scores) / len(scores), 1)
        max_score = round(max(scores), 1)
        min_score = round(min(scores), 1)
        start_ts  = times[0]  if times else "—"
        end_ts    = times[-1] if times else "—"

        trend = "stable"
        if len(scores) >= 2:
            if scores[-1] > scores[0] + 2:
                trend = "worsening"
            elif scores[-1] < scores[0] - 2:
                trend = "improving"

        # Format session label as readable date range
        try:
            session_date = datetime.strptime(sid, "%Y%m%dT%H%M%S").strftime("%d %b, %H:%M")
        except Exception:
            session_date = sid

        insights.append({
            "id":     f"session_{i}",
            "window": f"Session {i + 1} — {session_date}",
            "signal": f"Avg score {avg_score} · Peak {max_score} · Low {min_score}",
            "impact": f"{len(scores)} readings · Trend: {trend} ({start_ts} → {end_ts})",
        })

    return insights


def _write_progression(historical: list[dict], current_timeline: list[dict]) -> None:
    PROG_FILE.parent.mkdir(parents=True, exist_ok=True)

    trend   = _classify_trend(current_timeline)
    score   = current_timeline[-1]["score"] if current_timeline else 0
    summary = _build_summary()
    ts      = datetime.now(timezone.utc).isoformat()

    realtime_insights = [
        {
            "id":        "rt_creat",
            "metric":    "Creatinine",
            "value":     f"{round(state[50912], 2)} mg/dL",
            "status":    _status("Creatinine", state[50912]),
            "updatedAt": datetime.now(timezone.utc).strftime("%d/%m/%Y, %H:%M:%S"),
        },
        {
            "id":        "rt_lactate",
            "metric":    "Lactate",
            "value":     f"{round(state[50813], 2)} mmol/L",
            "status":    _status("Lactate", state[50813]),
            "updatedAt": datetime.now(timezone.utc).strftime("%d/%m/%Y, %H:%M:%S"),
        },
        {
            "id":        "rt_wbc",
            "metric":    "WBC",
            "value":     f"{round(state[51300], 2)} K/uL",
            "status":    _status("WBC", state[51300]),
            "updatedAt": datetime.now(timezone.utc).strftime("%d/%m/%Y, %H:%M:%S"),
        },
        {
            "id":        "rt_plt",
            "metric":    "Platelets",
            "value":     f"{round(state[51265], 2)} K/uL",
            "status":    _status("Platelets", state[51265]),
            "updatedAt": datetime.now(timezone.utc).strftime("%d/%m/%Y, %H:%M:%S"),
        },
    ]

    # Build historic insights in priority order:
    # 1. Previous simulation sessions (most clinically relevant for progression)
    # 2. MIMIC prior admissions (baseline context)
    session_insights = _load_session_historic_insights()

    mimic_insights = [
        {
            "id":     f"hist_{i}",
            "window": e["time"],
            "signal": f"Disease score {e['score']}",
            "impact": e.get("summary", "Prior admission data"),
        }
        for i, e in enumerate(historical)
    ]

    # Session insights first — they are more recent and clinically relevant
    combined_historic = session_insights + mimic_insights

    payload = {
        "subject_id":       SUBJECT_ID,
        "hadm_id":          HADM_ID,
        "updated_at":       ts,
        "stage":            _classify_stage(score),
        "trendDirection":   trend,
        "summary":          summary,
        "timeline":         (historical + current_timeline)[-20:],
        "historicInsights": combined_historic,
        "realTimeInsights": realtime_insights,
    }

    PROG_FILE.write_text(json.dumps(payload, indent=2))
    print(f"    ✓ Progression updated — score={score} trend={trend} "
          f"historic_sessions={len(session_insights)}")

def _trigger_analysis() -> None:
    try:
        print("    Triggering /analyze ...")
        resp = requests.post(
            API_URL,
            json={"subject_id": SUBJECT_ID, "hadm_id": HADM_ID},
            timeout=120,
        )
        if resp.status_code == 200:
            data     = resp.json()
            concern  = data.get("primary_concern", "N/A")
            outliers = len(data.get("excluded_outliers", []))
            print(f"    ✓ Pipeline done: {concern} | outliers excluded: {outliers}")
        else:
            print(f"    API error {resp.status_code}: {resp.text[:100]}")
    except requests.exceptions.Timeout:
        print("    Timeout — pipeline still running in background")
    except requests.exceptions.ConnectionError:
        print("    Cannot reach API — is uvicorn running on port 8000?")
# ── Main loop ──────────────────────────────────────────────────────────────────

def run_simulation(rounds: int = 20, auto_analyze: bool = True) -> None:
    print(f"\nICU Simulator — patient {SUBJECT_ID}/{HADM_ID}")
    print(f"Rounds: {rounds} · Interval: {INTERVAL}s · Auto-analyze: {auto_analyze}\n")

    # Load historical baseline once at start
    print("Loading historical baseline...")
    historical = _load_historical()
    print(f"Found {len(historical)} prior admissions\n")

    current_timeline: list[dict] = _load_existing_timeline()
    print(f"Resuming with {len(current_timeline)} existing real-time points\n")

    for i in range(1, rounds + 1):
        ts       = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        ts_label = datetime.now(timezone.utc).strftime("%d %b, %H:%M")
        print(f"Round {i}/{rounds} — {ts}")

        # Write all 6 SOFA lab rows
        for profile in LAB_PROFILES:
            value = _next_value(profile)
            _append_lab_row(profile, value, ts)

        # Compute score and build timeline entry
        score = _compute_score()
        entry = {
            "time":    ts_label,
            "score":   score,
            "source":  "Real-time",
            "summary": f"Round {i} — score {score}",
        }
        current_timeline.append(entry)
        _save_session_log(entry)
        # Write progression JSON immediately — frontend polls this
        _write_progression(historical, current_timeline)

        # Trigger full pipeline re-analysis
        if auto_analyze:
            _trigger_analysis()

        print()
        if i < rounds:
            time.sleep(INTERVAL)

    print("Simulation complete.")
    print(f"Final progression: {PROG_FILE}")

def _load_existing_timeline() -> list[dict]:
    """
    Load real-time timeline points saved from previous sessions.
    Returns empty list if no file exists yet.
    """
    if not PROG_FILE.exists():
        return []
    try:
        data     = json.loads(PROG_FILE.read_text())
        timeline = data.get("timeline", [])
        # Keep only Real-time points — historical points are re-loaded separately
        realtime = [t for t in timeline if t.get("source") == "Real-time"]
        print(f"  Loaded {len(realtime)} previous real-time points from disk")
        return realtime
    except Exception as e:
        print(f"  Could not load previous timeline: {e}")
        return []


_current_session_id: str | None = None

def _save_session_log(entry: dict) -> None:
    """Append round to permanent session log. Marks session boundaries explicitly."""
    global _current_session_id

    log_file = PROG_FILE.parent / "simulation_session_log.json"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Generate a session ID once per process run
    if _current_session_id is None:
        _current_session_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")

    log = []
    if log_file.exists():
        try:
            log = json.loads(log_file.read_text())
        except Exception:
            log = []

    log.append({
        **entry,
        "logged_at":  datetime.now(timezone.utc).isoformat(),
        "session_id": _current_session_id,
    })

    log_file.write_text(json.dumps(log, indent=2))


if __name__ == "__main__":
    run_simulation()
