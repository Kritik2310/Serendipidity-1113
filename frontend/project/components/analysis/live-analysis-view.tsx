"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { DashboardLayout } from "@/components/dashboard-layout"
import { PatientHeader } from "@/components/analysis/patient-header"
import { RiskPanel } from "@/components/analysis/risk-panel"
import { LabTrends } from "@/components/analysis/lab-trends"
import { AlertsPanel } from "@/components/analysis/alerts-panel"
import { NotesPanel } from "@/components/analysis/notes-panel"
import { GuidelinesPanel } from "@/components/analysis/guidelines-panel"
import { DiseaseProgressionPanel } from "@/components/analysis/disease-progression-panel"
import { ActionButton } from "@/components/analysis/action-button"
import {
  deriveRiskLevel,
  fetchProgression,
  fetchReport,
  mergeDiseaseProgression,
  streamPatient,
  toAlerts,
  toDiseaseProgression,
  toGuidelines,
  toLabResults,
  toNotes,
  type AnalyzeResponse,
} from "@/lib/api"
import type { DiseaseProgression } from "@/lib/patient-data"

interface LiveAnalysisViewProps {
  initialReport: AnalyzeResponse
}

export function LiveAnalysisView({ initialReport }: LiveAnalysisViewProps) {
  const [report, setReport]           = useState<AnalyzeResponse>(initialReport)
  const [liveProgression, setLiveProgression] = useState<DiseaseProgression | null>(null)
  const progressionIntervalRef        = useRef<ReturnType<typeof setInterval> | null>(null)

  // ── SSE: refresh report whenever backend saves a new chief report ──────────
  useEffect(() => {
    const source = streamPatient(
      report.subject_id,
      report.hadm_id,
      async () => {
        try {
          const freshReport = await fetchReport(report.subject_id, report.hadm_id)
          setReport(freshReport)
        } catch {
          // Keep showing last successful report on failure
        }
      }
    )
    return () => source.close()
  }, [report.subject_id, report.hadm_id])

  // ── Poll /progression every 35s for live simulation data ──────────────────
  useEffect(() => {
  const loadProgression = async () => {
    try {
      const data = await fetchProgression(report.subject_id, report.hadm_id)
      if (data) {
        setLiveProgression(data)
      }
    } catch {
      // silently keep previous state
    }
  }

  // Fire immediately on mount — don't wait 35s for first load
  loadProgression()

  // Poll every 10s — fast enough to catch updates within one simulator round
  const interval = setInterval(loadProgression, 10_000)

  return () => clearInterval(interval)
}, [report.subject_id, report.hadm_id])

  const riskLevel  = deriveRiskLevel(report)
  const labs       = useMemo(() => toLabResults(report), [report])
  const alerts     = useMemo(() => toAlerts(report), [report])
  const notes      = useMemo(() => toNotes(report), [report])
  const guidelines = useMemo(() => toGuidelines(report), [report])

  // Prefer live progression from simulator — fall back to computed from report
  const fallbackProgression = useMemo(() => toDiseaseProgression(report), [report])
  const progression: DiseaseProgression | undefined = useMemo(
    () => mergeDiseaseProgression(fallbackProgression, liveProgression),
    [fallbackProgression, liveProgression]
  )

  return (
    <DashboardLayout>
      <PatientHeader
        subjectId={report.subject_id}
        hadmId={report.hadm_id}
        primaryConcern={report.primary_concern}
        generatedAt={report.generated_at}
        ragAvailable={report.data_quality.rag_available}
        sofaCoveragePct={Number(report.data_quality.sofa_coverage_pct || 0)}
      />

      <div className="p-8 pb-32">
        <div className="mb-6">
          <RiskPanel
            primaryConcern={report.primary_concern}
            riskLevel={riskLevel}
            prioritizedRisks={report.prioritized_risks}
          />
        </div>

        {progression && (
          <div className="mb-6">
            <DiseaseProgressionPanel progression={progression} />
          </div>
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <LabTrends labs={labs} />
          <AlertsPanel alerts={alerts} />
        </div>

        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <NotesPanel notes={notes} />
          <GuidelinesPanel guidelines={guidelines} />
        </div>
      </div>

      <ActionButton
        subjectId={report.subject_id}
        hadmId={report.hadm_id}
        riskLevel={riskLevel}
      />
    </DashboardLayout>
  )
}
