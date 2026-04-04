import type {
  Alert,
  ClinicalNote,
  DiseaseProgression,
  Guideline,
  HistoricInsight,
  LabResult,
  ProgressionPoint,
  RealTimeInsight,
  RiskLevel,
} from "@/lib/patient-data"

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || "http://127.0.0.1:8000"

export interface PrioritizedRisk {
  risk_flag: string
  status: string
  guideline_source: string
  explanation: string
  threshold: string
}

export interface DiseaseTimelineEvent {
  timestamp: string
  source: "clinical_note" | "lab_result"
  note_type?: string
  findings?: Array<Record<string, unknown>>
  test?: string
  value?: number
  unit?: string
  trend?: string
  above_normal?: boolean
  below_normal?: boolean
  is_outlier?: boolean
  aki_stage?: string | null
}

export interface AnalyzeResponse {
  subject_id: number
  hadm_id: number
  status: string
  agents_succeeded: string[]
  agents_failed: string[]
  primary_concern: string
  clinical_summary: string
  prioritized_risks: PrioritizedRisk[]
  recommended_actions: string[]
  excluded_outliers: Array<Record<string, unknown>>
  data_quality: {
    note_parser_available: boolean
    lab_mapper_available: boolean
    rag_available: boolean
    outliers_removed_count?: number
    sofa_coverage_pct: number
    [key: string]: unknown
  }
  doctor_handoff: string
  generated_at: string
  disease_timeline: DiseaseTimelineEvent[]
  family_communication: {
    time_window_hours: number
    regional_language: string
    regional_language_code: string
    english_summary: string
    regional_summary: string
    generated_at: string
  }
  disease_progression?: Array<{
    period: string
    observation: string
  }>
  safety_disclaimer: string
}

export interface PatientDirectoryEntry {
  subject_id: number
  hadm_id: number
  last_analyzed: number
}

export interface PatientSummary {
  analysisId: string
  subjectId: number
  hadmId: number
  status: string
  primaryConcern: string
  riskLevel: RiskLevel
  lastAnalyzed: string
}

export interface PatientReportBundle {
  summary: PatientSummary
  report: AnalyzeResponse | null
}

export interface StreamPayload {
  subject_id: number
  hadm_id: number
  primary_concern: string
  generated_at: string
  data_quality: Record<string, unknown>
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Request failed: ${response.status}`)
  }

  return response.json() as Promise<T>
}

export function buildAnalysisId(subjectId: number, hadmId: number): string {
  return `${subjectId}-${hadmId}`
}

export function parseAnalysisId(id: string): { subjectId: number; hadmId: number } {
  const [subjectPart, hadmPart] = id.split("-")
  const subjectId = Number(subjectPart)
  const hadmId = Number(hadmPart)

  if (Number.isNaN(subjectId) || Number.isNaN(hadmId)) {
    throw new Error(`Invalid analysis id: ${id}`)
  }

  return { subjectId, hadmId }
}

export function formatRiskFlag(riskFlag: string): string {
  return riskFlag
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

export function deriveRiskLevel(report: AnalyzeResponse): RiskLevel {
  const concern = report.primary_concern.toUpperCase()
  const supportedCount = report.prioritized_risks.filter((risk) => risk.status === "supported").length

  if (concern.includes("SHOCK") || supportedCount > 1) {
    return "high"
  }
  if (supportedCount === 1 || report.prioritized_risks.length > 0) {
    return "medium"
  }
  return "low"
}

export async function fetchPatients(): Promise<PatientDirectoryEntry[]> {
  const data = await apiRequest<{ patients: PatientDirectoryEntry[] }>("/patients")
  return data.patients
}

export async function fetchReport(subjectId: number, hadmId: number): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>(`/report/${subjectId}/${hadmId}`)
}

export async function analyzePatient(subjectId: number, hadmId: number): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/analyze", {
    method: "POST",
    body: JSON.stringify({
      subject_id: subjectId,
      hadm_id: hadmId,
    }),
  })
}

// Add after analyzePatient()

export async function fetchProgression(
  subjectId: number,
  hadmId: number
): Promise<DiseaseProgression | null> {
  try {
    const data = await apiRequest<{
      subject_id: number
      hadm_id: number
      stage: string
      trendDirection: "worsening" | "improving" | "stable"
      summary: string
      timeline: Array<{
        time: string
        score: number
        source: string
        summary: string
      }>
      historicInsights: HistoricInsight[]
      realTimeInsights: RealTimeInsight[]
    }>(`/progression/${subjectId}/${hadmId}`)

    return {
      stage:            data.stage,
      trendDirection:   data.trendDirection,
      riskDeltaPercent: 0,
      summary:          data.summary,
      next24hOutlook:   "Derived from real-time simulation data.",
      historicInsights: data.historicInsights,
      realTimeInsights: data.realTimeInsights,
      timeline: data.timeline.map((pt) => ({
        time:    pt.time,
        score:   pt.score,
        source:  pt.source === "Historical" ? "Historic" : "Real-time",
        summary: pt.summary,
      })),
    }
  } catch {
    return null
  }
}

export async function fetchPatientSummaries(): Promise<PatientSummary[]> {
  const directory = await fetchPatients()

  return Promise.all(
    directory.map(async (entry) => {
      try {
        const report = await fetchReport(entry.subject_id, entry.hadm_id)
        return {
          analysisId: buildAnalysisId(entry.subject_id, entry.hadm_id),
          subjectId: entry.subject_id,
          hadmId: entry.hadm_id,
          status: report.status,
          primaryConcern: report.primary_concern,
          riskLevel: deriveRiskLevel(report),
          lastAnalyzed: report.generated_at,
        }
      } catch {
        return {
          analysisId: buildAnalysisId(entry.subject_id, entry.hadm_id),
          subjectId: entry.subject_id,
          hadmId: entry.hadm_id,
          status: "unknown",
          primaryConcern: "Report unavailable",
          riskLevel: "low" as RiskLevel,
          lastAnalyzed: new Date(entry.last_analyzed * 1000).toISOString(),
        }
      }
    })
  )
}

export async function fetchAllPatientReports(): Promise<PatientReportBundle[]> {
  const directory = await fetchPatients()

  return Promise.all(
    directory.map(async (entry) => {
      const summary: PatientSummary = {
        analysisId: buildAnalysisId(entry.subject_id, entry.hadm_id),
        subjectId: entry.subject_id,
        hadmId: entry.hadm_id,
        status: "unknown",
        primaryConcern: "Report unavailable",
        riskLevel: "low",
        lastAnalyzed: new Date(entry.last_analyzed * 1000).toISOString(),
      }

      try {
        const report = await fetchReport(entry.subject_id, entry.hadm_id)
        return {
          summary: {
            ...summary,
            status: report.status,
            primaryConcern: report.primary_concern,
            riskLevel: deriveRiskLevel(report),
            lastAnalyzed: report.generated_at,
          },
          report,
        }
      } catch {
        return { summary, report: null }
      }
    })
  )
}

export function streamPatient(
  subjectId: number,
  hadmId: number,
  onMessage: (payload: StreamPayload) => void,
  onError?: (event: Event) => void
): EventSource {
  const source = new EventSource(`${API_BASE_URL}/stream/${subjectId}/${hadmId}`)

  source.onmessage = (event) => {
    onMessage(JSON.parse(event.data) as StreamPayload)
  }

  if (onError) {
    source.onerror = onError
  }

  return source
}

export function toLabResults(report: AnalyzeResponse): LabResult[] {
  const grouped = new Map<string, DiseaseTimelineEvent[]>()

  report.disease_timeline
    .filter((event) => event.source === "lab_result" && event.test)
    .forEach((event) => {
      const test = event.test as string
      const existing = grouped.get(test) || []
      existing.push(event)
      grouped.set(test, existing)
    })

  return Array.from(grouped.entries()).map(([test, entries]) => {
    const sorted = [...entries].sort((a, b) => a.timestamp.localeCompare(b.timestamp))
    const latest = sorted[sorted.length - 1]
    const status = sorted.some((entry) => entry.is_outlier)
      ? "critical"
      : sorted.some((entry) => entry.above_normal || entry.below_normal)
      ? "abnormal"
      : "normal"

    return {
      name: test,
      value: Number(latest.value || 0),
      unit: latest.unit || "",
      normalRange: "See ICU range",
      status,
      trend: sorted.map((entry) => ({
        time: new Date(entry.timestamp).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
        value: Number(entry.value || 0),
      })),
    }
  })
}

export function toAlerts(report: AnalyzeResponse): Alert[] {
  const alerts: Alert[] = report.prioritized_risks.map((risk, index) => ({
    id: `risk-${index}`,
    type: (risk.status === "supported" ? "critical" : "abnormal") as "critical" | "abnormal",
    message: `${formatRiskFlag(risk.risk_flag)}: ${risk.explanation}`,
    timestamp: report.generated_at,
  }))

  report.excluded_outliers.forEach((outlier, index) => {
    alerts.push({
      id: `outlier-${index}`,
      type: "abnormal",
      message: `Excluded outlier: ${String(outlier.signal || outlier.test || "Unknown value")}`,
      timestamp: String(outlier.timestamp || report.generated_at),
    })
  })

  return alerts
}

export function toNotes(report: AnalyzeResponse): ClinicalNote[] {
  return [
    {
      id: "clinical-summary",
      content: report.clinical_summary,
      timestamp: report.generated_at,
    },
    {
      id: "doctor-handoff",
      content: report.doctor_handoff,
      timestamp: report.generated_at,
    },
    {
      id: "safety-disclaimer",
      content: report.safety_disclaimer,
      timestamp: report.generated_at,
    },
  ]
}

export function toGuidelines(report: AnalyzeResponse): Guideline[] {
  return report.prioritized_risks.map((risk, index) => ({
    id: `guideline-${index}`,
    title: formatRiskFlag(risk.risk_flag),
    description: `${risk.explanation} Threshold: ${risk.threshold}`,
    source: risk.guideline_source,
  }))
}

function toHistoricInsights(events: DiseaseTimelineEvent[]): HistoricInsight[] {
  return events.slice(0, 2).map((event, index) => ({
    id: `historic-${index}`,
    window: new Date(event.timestamp).toLocaleString(),
    signal: event.source === "lab_result" ? String(event.test || "Lab event") : "Clinical note update",
    impact: event.source === "lab_result" ? String(event.trend || "monitored") : "Narrative findings recorded",
  }))
}

function summarizeTimestampEvents(events: DiseaseTimelineEvent[]): string {
  const labTests = events
    .filter((event) => event.source === "lab_result" && event.test)
    .map((event) => `${event.test} ${event.value ?? ""}${event.unit ? ` ${event.unit}` : ""}`.trim())

  const noteCounts = events
    .filter((event) => event.source === "clinical_note")
    .reduce((count, event) => count + (Array.isArray(event.findings) ? event.findings.length : 0), 0)

  if (labTests.length && noteCounts) {
    return `${labTests.join(", ")} with ${noteCounts} note finding${noteCounts === 1 ? "" : "s"}`
  }
  if (labTests.length) {
    return labTests.join(", ")
  }
  if (noteCounts) {
    return `${noteCounts} note finding${noteCounts === 1 ? "" : "s"} recorded`
  }
  return "Monitoring update"
}

function computeEventSeverityScore(event: DiseaseTimelineEvent): number {
  if (event.source === "lab_result") {
    if (event.is_outlier) {
      return 95
    }
    if (event.aki_stage === "Stage 3") {
      return 92
    }
    if (event.aki_stage === "Stage 2") {
      return 84
    }
    if (event.aki_stage === "Stage 1") {
      return 74
    }
    if (event.above_normal || event.below_normal) {
      return 68
    }
    return 44
  }

  const findings = Array.isArray(event.findings) ? event.findings.length : 0
  return findings > 0 ? Math.min(50 + findings * 8, 78) : 42
}

function buildAggregatedTimeline(report: AnalyzeResponse): ProgressionPoint[] {
  const grouped = new Map<string, DiseaseTimelineEvent[]>()

  for (const event of report.disease_timeline) {
    const existing = grouped.get(event.timestamp) || []
    existing.push(event)
    grouped.set(event.timestamp, existing)
  }

  const riskBoost =
    report.prioritized_risks.filter((risk) => risk.status.toLowerCase() === "supported").length * 6
  const outlierPenalty = Number(report.data_quality.outliers_removed_count || 0) * 4

  const aggregated = Array.from(grouped.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([timestamp, events]) => {
      const baseScore = Math.max(...events.map(computeEventSeverityScore))
      const adjustedScore = Math.min(100, Math.max(35, baseScore + riskBoost - outlierPenalty))
      const hasRealtimeLab = events.some((event) => event.source === "lab_result")

      return {
        time: new Date(timestamp).toLocaleString([], {
          day: "2-digit",
          month: "short",
          hour: "2-digit",
          minute: "2-digit",
        }),
        source: hasRealtimeLab ? ("Real-time" as const) : ("Historic" as const),
        score: adjustedScore,
        summary: summarizeTimestampEvents(events),
      }
    })

  return aggregated.slice(-12)
}

function toRealtimeInsights(events: DiseaseTimelineEvent[]): RealTimeInsight[] {
  return events.slice(-2).map((event, index) => ({
    id: `realtime-${index}`,
    metric: event.source === "lab_result" ? String(event.test || "Lab event") : "Clinical note",
    value:
      event.source === "lab_result"
        ? `${event.value ?? ""} ${event.unit ?? ""}`.trim()
        : `${Array.isArray(event.findings) ? event.findings.length : 0} findings`,
    status: event.is_outlier
      ? "critical"
      : event.above_normal || event.below_normal
      ? "watch"
      : "normal",
    updatedAt: new Date(event.timestamp).toLocaleString(),
  }))
}

export function toDiseaseProgression(report: AnalyzeResponse): DiseaseProgression | undefined {
  if (!report.disease_timeline.length) {
    return undefined
  }

  const orderedEvents = [...report.disease_timeline].sort((a, b) => a.timestamp.localeCompare(b.timestamp))
  const timeline = buildAggregatedTimeline(report)

  const firstScore = timeline[0]?.score ?? 50
  const lastScore = timeline[timeline.length - 1]?.score ?? 50
  const trendDirection = lastScore > firstScore ? "worsening" : lastScore < firstScore ? "improving" : "stable"

  return {
    stage: formatRiskFlag(report.primary_concern),
    trendDirection,
    riskDeltaPercent: Math.abs(lastScore - firstScore),
    summary:
      report.disease_progression?.[report.disease_progression.length - 1]?.observation ||
      report.clinical_summary,
    next24hOutlook: report.doctor_handoff,
    historicInsights: report.disease_progression?.length
      ? report.disease_progression.slice(0, 2).map((item, index) => ({
          id: `historic-chief-${index}`,
          window: item.period,
          signal: item.observation,
          impact: "Chief-agent synthesized progression update",
        }))
      : toHistoricInsights(orderedEvents),
    realTimeInsights: toRealtimeInsights(orderedEvents),
    timeline,
  }
}

export function mergeDiseaseProgression(
  fallback: DiseaseProgression | undefined,
  live: DiseaseProgression | null
): DiseaseProgression | undefined {
  if (!live) {
    return fallback
  }

  const mergedHistoricInsights =
    live.historicInsights.length > 0
      ? live.historicInsights
      : fallback?.historicInsights || []

  const fallbackHistoricTimeline = (fallback?.timeline || []).filter(
    (point) => point.source === "Historic"
  )
  const liveHasHistoricTimeline = live.timeline.some((point) => point.source === "Historic")
  const mergedTimeline =
    liveHasHistoricTimeline || fallbackHistoricTimeline.length === 0
      ? live.timeline
      : [...fallbackHistoricTimeline, ...live.timeline].slice(-20)

  return {
    ...live,
    historicInsights: mergedHistoricInsights,
    timeline: mergedTimeline,
  }
}
