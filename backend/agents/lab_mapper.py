import pandas as pd
from pathlib import Path
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
            return df

        intime = pd.to_datetime(icu.iloc[0]["intime"])
        outtime = pd.to_datetime(icu.iloc[0]["outtime"])

        df["charttime"] = pd.to_datetime(df["charttime"], errors="coerce")

        df = df[
            (df["charttime"] >= intime) &
            (df["charttime"] <= outtime)
        ]

        return df
    #lab selection
    def filter_labs(self, df):
        return df[df["itemid"].isin(ICU_CRITICAL_LABS.keys())]

    #data cleaning(remove null,unit conversions)
    def clean_data(self, df):
        df = df[df["valuenum"].notna()]
        df = df[df["charttime"].notna()]
        df["charttime"] = pd.to_datetime(df["charttime"])
        return df

    #map features to the the labs defined
    def map_names(self, df):
        df["lab_name"] = df["itemid"].map(
            lambda x: ICU_CRITICAL_LABS[x]["name"]
        )
        return df


    def deduplicate(self, df):
        df = df.sort_values("charttime")
        df["time_bucket"] = df["charttime"].dt.floor("30min")
        df = df.groupby(["lab_name", "time_bucket"], as_index=False).last()
        return df

    #trend analysis(increase,decrease,stable)
    def calculate_trend(self, current, previous):
        if previous is None:
            return "stable", 0

        delta = current - previous

        if abs(delta) < 0.05 * previous:
            return "stable", delta
        elif delta > 0:
            return "rising", delta
        else:
            return "falling", delta

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
    
    #output formatting
    def build_output(self, df):
        timeline_by_test = {}
        critical_values = []
        abnormal_values=[]

        for lab in df["lab_name"].unique():

            sub = df[df["lab_name"] == lab].sort_values("charttime")

            timeline = []
            prev = None

            for _, row in sub.iterrows():
                val = float(row["valuenum"])

                trend, delta = self.calculate_trend(val, prev)
                prev = val

                above, below, critical, direction = self.check_flags(lab, val)

                entry = {
                    "timestamp": row["charttime"].isoformat(),
                    "value": val,
                    "delta": round(delta, 2),
                    "above_normal": above,
                    "trend": trend
                }

                timeline.append(entry)

                if critical:
                    critical_values.append({
                        "test": lab,
                        "value": val,
                        "timestamp": row["charttime"].isoformat(),
                        "direction": direction
                    })
                    
                if above or below:
                    abnormal_values.append({
                        "test":lab,
                        "value":val,
                        "timestamp":row["charttime"].isoformat(),
                        "type":"high" if above else "low"
                    })

            timeline_by_test[lab] = timeline

        return timeline_by_test, critical_values,abnormal_values

    def process(self, subject_id, hadm_id):

        df = self.filter(subject_id, hadm_id)
        df = self.apply_icu_window(df, subject_id, hadm_id)
        df = self.filter_labs(df)
        df = self.clean_data(df)
        df = self.map_names(df)
        df = self.deduplicate(df)

        timeline, critical_values,abnormal_values = self.build_output(df)

        if df.empty:
            days = 0
        else:
            days = max(1, (df["charttime"].max() - df["charttime"].min()).days + 1)

        return {
            "agent": "lab_mapper",
            "timeline_by_test": timeline,
            "critical_values": critical_values,
            "abnormal_values":abnormal_values,
            "days_of_data": days
        }

def run_lab_mapper(lab_input):
    subject_id = lab_input["subject_id"]
    hadm_id = lab_input["hadm_id"]

    agent = LabMapperAgent()
    process =  agent.process(subject_id, hadm_id)
    print(process)

lab_input = {
    "subject_id": 42321,
    "hadm_id": 114648
}

run_lab_mapper(lab_input)