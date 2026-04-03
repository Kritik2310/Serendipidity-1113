# outlier_rules.py
# Delta check rules from Section 15.2 of icu_clinical_guidelines.pdf
# Used by Chief Agent for real-time spike detection

from datetime import datetime, timedelta

# Z-score threshold — aligns with guidelines Section 15.2
Z_THRESHOLD = 3.0

# Physiologically implausible hard limits — Section 15.1
IMPLAUSIBLE_LIMITS = {
    "Creatinine":  (0.0,  25.0),
    "Lactate":     (0.0,  30.0),
    "Hemoglobin":  (2.0,  22.0),
    "WBC":         (0.1, 500.0),
    "Platelets":   (1.0, 2000.0),
    "Bilirubin":   (0.0,  60.0),
}

# Delta check rules — max allowable change within time window
# Format: {lab: {"max_delta": float, "direction": "rise"|"drop"|"any",
#                "window_hours": float, "unit": str}}
DELTA_RULES = {
    "Creatinine": {
        "max_delta":    2.0,
        "direction":    "rise",
        "window_hours": 6.0,
        "unit":         "mg/dL",
        "guideline":    "Section 15.2 — rise > 2.0 mg/dL in < 6h",
    },
    "Lactate": {
        "max_delta":    4.0,
        "direction":    "rise",
        "window_hours": 2.0,
        "unit":         "mmol/L",
        "guideline":    "Section 15.2 — rise > 4 mmol/L in < 2h",
    },
    "WBC": {
        "max_delta":    20.0,
        "direction":    "any",
        "window_hours": 6.0,
        "unit":         "K/uL",
        "guideline":    "Section 15.2 — change > 20 K/uL in < 6h",
    },
    "Hemoglobin": {
        "max_delta":    4.0,
        "direction":    "drop",
        "window_hours": 6.0,
        "unit":         "g/dL",
        "guideline":    "Section 15.2 — drop > 4 g/dL in < 6h (no surgery)",
    },
    "Platelets": {
        "max_delta":    100.0,
        "direction":    "drop",
        "window_hours": 12.0,
        "unit":         "K/uL",
        "guideline":    "Section 15.2 — drop > 100 K/uL in < 12h",
    },
    "Bilirubin": {
        "max_delta":    5.0,
        "direction":    "rise",
        "window_hours": 12.0,
        "unit":         "mg/dL",
        "guideline":    "Section 15.2 — rise > 5 mg/dL in < 12h",
    },
}


def check_delta(
    test: str,
    current_value: float,
    current_ts: str,
    timeline: list[dict],
) -> dict | None:
    """
    Check if current value changed too fast vs recent readings.
    Returns outlier dict if flagged, None if clean.

    timeline: list of {"timestamp": str, "value": float} dicts
              from lab_mapper timeline_by_test[test]
    """
    rule = DELTA_RULES.get(test)
    if not rule:
        return None

    try:
        ts_current = datetime.fromisoformat(current_ts)
    except (ValueError, TypeError):
        return None

    window = timedelta(hours=rule["window_hours"])

    # Find the most recent prior reading within the time window
    prior_value = None
    prior_ts    = None

    for entry in reversed(timeline):
        try:
            ts_entry = datetime.fromisoformat(entry["timestamp"])
        except (ValueError, TypeError):
            continue

        if ts_entry >= ts_current:
            continue   # skip current and future entries

        if (ts_current - ts_entry) <= window:
            prior_value = entry["value"]
            prior_ts    = entry["timestamp"]
            break

    if prior_value is None:
        return None   # no prior reading in window — cannot check

    delta = current_value - prior_value

    # Evaluate based on direction rule
    direction   = rule["direction"]
    max_delta   = rule["max_delta"]
    violated    = False

    if direction == "rise"  and delta > max_delta:
        violated = True
    elif direction == "drop" and delta < -max_delta:
        violated = True
    elif direction == "any"  and abs(delta) > max_delta:
        violated = True

    if not violated:
        return None

    return {
        "check":       "delta",
        "test":        test,
        "current_value": current_value,
        "prior_value": prior_value,
        "prior_ts":    prior_ts,
        "delta":       round(delta, 3),
        "window_hours": rule["window_hours"],
        "max_allowed": max_delta,
        "guideline":   rule["guideline"],
        "reason": (
            f"Rapid change detected — {test} changed by {round(delta,3)} "
            f"{rule['unit']} within {rule['window_hours']}h "
            f"(max allowed: {max_delta}). "
            f"Probable measurement error or specimen issue. {rule['guideline']}."
        ),
    }