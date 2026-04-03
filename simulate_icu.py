# simulate_icu.py
from __future__ import annotations

import csv
import random
import time
from datetime import datetime, timezone
from pathlib import Path

LAB_FILE   = Path("backend/data/LABEVENTS.csv")
SUBJECT_ID = 10002
HADM_ID    = 198765
INTERVAL   = 30   # seconds between new readings

# Simulate realistic ICU lab trends — values drift over time
# Format: itemid, lab_name, base_value, drift_per_step, unit
LAB_PROFILES = [
    {"itemid": 50912, "name": "Creatinine", "value": 1.4, "drift": 0.15,  "unit": "mg/dL"},
    {"itemid": 50813, "name": "Lactate",    "value": 2.2, "drift": 0.2,   "unit": "mmol/L"},
    {"itemid": 51300, "name": "WBC",        "value": 13.0,"drift": 0.8,   "unit": "K/uL"},
]

# Track current values across iterations
state = {p["itemid"]: p["value"] for p in LAB_PROFILES}


def _next_row_id(file: Path) -> int:
    """Get the next available row_id from the CSV."""
    with open(file, "r") as f:
        return sum(1 for _ in f)   # rowcount = next id


def _new_value(itemid: int, profile: dict) -> float:
    """Drift the value slightly — simulates gradual clinical change."""
    current = state[itemid]
    # 70% chance value worsens (drifts up), 30% chance it improves
    direction = 1 if random.random() < 0.7 else -1
    noise     = random.uniform(0, profile["drift"])
    new_val   = round(current + direction * noise, 2)
    # Keep values in a realistic ICU range
    new_val   = max(0.1, new_val)
    state[itemid] = new_val
    return new_val


def _append_lab_row(profile: dict, value: float, timestamp: str) -> None:
    """Append one new lab row to LABEVENTS.csv."""
    row_id = _next_row_id(LAB_FILE)
    row = {
        "row_id":     row_id,
        "subject_id": SUBJECT_ID,
        "hadm_id":    HADM_ID,
        "itemid":     profile["itemid"],
        "charttime":  timestamp,
        "value":      value,
        "valuenum":   value,
        "valueuom":   profile["unit"],
        "flag":       "abnormal" if value > profile["value"] * 1.2 else "",
    }

    with open(LAB_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        writer.writerow(row)

    print(f"  [+] {profile['name']}: {value} {profile['unit']}  @ {timestamp}")


def run_simulation(rounds: int = 10) -> None:
    print(f"ICU Simulator — patient {SUBJECT_ID}/{HADM_ID}")
    print(f"Adding labs every {INTERVAL}s for {rounds} rounds\n")

    for i in range(1, rounds + 1):
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        print(f"Round {i}/{rounds} — {ts}")

        for profile in LAB_PROFILES:
            value = _new_value(profile["itemid"], profile)
            _append_lab_row(profile, value, ts)

        print(f"  → Re-run POST /analyze to see updated risk report\n")
        if i < rounds:
            time.sleep(INTERVAL)

    print("Simulation complete.")


if __name__ == "__main__":
    run_simulation(rounds=10)