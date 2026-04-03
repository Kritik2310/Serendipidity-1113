#lab_ranges.py
ICU_CRITICAL_LABS = {
    51300: {"name": "WBC", "normal": [4.5, 11.0]},
    50813: {"name": "Lactate", "normal": [0.5, 2.0]},
    50912: {"name": "Creatinine", "normal": [0.6, 1.2]},
}

PANIC_THRESHOLDS = {
    "WBC": {"low": 2.0, "high": 15.0, "critical_high":30.0}, #earlier alert
    "Lactate": {"low": None, "high": 2.0, "critical_high":4.0}, #severe sepsis
    "Creatinine": {"low": None, "high": 3.0, "critical_high":2.5}, #early AKI
}
