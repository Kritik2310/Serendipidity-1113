import pandas as pd
import numpy as np
from pathlib import Path
import json
import datetime
from backend.utils.lab_ranges import ICU_CRITICAL_LABS,PANIC_THRESHOLDS

#path definition
# BASE_DIR = Path(__file__).resolve().parent.parent
# DATA_DIR = BASE_DIR / "data"

LAB_FILE = "backend/data/LABEVENTS.csv"
ICU_FILE = "backend/data/ICUSTAYS.csv"

class LabMapperAgent():
    
    def __init__(self):
        self.lab_df = pd.read_csv(LAB_FILE)
        self.icu_df = pd.read_csv(ICU_FILE)
        self.lab_lookup = {v["name"]: v for v in ICU_CRITICAL_LABS.values()}
        
    #patient filtering
    def filter(self,sub_id,hadm_id):
        ##considering patient's admission and stay days in ICU for monitoring n recurrence
        df = self.lab_df[(self.lab_df["subject_id"] == sub_id) & (self.lab_df["hadm_id"] == hadm_id)].copy()
        return df
    
    def apply_icu_window(self,df,sub_id,hadm_id):
        icu = self.icu_df[(self.icu_df["subject_id"] == sub_id) & (self.icu_df["hadm_id"] == hadm_id)]

        if icu.empty:
            return df,None,None

        intime = pd.to_datetime(icu.iloc[0]["intime"])
        outtime = pd.to_datetime(icu.iloc[0]["outtime"])
        df["charttime"] = pd.to_datetime(df["charttime"], errors="coerce")
        df = df[(df["charttime"] >= intime) & (df["charttime"] <= outtime)]

        return df,intime,outtime
    
    #lab selection
    def filter_labs(self, df):
        return df[df["itemid"].isin(ICU_CRITICAL_LABS.keys())]

    #data cleaning(remove null,unit conversions)
    def clean_data(self, df):
        df = df[df["valuenum"].notna() & df["charttime"].notna()].copy()
        df["charttime"] = pd.to_datetime(df["charttime"])
        return df

    #map features to the the labs defined
    def map_names(self, df):
        df["lab_name"] = df["itemid"].map(lambda x: ICU_CRITICAL_LABS[x]["name"])
        df["unit"] = df["itemid"].map(lambda x: ICU_CRITICAL_LABS[x].get("unit",""))
        return df

    def deduplicate(self, df):
        df = df.sort_values("charttime")
        df["time_bucket"] = df["charttime"].dt.floor("30min")
        df = df.groupby(["lab_name", "time_bucket"], as_index=False).last()
        return df

    #trend analysis(increase,decrease,stable)
    def calculate_trend(self, current, previous):
        if previous is None:
            return "stable", 0.0
        delta = current - previous
        pct = (abs(delta) / previous * 100) if previous !=0 else 0
        if pct < 5:
            return "stable",delta
        return ("rising" if delta > 0 else "falling"), delta
        
    def compute_rolling_stats(self, values: list[float], window: int = 3):
        if len(values) < 2:
            return None, None
        arr  = np.array(values[-window:])
        return float(arr.mean()), float(arr.std(ddof=0))

    def detect_outlier(self, value: float, history: list[float],z_threshold: float = 3.0) -> dict:
        if len(history) < 2:
            return {"is_outlier": False, "z_score": None, "rolling_mean": None,
                    "rolling_std": None, "redraw_required": False}

        mean, std = self.compute_rolling_stats(history)
        if std == 0 or std is None:
            return {"is_outlier": False, "z_score": None, "rolling_mean": mean,
                    "rolling_std": std, "redraw_required": False}

        z = (value - mean) / std
        is_outlier = abs(z) > z_threshold

        return {
            "is_outlier":      is_outlier,
            "z_score":         round(float(z), 3),
            "rolling_mean":    round(mean, 3),
            "rolling_std":     round(std, 3),
            "redraw_required": is_outlier   # Chief Agent gate flag
        }

    # threshold detection
    def check_flags(self, lab, value):
        lab_info = self.lab_lookup[lab]
        normal_low, normal_high = lab_info["normal"]

        above = value > normal_high
        below = value < normal_low

        panic = PANIC_THRESHOLDS.get(lab, {})
        critical = False
        direction = None

        if panic.get("critical_high") and value > panic["critical_high"]:
            critical = True
            direction = "high"

        if panic.get("low") and value < panic["low"]:
            critical = True
            direction = "low"

        return above, below, critical, direction
    
    def compute_aki_stage(self, lab: str, current: float,admission_value: float | None) -> str | None:
        
        if lab != "Creatinine" or admission_value is None or admission_value == 0:
            return None
        ratio = current / admission_value
        if ratio >= 3.0 or current >= 4.0:
            return "Stage 3"
        if ratio >= 2.0:
            return "Stage 2"
        if ratio >= 1.5:
            return "Stage 1"
        return "No AKI"
    
    #output formatting
    def build_output(self, df,intime,outtime):
        timeline_by_test = {}
        critical_values = []
        abnormal_values=[]
        outlier_flags = []

        for lab in df["lab_name"].unique():

            sub = df[df["lab_name"] == lab].sort_values("charttime")
            unit    = sub.iloc[0]["unit"] if "unit" in sub.columns else ""
            history = []
            timeline = []
            prev     = None
            admission_value = None 

            for _, row in sub.iterrows():
                val = float(row["valuenum"])

                if admission_value is None:
                    admission_value = val
                outlier_info = self.detect_outlier(val, history)
                trend, delta = self.calculate_trend(val, prev)
                above, below, critical, direction = self.check_flags(lab, val)
                aki_stage = self.compute_aki_stage(lab, val, admission_value)
                entry = {
                    "timestamp":        row["charttime"].isoformat(),
                    "value":            val,
                    "unit":             unit,
                    "delta":            round(float(delta), 3),
                    "delta_pct":        round(abs(delta) / prev * 100 if prev else 0, 1),
                    "above_normal":     above,
                    "below_normal":     below,   
                    "trend":            trend,
                    "outlier":          outlier_info,  
                    **({"aki_stage": aki_stage} if aki_stage else {})
                }

                timeline.append(entry)
                history.append(val)   # append AFTER outlier check
                prev = val

                if critical:
                    critical_values.append({
                        "test": lab,
                        "value": val,
                        "timestamp": row["charttime"].isoformat(),
                        "direction": direction,
                        "is_outlier": outlier_info["is_outlier"]
                    })
                    
                if above or below:
                    abnormal_values.append({
                        "test":lab,
                        "value":val,
                        "timestamp":row["charttime"].isoformat(),
                        "type":"high" if above else "low"
                    })
                if outlier_info["is_outlier"]:
                    outlier_flags.append({
                        "test":           lab,
                        "value":          val,
                        "unit":           unit,
                        "timestamp":      row["charttime"].isoformat(),
                        "z_score":        outlier_info["z_score"],
                        "rolling_mean":   outlier_info["rolling_mean"],
                        "rolling_std":    outlier_info["rolling_std"],
                        "redraw_required": True,
                        "redraw_confirmed": False   # Chief Agent sets this to True on redraw
                    })
                    
            timeline_by_test[lab] = timeline

        return timeline_by_test, critical_values,abnormal_values,outlier_flags 

    def process(self, subject_id: int, hadm_id: int) -> dict:
        df = self.filter(subject_id, hadm_id)
        df, intime, outtime = self.apply_icu_window(df, subject_id, hadm_id)
        df = self.filter_labs(df)
        df = self.clean_data(df)
        df = self.map_names(df)
        df = self.deduplicate(df)

        if df.empty:
            return {
                "agent": "lab_mapper", "subject_id": subject_id,
                "hadm_id": hadm_id, "timeline_by_test": {},
                "critical_values": [], "abnormal_values": [],
                "outlier_flags": [], "icu_duration_hours": 0,
                "days_of_data": 0, "labs_available": [],
                "sofa_inputs_available": False
            }

        timeline, critical, abnormal, outliers = self.build_output(df, intime, outtime)
        icu_hours = round(
            (outtime - intime).total_seconds() / 3600, 1
        ) if intime and outtime else 0

        available_labs = list(timeline.keys())
        sofa_labs_needed = {
            "Creatinine", "WBC", "Platelets", "Bilirubin",
            "Lactate", "Hemoglobin"
        }
        sofa_coverage = sofa_labs_needed & set(available_labs)

        return {
            "agent":               "lab_mapper",
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
            "sofa_coverage_pct":   round(len(sofa_coverage) / len(sofa_labs_needed) * 100, 1)
        }
def run_lab_mapper(lab_input):
    subject_id = lab_input["subject_id"]
    hadm_id = lab_input["hadm_id"]

    agent = LabMapperAgent()
    process =  agent.process(subject_id, hadm_id)
    print(process)

def save_lab_mapper_output(result: dict, base_dir: str = "backend/outputs") -> Path:
    subject_id = result["subject_id"]
    hadm_id    = result["hadm_id"]
    timestamp  = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    out_dir = (
        Path(base_dir)
        / "lab_mapper"
        / f"sub_{subject_id}"
        / f"hadm_{hadm_id}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / f"lab_mapper_{timestamp}.json"

    with open(out_file, "w") as f:
        json.dump(result, f, indent=2, default=str)

    print(f"Saved: {out_file}")
    return out_file

lab_input = {"subject_id": 42321,"hadm_id": 114648}
result = run_lab_mapper(lab_input)
save_lab_mapper_output(result)
