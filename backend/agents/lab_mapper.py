# lab_mapper.py
from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from backend.utils.lab_ranges import ICU_CRITICAL_LABS, PANIC_THRESHOLDS, SOFA_LABS

logger = logging.getLogger(__name__)

LAB_FILE = "backend/data/LABEVENTS.csv"
ICU_FILE = "backend/data/ICUSTAYS.csv"


class LabMapperAgent:
    """
    Processes lab events for one patient:
    """

    def __init__(self):
        self.lab_df     = pd.read_csv(LAB_FILE)
        self.icu_df     = pd.read_csv(ICU_FILE)
        self.lab_lookup = {v["name"]: v for v in ICU_CRITICAL_LABS.values()}

    #Patient filtering

    def _filter_patient(self, subject_id: int, hadm_id: int) -> pd.DataFrame:
        """Keep only rows for this patient — done before any processing."""
        return self.lab_df[
            (self.lab_df["subject_id"] == subject_id) &
            (self.lab_df["hadm_id"]    == hadm_id)
        ].copy()

    def _apply_icu_window(
        self, df: pd.DataFrame, subject_id: int, hadm_id: int
    ) -> tuple[pd.DataFrame, pd.Timestamp | None, pd.Timestamp | None]:
        """Clip lab records to the ICU stay window (intime → outtime)."""
        icu = self.icu_df[
            (self.icu_df["subject_id"] == subject_id) &
            (self.icu_df["hadm_id"]    == hadm_id)
        ]
        if icu.empty:
            return df, None, None

        intime  = pd.to_datetime(icu.iloc[0]["intime"])
        outtime = pd.to_datetime(icu.iloc[0]["outtime"])
        df["charttime"] = pd.to_datetime(df["charttime"], errors="coerce")
        df = df[(df["charttime"] >= intime) & (df["charttime"] <= outtime)]
        return df, intime, outtime

    # Data preparation 

    def _filter_labs(self, df: pd.DataFrame) -> pd.DataFrame:
        """Keep only itemids defined in ICU_CRITICAL_LABS."""
        return df[df["itemid"].isin(ICU_CRITICAL_LABS.keys())]

    def _clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Drop rows with missing value or timestamp."""
        df = df[df["valuenum"].notna() & df["charttime"].notna()].copy()
        df["charttime"] = pd.to_datetime(df["charttime"])
        return df

    def _map_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Attach human-readable lab name and unit from ICU_CRITICAL_LABS."""
        df["lab_name"] = df["itemid"].map(lambda x: ICU_CRITICAL_LABS[x]["name"])
        df["unit"]     = df["itemid"].map(lambda x: ICU_CRITICAL_LABS[x].get("unit", ""))
        return df

    def _deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Bucket into 30-min windows — keep last reading per window per lab."""
        df = df.sort_values("charttime")
        df["time_bucket"] = df["charttime"].dt.floor("30min")
        return df.groupby(["lab_name", "time_bucket"], as_index=False).last()

    # Analytics 

    def _trend(self, current: float, previous: float | None) -> tuple[str, float]:
        """Return (trend_label, delta). Stable if change < 5%."""
        if previous is None:
            return "stable", 0.0
        delta = current - previous
        pct   = abs(delta) / previous * 100 if previous != 0 else 0
        if pct < 5:
            return "stable", delta
        return ("rising" if delta > 0 else "falling"), delta

    def _rolling_stats(
        self, values: list[float], window: int = 3
    ) -> tuple[float | None, float | None]:
        if len(values) < 2:
            return None, None
        arr = np.array(values[-window:])
        return float(arr.mean()), float(arr.std(ddof=0))

    def _detect_outlier(
        self, value: float, history: list[float], z_threshold: float = 3.0
    ) -> dict:
        """
        Z-score outlier detection against rolling history.
        """
        if len(history) < 2:
            return {
                "is_outlier": False, "z_score": None,
                "rolling_mean": None, "rolling_std": None, "redraw_required": False,
            }

        mean, std = self._rolling_stats(history)
        if not std:
            return {
                "is_outlier": False, "z_score": None,
                "rolling_mean": mean, "rolling_std": std, "redraw_required": False,
            }

        z          = (value - mean) / std
        is_outlier = abs(z) > z_threshold
        return {
            "is_outlier":      is_outlier,
            "z_score":         round(float(z), 3),
            "rolling_mean":    round(mean, 3),
            "rolling_std":     round(std, 3),
            "redraw_required": is_outlier,
        }

    def _check_flags(
        self, lab: str, value: float
    ) -> tuple[bool, bool, bool, str | None]:
        """
        Check normal range and panic thresholds.
        Returns (above_normal, below_normal, is_critical, direction).
        Handles both critical_high and critical_low thresholds.
        """
        info       = self.lab_lookup[lab]
        low, high  = info["normal"]
        above      = value > high
        below      = value < low

        panic     = PANIC_THRESHOLDS.get(lab, {})
        critical  = False
        direction = None

        if panic.get("critical_high") and value > panic["critical_high"]:
            critical, direction = True, "high"

        # Supports new critical_low key (Platelets, Hemoglobin)
        if panic.get("critical_low") and value < panic["critical_low"]:
            critical, direction = True, "low"

        # Legacy low key support
        if not critical and panic.get("low") and value < panic["low"]:
            critical, direction = True, "low"

        return above, below, critical, direction

    def _aki_stage(
        self, lab: str, current: float, admission_value: float | None
    ) -> str | None:
        """KDIGO AKI staging based on creatinine ratio vs admission value."""
        if lab != "Creatinine" or not admission_value:
            return None
        ratio = current / admission_value
        if ratio >= 3.0 or current >= 4.0:
            return "Stage 3"
        if ratio >= 2.0:
            return "Stage 2"
        if ratio >= 1.5:
            return "Stage 1"
        return "No AKI"

    #Output builder 
    def _build_output(
        self,
        df: pd.DataFrame,
        intime: pd.Timestamp | None,
        outtime: pd.Timestamp | None,
    ) -> tuple[dict, list, list, list]:

        timeline_by_test: dict      = {}
        critical_values:  list[dict] = []
        abnormal_values:  list[dict] = []
        outlier_flags:    list[dict] = []

        for lab in df["lab_name"].unique():
            sub     = df[df["lab_name"] == lab].sort_values("charttime")
            unit    = sub.iloc[0].get("unit", "")
            history: list[float] = []
            timeline: list[dict] = []
            prev:    float | None = None
            admission_value: float | None = None

            for _, row in sub.iterrows():
                val = float(row["valuenum"])

                if admission_value is None:
                    admission_value = val

                outlier_info          = self._detect_outlier(val, history)
                trend, delta          = self._trend(val, prev)
                above, below, critical, direction = self._check_flags(lab, val)
                aki_stage             = self._aki_stage(lab, val, admission_value)

                entry: dict = {
                    "timestamp":    row["charttime"].isoformat(),
                    "value":        val,
                    "unit":         unit,
                    "delta":        round(float(delta), 3),
                    "delta_pct":    round(abs(delta) / prev * 100 if prev else 0, 1),
                    "above_normal": above,
                    "below_normal": below,
                    "trend":        trend,
                    "outlier":      outlier_info,
                }
                if aki_stage:
                    entry["aki_stage"] = aki_stage

                timeline.append(entry)
                history.append(val)
                prev = val

                if critical:
                    critical_values.append({
                        "test":       lab,
                        "value":      val,
                        "timestamp":  row["charttime"].isoformat(),
                        "direction":  direction,
                        "is_outlier": outlier_info["is_outlier"],
                    })

                if above or below:
                    abnormal_values.append({
                        "test":      lab,
                        "value":     val,
                        "timestamp": row["charttime"].isoformat(),
                        "type":      "high" if above else "low",
                    })

                if outlier_info["is_outlier"]:
                    outlier_flags.append({
                        "test":             lab,
                        "value":            val,
                        "unit":             unit,
                        "timestamp":        row["charttime"].isoformat(),
                        "z_score":          outlier_info["z_score"],
                        "rolling_mean":     outlier_info["rolling_mean"],
                        "rolling_std":      outlier_info["rolling_std"],
                        "redraw_required":  True,
                        "redraw_confirmed": False,   # Chief Agent sets True after verification
                    })

            timeline_by_test[lab] = timeline

        return timeline_by_test, critical_values, abnormal_values, outlier_flags

    #Public process method 
    def process(self, subject_id: int, hadm_id: int) -> dict:
        df                    = self._filter_patient(subject_id, hadm_id)
        df, intime, outtime   = self._apply_icu_window(df, subject_id, hadm_id)
        df                    = self._filter_labs(df)
        df                    = self._clean(df)
        df                    = self._map_names(df)
        df                    = self._deduplicate(df)

        if df.empty:
            logger.warning("No lab data for subject=%s hadm=%s", subject_id, hadm_id)
            return {
                "agent":                "lab_mapper",
                "subject_id":          subject_id,
                "hadm_id":             hadm_id,
                "timeline_by_test":    {},
                "critical_values":     [],
                "abnormal_values":     [],
                "outlier_flags":       [],
                "icu_duration_hours":  0,
                "days_of_data":        0,
                "labs_available":      [],
                "sofa_inputs_available": set(),
                "sofa_coverage_pct":   0.0,
            }

        timeline, critical, abnormal, outliers = self._build_output(df, intime, outtime)

        icu_hours      = round((outtime - intime).total_seconds() / 3600, 1) if intime and outtime else 0
        available_labs = list(timeline.keys())

        # SOFA_LABS imported from lab_ranges 
        sofa_coverage  = SOFA_LABS & set(available_labs)

        logger.info(
            "LabMapper — %d labs | %d critical | %d outliers | SOFA %.0f%%",
            len(available_labs), len(critical), len(outliers),
            round(len(sofa_coverage) / len(SOFA_LABS) * 100, 1),
        )

        return {
            "agent":                "lab_mapper",
            "subject_id":          subject_id,
            "hadm_id":             hadm_id,
            "timeline_by_test":    timeline,
            "critical_values":     critical,
            "abnormal_values":     abnormal,
            "outlier_flags":       outliers,
            "icu_duration_hours":  icu_hours,
            "days_of_data":        max(1, (df["charttime"].max() - df["charttime"].min()).days + 1),
            "labs_available":      available_labs,
            "sofa_inputs_available": sofa_coverage,
            "sofa_coverage_pct":   round(len(sofa_coverage) / len(SOFA_LABS) * 100, 1),
        }

#Runners 
def run_lab_mapper(lab_input: dict) -> dict:
    return LabMapperAgent().process(lab_input["subject_id"], lab_input["hadm_id"])
def save_lab_mapper_output(result: dict, base_dir: str = "backend/outputs") -> Path:
    sid = result["subject_id"]
    hid = result["hadm_id"]
    ts  = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    out_dir  = Path(base_dir) / "lab_mapper" / f"sub_{sid}" / f"hadm_{hid}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"lab_mapper_{ts}.json"

    with open(out_file, "w") as f:
        json.dump(result, f, indent=2, default=str)

    logger.info("Saved → %s", out_file)
    return out_file


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
    result = run_lab_mapper({"subject_id": 42321, "hadm_id": 114648})
    save_lab_mapper_output(result)