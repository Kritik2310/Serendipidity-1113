export type RiskLevel = "high" | "medium" | "low"

export interface Patient {
  id: string
  name: string
  age: number
  gender: "Male" | "Female"
  admissionDate: string
  status: string
  riskLevel: RiskLevel
  condition: string
  bedNumber: string
  vitals: {
    heartRate: number
    bloodPressure: string
    temperature: number
    oxygenSaturation: number
  }
}

export interface LabResult {
  name: string
  value: number
  unit: string
  normalRange: string
  status: "normal" | "abnormal" | "critical"
  trend: { time: string; value: number }[]
}

export interface Alert {
  id: string
  type: "critical" | "abnormal"
  message: string
  timestamp: string
}

export interface ClinicalNote {
  id: string
  content: string
  timestamp: string
}

export interface Guideline {
  id: string
  title: string
  description: string
  source: string
}

export interface HistoricInsight {
  id: string
  window: string
  signal: string
  impact: string
}

export interface RealTimeInsight {
  id: string
  metric: string
  value: string
  status: "normal" | "watch" | "critical"
  updatedAt: string
}

export interface DiseaseProgression {
  stage: string
  trendDirection: "improving" | "stable" | "worsening"
  riskDeltaPercent: number
  summary: string
  next24hOutlook: string
  historicInsights: HistoricInsight[]
  realTimeInsights: RealTimeInsight[]
  timeline: ProgressionPoint[]
}

export interface ProgressionPoint {
  time: string
  source: "Historic" | "Real-time"
  score: number
}

export const patients: Patient[] = [
  {
    id: "P001",
    name: "John Martinez",
    age: 67,
    gender: "Male",
    admissionDate: "2026-03-29",
    status: "Critical",
    riskLevel: "high",
    condition: "Early Sepsis Risk",
    bedNumber: "ICU-12",
    vitals: {
      heartRate: 112,
      bloodPressure: "90/60",
      temperature: 38.9,
      oxygenSaturation: 91,
    },
  },
  {
    id: "P002",
    name: "Sarah Johnson",
    age: 54,
    gender: "Female",
    admissionDate: "2026-03-28",
    status: "Monitoring",
    riskLevel: "medium",
    condition: "Respiratory Distress",
    bedNumber: "ICU-08",
    vitals: {
      heartRate: 95,
      bloodPressure: "110/75",
      temperature: 37.8,
      oxygenSaturation: 94,
    },
  },
  {
    id: "P003",
    name: "Michael Chen",
    age: 45,
    gender: "Male",
    admissionDate: "2026-03-27",
    status: "Stable",
    riskLevel: "low",
    condition: "Post-Surgery Recovery",
    bedNumber: "ICU-05",
    vitals: {
      heartRate: 72,
      bloodPressure: "125/82",
      temperature: 36.8,
      oxygenSaturation: 98,
    },
  },
  {
    id: "P004",
    name: "Emily Davis",
    age: 72,
    gender: "Female",
    admissionDate: "2026-03-30",
    status: "Critical",
    riskLevel: "high",
    condition: "Acute Kidney Injury",
    bedNumber: "ICU-03",
    vitals: {
      heartRate: 105,
      bloodPressure: "85/55",
      temperature: 38.2,
      oxygenSaturation: 89,
    },
  },
  {
    id: "P005",
    name: "Robert Wilson",
    age: 58,
    gender: "Male",
    admissionDate: "2026-03-31",
    status: "Monitoring",
    riskLevel: "medium",
    condition: "Cardiac Arrhythmia",
    bedNumber: "ICU-07",
    vitals: {
      heartRate: 88,
      bloodPressure: "130/85",
      temperature: 37.2,
      oxygenSaturation: 96,
    },
  },
  {
    id: "P006",
    name: "Lisa Thompson",
    age: 41,
    gender: "Female",
    admissionDate: "2026-03-26",
    status: "Stable",
    riskLevel: "low",
    condition: "Pneumonia Recovery",
    bedNumber: "ICU-11",
    vitals: {
      heartRate: 76,
      bloodPressure: "118/78",
      temperature: 37.0,
      oxygenSaturation: 97,
    },
  },
  {
    id: "P007",
    name: "Aisha Khan",
    age: 63,
    gender: "Female",
    admissionDate: "2026-03-30",
    status: "Monitoring",
    riskLevel: "medium",
    condition: "COPD Exacerbation",
    bedNumber: "ICU-02",
    vitals: {
      heartRate: 99,
      bloodPressure: "116/70",
      temperature: 37.6,
      oxygenSaturation: 92,
    },
  },
  {
    id: "P008",
    name: "Daniel Brooks",
    age: 36,
    gender: "Male",
    admissionDate: "2026-03-25",
    status: "Stable",
    riskLevel: "low",
    condition: "Trauma Observation",
    bedNumber: "ICU-04",
    vitals: {
      heartRate: 79,
      bloodPressure: "122/80",
      temperature: 36.9,
      oxygenSaturation: 97,
    },
  },
  {
    id: "P009",
    name: "Priya Nair",
    age: 49,
    gender: "Female",
    admissionDate: "2026-03-28",
    status: "Monitoring",
    riskLevel: "medium",
    condition: "Diabetic Ketoacidosis",
    bedNumber: "ICU-09",
    vitals: {
      heartRate: 102,
      bloodPressure: "108/68",
      temperature: 37.4,
      oxygenSaturation: 95,
    },
  },
  {
    id: "P010",
    name: "George Patel",
    age: 74,
    gender: "Male",
    admissionDate: "2026-03-31",
    status: "Critical",
    riskLevel: "high",
    condition: "Septic Shock Watch",
    bedNumber: "ICU-01",
    vitals: {
      heartRate: 118,
      bloodPressure: "88/52",
      temperature: 39.1,
      oxygenSaturation: 90,
    },
  },
  {
    id: "P011",
    name: "Meera Iyer",
    age: 29,
    gender: "Female",
    admissionDate: "2026-03-27",
    status: "Stable",
    riskLevel: "low",
    condition: "Postpartum Hemorrhage Recovery",
    bedNumber: "ICU-10",
    vitals: {
      heartRate: 81,
      bloodPressure: "120/76",
      temperature: 36.7,
      oxygenSaturation: 98,
    },
  },
  {
    id: "P012",
    name: "Carlos Mendes",
    age: 52,
    gender: "Male",
    admissionDate: "2026-03-29",
    status: "Stable",
    riskLevel: "low",
    condition: "Pancreatitis Recovery",
    bedNumber: "ICU-06",
    vitals: {
      heartRate: 84,
      bloodPressure: "124/81",
      temperature: 37.1,
      oxygenSaturation: 97,
    },
  },
]

const highRiskLabs: LabResult[] = [
  {
    name: "Creatinine",
    value: 2.8,
    unit: "mg/dL",
    normalRange: "0.7-1.3",
    status: "critical",
    trend: [
      { time: "00:00", value: 1.6 },
      { time: "04:00", value: 1.9 },
      { time: "08:00", value: 2.2 },
      { time: "12:00", value: 2.4 },
      { time: "16:00", value: 2.6 },
      { time: "20:00", value: 2.8 },
    ],
  },
  {
    name: "Lactate",
    value: 4.2,
    unit: "mmol/L",
    normalRange: "0.5-2.0",
    status: "critical",
    trend: [
      { time: "00:00", value: 2.4 },
      { time: "04:00", value: 2.8 },
      { time: "08:00", value: 3.3 },
      { time: "12:00", value: 3.7 },
      { time: "16:00", value: 4.0 },
      { time: "20:00", value: 4.2 },
    ],
  },
  {
    name: "WBC",
    value: 15.8,
    unit: "K/uL",
    normalRange: "4.5-11.0",
    status: "abnormal",
    trend: [
      { time: "00:00", value: 12.1 },
      { time: "04:00", value: 13.3 },
      { time: "08:00", value: 14.2 },
      { time: "12:00", value: 14.9 },
      { time: "16:00", value: 15.4 },
      { time: "20:00", value: 15.8 },
    ],
  },
]

const mediumRiskLabs: LabResult[] = [
  {
    name: "Creatinine",
    value: 1.5,
    unit: "mg/dL",
    normalRange: "0.7-1.3",
    status: "abnormal",
    trend: [
      { time: "00:00", value: 1.7 },
      { time: "04:00", value: 1.6 },
      { time: "08:00", value: 1.6 },
      { time: "12:00", value: 1.5 },
      { time: "16:00", value: 1.5 },
      { time: "20:00", value: 1.5 },
    ],
  },
  {
    name: "Lactate",
    value: 2.3,
    unit: "mmol/L",
    normalRange: "0.5-2.0",
    status: "abnormal",
    trend: [
      { time: "00:00", value: 2.6 },
      { time: "04:00", value: 2.5 },
      { time: "08:00", value: 2.4 },
      { time: "12:00", value: 2.4 },
      { time: "16:00", value: 2.3 },
      { time: "20:00", value: 2.3 },
    ],
  },
  {
    name: "WBC",
    value: 12.0,
    unit: "K/uL",
    normalRange: "4.5-11.0",
    status: "abnormal",
    trend: [
      { time: "00:00", value: 13.0 },
      { time: "04:00", value: 12.8 },
      { time: "08:00", value: 12.5 },
      { time: "12:00", value: 12.3 },
      { time: "16:00", value: 12.1 },
      { time: "20:00", value: 12.0 },
    ],
  },
]

const lowRiskLabs: LabResult[] = [
  {
    name: "Creatinine",
    value: 1.1,
    unit: "mg/dL",
    normalRange: "0.7-1.3",
    status: "normal",
    trend: [
      { time: "00:00", value: 1.2 },
      { time: "04:00", value: 1.1 },
      { time: "08:00", value: 1.1 },
      { time: "12:00", value: 1.1 },
      { time: "16:00", value: 1.1 },
      { time: "20:00", value: 1.1 },
    ],
  },
  {
    name: "Lactate",
    value: 1.5,
    unit: "mmol/L",
    normalRange: "0.5-2.0",
    status: "normal",
    trend: [
      { time: "00:00", value: 1.7 },
      { time: "04:00", value: 1.6 },
      { time: "08:00", value: 1.6 },
      { time: "12:00", value: 1.5 },
      { time: "16:00", value: 1.5 },
      { time: "20:00", value: 1.5 },
    ],
  },
  {
    name: "WBC",
    value: 8.2,
    unit: "K/uL",
    normalRange: "4.5-11.0",
    status: "normal",
    trend: [
      { time: "00:00", value: 9.0 },
      { time: "04:00", value: 8.8 },
      { time: "08:00", value: 8.6 },
      { time: "12:00", value: 8.4 },
      { time: "16:00", value: 8.3 },
      { time: "20:00", value: 8.2 },
    ],
  },
]

type BaseDiseaseProgression = Omit<DiseaseProgression, "timeline">

const diseaseProgressionByPatient: Record<string, BaseDiseaseProgression> = {
  P001: {
    stage: "Early septic progression",
    trendDirection: "worsening",
    riskDeltaPercent: 16,
    summary: "Inflammatory markers are rising with persistent hypotension, increasing short-term deterioration risk.",
    next24hOutlook: "High likelihood of vasopressor escalation if lactate remains above 4.0 mmol/L.",
    historicInsights: [
      {
        id: "HP001-1",
        window: "Last 72h",
        signal: "Lactate increased from 2.1 to 4.2 mmol/L",
        impact: "Strong correlation with early sepsis progression.",
      },
      {
        id: "HP001-2",
        window: "Last 48h",
        signal: "Sustained MAP below ICU target",
        impact: "Suggests unstable perfusion state.",
      },
    ],
    realTimeInsights: [
      {
        id: "RP001-1",
        metric: "Lactate",
        value: "4.2 mmol/L",
        status: "critical",
        updatedAt: "6 min ago",
      },
      {
        id: "RP001-2",
        metric: "Blood Pressure",
        value: "90/60 mmHg",
        status: "critical",
        updatedAt: "2 min ago",
      },
    ],
  },
  P002: {
    stage: "Respiratory stabilization phase",
    trendDirection: "stable",
    riskDeltaPercent: -4,
    summary: "Gas exchange has mildly improved while tachycardia persists during mobilization periods.",
    next24hOutlook: "Likely to remain in monitored range with oxygen support optimization.",
    historicInsights: [
      {
        id: "HP002-1",
        window: "Last 48h",
        signal: "SpO2 improved from 91% to 94%",
        impact: "Reduced acute hypoxia burden.",
      },
      {
        id: "HP002-2",
        window: "Last 24h",
        signal: "Respiratory rate variability narrowed",
        impact: "Less frequent distress episodes.",
      },
    ],
    realTimeInsights: [
      {
        id: "RP002-1",
        metric: "SpO2",
        value: "94%",
        status: "watch",
        updatedAt: "3 min ago",
      },
      {
        id: "RP002-2",
        metric: "Heart Rate",
        value: "95 bpm",
        status: "watch",
        updatedAt: "1 min ago",
      },
    ],
  },
  P003: {
    stage: "Post-operative recovery",
    trendDirection: "improving",
    riskDeltaPercent: -9,
    summary: "Hemodynamics and inflammatory markers continue to normalize post procedure.",
    next24hOutlook: "Expected to stay stable and may qualify for step-down evaluation.",
    historicInsights: [
      {
        id: "HP003-1",
        window: "Last 72h",
        signal: "Pain score declined from 6/10 to 2/10",
        impact: "Indicates recovery trajectory.",
      },
      {
        id: "HP003-2",
        window: "Last 48h",
        signal: "WBC trended toward normal",
        impact: "Lower concern for post-op infection.",
      },
    ],
    realTimeInsights: [
      {
        id: "RP003-1",
        metric: "Temperature",
        value: "36.8 C",
        status: "normal",
        updatedAt: "5 min ago",
      },
      {
        id: "RP003-2",
        metric: "Oxygen Saturation",
        value: "98%",
        status: "normal",
        updatedAt: "2 min ago",
      },
    ],
  },
  P004: {
    stage: "AKI active phase",
    trendDirection: "worsening",
    riskDeltaPercent: 13,
    summary: "Renal markers and urine output pattern indicate active kidney injury progression.",
    next24hOutlook: "High chance of nephrology escalation if creatinine trend continues upward.",
    historicInsights: [
      {
        id: "HP004-1",
        window: "Last 72h",
        signal: "Creatinine rose from 1.3 to 2.8 mg/dL",
        impact: "Consistent with AKI stage progression.",
      },
      {
        id: "HP004-2",
        window: "Last 24h",
        signal: "Urine output dropped below target",
        impact: "Suggests impaired renal clearance.",
      },
    ],
    realTimeInsights: [
      {
        id: "RP004-1",
        metric: "Creatinine",
        value: "2.8 mg/dL",
        status: "critical",
        updatedAt: "8 min ago",
      },
      {
        id: "RP004-2",
        metric: "Blood Pressure",
        value: "85/55 mmHg",
        status: "critical",
        updatedAt: "2 min ago",
      },
    ],
  },
  P005: {
    stage: "Arrhythmia control phase",
    trendDirection: "stable",
    riskDeltaPercent: -2,
    summary: "Rate control is effective with occasional rhythm variability during activity.",
    next24hOutlook: "Expected to stay medium-risk with telemetry surveillance.",
    historicInsights: [
      {
        id: "HP005-1",
        window: "Last 48h",
        signal: "Heart rate peaks reduced from 126 to 102 bpm",
        impact: "Lower arrhythmic burden.",
      },
      {
        id: "HP005-2",
        window: "Last 24h",
        signal: "No sustained ventricular episodes",
        impact: "Improved electrical stability.",
      },
    ],
    realTimeInsights: [
      {
        id: "RP005-1",
        metric: "Heart Rate",
        value: "88 bpm",
        status: "watch",
        updatedAt: "1 min ago",
      },
      {
        id: "RP005-2",
        metric: "Blood Pressure",
        value: "130/85 mmHg",
        status: "normal",
        updatedAt: "4 min ago",
      },
    ],
  },
  P006: {
    stage: "Pulmonary recovery",
    trendDirection: "improving",
    riskDeltaPercent: -7,
    summary: "Infection burden is down and oxygen needs are trending lower.",
    next24hOutlook: "Likely to maintain stable respiratory status on current plan.",
    historicInsights: [
      {
        id: "HP006-1",
        window: "Last 72h",
        signal: "CRP and WBC both declined",
        impact: "Suggests response to therapy.",
      },
      {
        id: "HP006-2",
        window: "Last 24h",
        signal: "No fever spikes observed",
        impact: "Lower acute flare risk.",
      },
    ],
    realTimeInsights: [
      {
        id: "RP006-1",
        metric: "SpO2",
        value: "97%",
        status: "normal",
        updatedAt: "2 min ago",
      },
      {
        id: "RP006-2",
        metric: "Temperature",
        value: "37.0 C",
        status: "normal",
        updatedAt: "6 min ago",
      },
    ],
  },
  P007: {
    stage: "COPD exacerbation control",
    trendDirection: "stable",
    riskDeltaPercent: 1,
    summary: "Airflow limitation persists, but current bronchodilator and oxygen strategy is holding.",
    next24hOutlook: "Moderate probability of transient desaturation during exertion.",
    historicInsights: [
      {
        id: "HP007-1",
        window: "Last 48h",
        signal: "Nighttime desaturation episodes reduced from 5 to 2",
        impact: "Improving nocturnal control.",
      },
      {
        id: "HP007-2",
        window: "Last 24h",
        signal: "ABG CO2 remained mildly elevated",
        impact: "Ongoing ventilatory watch needed.",
      },
    ],
    realTimeInsights: [
      {
        id: "RP007-1",
        metric: "SpO2",
        value: "92%",
        status: "watch",
        updatedAt: "2 min ago",
      },
      {
        id: "RP007-2",
        metric: "Heart Rate",
        value: "99 bpm",
        status: "watch",
        updatedAt: "1 min ago",
      },
    ],
  },
  P008: {
    stage: "Trauma observation recovery",
    trendDirection: "improving",
    riskDeltaPercent: -6,
    summary: "No new bleeding indicators with stable hemodynamics across observation windows.",
    next24hOutlook: "Low likelihood of acute deterioration if trend remains unchanged.",
    historicInsights: [
      {
        id: "HP008-1",
        window: "Last 72h",
        signal: "Hemoglobin remained stable",
        impact: "Low concern for delayed bleed.",
      },
      {
        id: "HP008-2",
        window: "Last 24h",
        signal: "Pain and agitation scores decreased",
        impact: "Improved recovery tolerance.",
      },
    ],
    realTimeInsights: [
      {
        id: "RP008-1",
        metric: "Blood Pressure",
        value: "122/80 mmHg",
        status: "normal",
        updatedAt: "4 min ago",
      },
      {
        id: "RP008-2",
        metric: "Heart Rate",
        value: "79 bpm",
        status: "normal",
        updatedAt: "1 min ago",
      },
    ],
  },
  P009: {
    stage: "DKA correction phase",
    trendDirection: "stable",
    riskDeltaPercent: -3,
    summary: "Anion gap is closing but glucose oscillation still requires insulin titration.",
    next24hOutlook: "Likely medium-risk until metabolic panel fully normalizes.",
    historicInsights: [
      {
        id: "HP009-1",
        window: "Last 48h",
        signal: "Serum ketones dropped steadily",
        impact: "Metabolic correction underway.",
      },
      {
        id: "HP009-2",
        window: "Last 24h",
        signal: "Anion gap reduced from 24 to 15",
        impact: "Improved acid-base status.",
      },
    ],
    realTimeInsights: [
      {
        id: "RP009-1",
        metric: "Capillary Glucose",
        value: "228 mg/dL",
        status: "watch",
        updatedAt: "5 min ago",
      },
      {
        id: "RP009-2",
        metric: "Heart Rate",
        value: "102 bpm",
        status: "watch",
        updatedAt: "2 min ago",
      },
    ],
  },
  P010: {
    stage: "Shock progression watch",
    trendDirection: "worsening",
    riskDeltaPercent: 18,
    summary: "Combined hypotension, fever, and tachycardia suggest rapid sepsis-shock progression risk.",
    next24hOutlook: "Very high deterioration risk without aggressive hemodynamic support.",
    historicInsights: [
      {
        id: "HP010-1",
        window: "Last 48h",
        signal: "MAP trended down despite fluids",
        impact: "Suggests poor hemodynamic reserve.",
      },
      {
        id: "HP010-2",
        window: "Last 24h",
        signal: "Fever curve increased to 39.1 C",
        impact: "Elevated inflammatory stress.",
      },
    ],
    realTimeInsights: [
      {
        id: "RP010-1",
        metric: "Blood Pressure",
        value: "88/52 mmHg",
        status: "critical",
        updatedAt: "1 min ago",
      },
      {
        id: "RP010-2",
        metric: "Heart Rate",
        value: "118 bpm",
        status: "critical",
        updatedAt: "1 min ago",
      },
    ],
  },
  P011: {
    stage: "Postpartum stabilization",
    trendDirection: "improving",
    riskDeltaPercent: -8,
    summary: "Hemodynamic profile and hemoglobin trajectory indicate ongoing recovery.",
    next24hOutlook: "Low risk of relapse if bleeding markers remain controlled.",
    historicInsights: [
      {
        id: "HP011-1",
        window: "Last 72h",
        signal: "Hemoglobin improved after transfusion",
        impact: "Lower risk of hypovolemic recurrence.",
      },
      {
        id: "HP011-2",
        window: "Last 24h",
        signal: "No fresh bleeding events recorded",
        impact: "Supports de-escalation planning.",
      },
    ],
    realTimeInsights: [
      {
        id: "RP011-1",
        metric: "Blood Pressure",
        value: "120/76 mmHg",
        status: "normal",
        updatedAt: "3 min ago",
      },
      {
        id: "RP011-2",
        metric: "SpO2",
        value: "98%",
        status: "normal",
        updatedAt: "2 min ago",
      },
    ],
  },
  P012: {
    stage: "Pancreatitis resolution",
    trendDirection: "improving",
    riskDeltaPercent: -5,
    summary: "Inflammatory and pain trends are decreasing with stable organ support metrics.",
    next24hOutlook: "Likely continued low-risk progression if oral tolerance remains adequate.",
    historicInsights: [
      {
        id: "HP012-1",
        window: "Last 48h",
        signal: "Lipase values declined",
        impact: "Favors resolving pancreatitis phase.",
      },
      {
        id: "HP012-2",
        window: "Last 24h",
        signal: "Pain control requirements decreased",
        impact: "Improved clinical comfort and recovery.",
      },
    ],
    realTimeInsights: [
      {
        id: "RP012-1",
        metric: "Temperature",
        value: "37.1 C",
        status: "normal",
        updatedAt: "4 min ago",
      },
      {
        id: "RP012-2",
        metric: "Heart Rate",
        value: "84 bpm",
        status: "normal",
        updatedAt: "1 min ago",
      },
    ],
  },
}

export function getPatientById(id: string): Patient | undefined {
  return patients.find((patient) => patient.id === id)
}

export function getLabResultsForPatient(patientId: string): LabResult[] {
  const patient = getPatientById(patientId)
  if (!patient) return []

  if (patient.riskLevel === "high") return highRiskLabs
  if (patient.riskLevel === "medium") return mediumRiskLabs
  return lowRiskLabs
}

export function getAlertsForPatient(patientId: string): Alert[] {
  const patient = getPatientById(patientId)
  if (!patient) return []

  if (patient.riskLevel === "high") {
    return [
      {
        id: `${patient.id}-A001`,
        type: "critical",
        message: "Hemodynamic instability detected - immediate reassessment advised",
        timestamp: "10 min ago",
      },
      {
        id: `${patient.id}-A002`,
        type: "critical",
        message: "Inflammatory markers remain above target threshold",
        timestamp: "24 min ago",
      },
      {
        id: `${patient.id}-A003`,
        type: "abnormal",
        message: "Ongoing perfusion concern based on pressure trend",
        timestamp: "1 hour ago",
      },
    ]
  }

  if (patient.riskLevel === "medium") {
    return [
      {
        id: `${patient.id}-A001`,
        type: "abnormal",
        message: "Moderate physiologic variability detected",
        timestamp: "22 min ago",
      },
      {
        id: `${patient.id}-A002`,
        type: "abnormal",
        message: "Close trend monitoring recommended",
        timestamp: "52 min ago",
      },
    ]
  }

  return [
    {
      id: `${patient.id}-A001`,
      type: "abnormal",
      message: "No active critical alerts; continue routine monitoring",
      timestamp: "2 hours ago",
    },
  ]
}

export function getNotesForPatient(patientId: string): ClinicalNote[] {
  const patient = getPatientById(patientId)
  if (!patient) return []

  if (patient.riskLevel === "high") {
    return [
      { id: `${patient.id}-N001`, content: "Escalation criteria reviewed with bedside team.", timestamp: "Today" },
      { id: `${patient.id}-N002`, content: "Perfusion and urine output require hourly review.", timestamp: "Today" },
      { id: `${patient.id}-N003`, content: "Family updated on high-acuity status.", timestamp: "Yesterday" },
    ]
  }

  if (patient.riskLevel === "medium") {
    return [
      { id: `${patient.id}-N001`, content: "Patient responding to current management plan.", timestamp: "Today" },
      { id: `${patient.id}-N002`, content: "Vitals remain within monitored variance.", timestamp: "Today" },
      { id: `${patient.id}-N003`, content: "No new urgent intervention required this shift.", timestamp: "Yesterday" },
    ]
  }

  return [
    { id: `${patient.id}-N001`, content: "Clinical trajectory remains stable.", timestamp: "Today" },
    { id: `${patient.id}-N002`, content: "Recovery milestones achieved for current care plan.", timestamp: "Today" },
    { id: `${patient.id}-N003`, content: "Continue step-down readiness checks.", timestamp: "Yesterday" },
  ]
}

export function getGuidelinesForPatient(patientId: string): Guideline[] {
  const patient = getPatientById(patientId)
  if (!patient) return []

  if (patient.condition.includes("Sepsis")) {
    return [
      {
        id: `${patient.id}-G001`,
        title: "Sepsis Bundle",
        description: "Complete blood culture, early antimicrobials, and hemodynamic support bundle per protocol.",
        source: "Surviving Sepsis Campaign",
      },
      {
        id: `${patient.id}-G002`,
        title: "Perfusion Monitoring",
        description: "Track lactate clearance and MAP response every hour during instability window.",
        source: "ICU Internal Protocol",
      },
    ]
  }

  if (patient.condition.includes("Kidney")) {
    return [
      {
        id: `${patient.id}-G001`,
        title: "AKI Risk Stratification",
        description: "Trend creatinine kinetics and urine output to determine stage progression and intervention timing.",
        source: "KDIGO AKI Guidance",
      },
      {
        id: `${patient.id}-G002`,
        title: "Medication Renal Review",
        description: "Adjust nephrotoxic or renally-cleared medications based on dynamic kidney function.",
        source: "Hospital Renal Safety Checklist",
      },
    ]
  }

  return [
    {
      id: `${patient.id}-G001`,
      title: "Standard ICU Monitoring",
      description: "Continue vitals, labs, and reassessment cadence according to risk category and condition pathway.",
      source: "Hospital ICU Protocol",
    },
  ]
}

export function getDiseaseProgressionForPatient(patientId: string): DiseaseProgression | undefined {
  const progression = diseaseProgressionByPatient[patientId]
  if (!progression) return undefined

  return {
    ...progression,
    timeline: buildProgressionTimeline(progression.trendDirection, progression.riskDeltaPercent),
  }
}

function buildProgressionTimeline(
  trendDirection: DiseaseProgression["trendDirection"],
  riskDeltaPercent: number
): ProgressionPoint[] {
  const historicLabels = ["-72h", "-48h", "-24h", "-12h", "-6h"]
  const realtimeLabels = ["-30m", "Now"]

  const absoluteDelta = Math.max(Math.abs(riskDeltaPercent), 4)
  const step = Math.max(Math.round(absoluteDelta / 5), 1)

  let base = 50
  let direction = 0

  if (trendDirection === "worsening") {
    base = 45
    direction = 1
  } else if (trendDirection === "improving") {
    base = 68
    direction = -1
  }

  const historicSeries = historicLabels.map((label, index) => ({
    time: label,
    source: "Historic" as const,
    score:
      trendDirection === "stable"
        ? base + (index % 2 === 0 ? -1 : 1)
        : base + direction * step * index,
  }))

  const lastHistoricScore = historicSeries[historicSeries.length - 1].score
  const realtimeSeries = realtimeLabels.map((label, index) => ({
    time: label,
    source: "Real-time" as const,
    score:
      trendDirection === "stable"
        ? lastHistoricScore + (index === 0 ? 0 : 1)
        : lastHistoricScore + direction * (index + 1) * Math.max(step, 2),
  }))

  return [...historicSeries, ...realtimeSeries]
}
