# lab_ranges.py
# Defines monitored lab tests and their clinical thresholds.
# ICU_CRITICAL_LABS keys are MIMIC-III itemids.

ICU_CRITICAL_LABS = {
    # ── Core sepsis / organ dysfunction markers ────────────────────────────
    51300: {"name": "WBC",        "normal": [4.5,  11.0],  "unit": "K/uL"},
    50813: {"name": "Lactate",    "normal": [0.5,   2.0],  "unit": "mmol/L"},
    50912: {"name": "Creatinine", "normal": [0.6,   1.2],  "unit": "mg/dL"},

    # ── SOFA score completeness — these 3 were missing ────────────────────
    50885: {"name": "Bilirubin",  "normal": [0.1,   1.2],  "unit": "mg/dL"},
    51265: {"name": "Platelets",  "normal": [150.0, 400.0], "unit": "K/uL"},
    51222: {"name": "Hemoglobin", "normal": [12.0,  17.5],  "unit": "g/dL"},
}

PANIC_THRESHOLDS = {
    # critical_high must always be > high — fixed the Creatinine inversion
    "WBC": {
        "low":           2.0,
        "high":         15.0,
        "critical_high": 30.0,   # blast crisis / severe infection
    },
    "Lactate": {
        "low":           None,
        "high":          2.0,    # sepsis threshold
        "critical_high": 4.0,    # severe sepsis / shock
    },
    "Creatinine": {
        "low":           None,
        "high":          1.5,    # AKI Stage 1 signal  ← was wrong (was 3.0)
        "critical_high": 3.0,    # AKI Stage 3 signal  ← was wrong (was 2.5)
    },
    "Bilirubin": {
        "low":           None,
        "high":          2.0,    # SOFA liver score = 1
        "critical_high": 6.0,    # SOFA liver score >= 3
    },
    "Platelets": {
        "low":           100.0,  # SOFA coag score = 1
        "high":          None,
        "critical_high": None,
        "critical_low":  50.0,   # SOFA coag score >= 3
    },
    "Hemoglobin": {
        "low":           7.0,    # transfusion threshold
        "high":          None,
        "critical_high": None,
        "critical_low":  6.0,    # critical anaemia
    },
}

# SOFA score labs — used by lab_mapper to compute coverage percentage
SOFA_LABS = {"Creatinine", "WBC", "Platelets", "Bilirubin", "Lactate", "Hemoglobin"}