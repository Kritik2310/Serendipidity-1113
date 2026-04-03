"use client"

import { useEffect, useMemo, useState } from "react"
import { DashboardLayout } from "@/components/dashboard-layout"
import { ArrowLeft, Printer, Download, AlertTriangle, CheckCircle } from "lucide-react"
import Link from "next/link"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  deriveRiskLevel,
  fetchReport,
  formatRiskFlag,
  streamPatient,
  toAlerts,
  toDiseaseProgression,
  toGuidelines,
  toLabResults,
  toNotes,
  type AnalyzeResponse,
} from "@/lib/api"

interface LiveReportViewProps {
  initialReport: AnalyzeResponse
  analysisId: string
}

export function LiveReportView({ initialReport, analysisId }: LiveReportViewProps) {
  const [report, setReport] = useState(initialReport)

  useEffect(() => {
    const source = streamPatient(report.subject_id, report.hadm_id, async () => {
      try {
        const freshReport = await fetchReport(report.subject_id, report.hadm_id)
        setReport(freshReport)
      } catch {
        // Keep the last successful report visible if refresh fails.
      }
    })

    return () => {
      source.close()
    }
  }, [report.subject_id, report.hadm_id])

  const labs = useMemo(() => toLabResults(report), [report])
  const alerts = useMemo(() => toAlerts(report), [report])
  const notes = useMemo(() => toNotes(report), [report])
  const guidelines = useMemo(() => toGuidelines(report), [report])
  const progression = useMemo(() => toDiseaseProgression(report), [report])
  const riskLevel = deriveRiskLevel(report)
  const isHighRisk = riskLevel === "high"
  const displayAlerts = useMemo(
    () =>
      [...alerts].sort((a, b) => {
        if (a.type === b.type) return 0
        return a.type === "critical" ? -1 : 1
      }),
    [alerts]
  )

  return (
    <DashboardLayout>
      <div className="min-h-screen bg-background">
        <div className="border-b border-border bg-card px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                href={`/analysis/${analysisId}`}
                className="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to Analysis
              </Link>
            </div>
            <div className="flex items-center gap-3">
              <Button variant="outline" size="sm">
                <Printer className="mr-2 h-4 w-4" />
                Print
              </Button>
              <Button variant="outline" size="sm">
                <Download className="mr-2 h-4 w-4" />
                Export PDF
              </Button>
            </div>
          </div>
        </div>

        <div className="mx-auto max-w-4xl px-8 py-8">
          <div className="rounded-xl border border-border bg-card shadow-sm">
            <div className="border-b border-border p-8">
              <div className="flex items-start justify-between">
                <div>
                  <h1 className="text-3xl font-bold text-foreground">Clinical Risk Report</h1>
                  <p className="mt-2 text-muted-foreground">
                    Generated on{" "}
                    {new Date(report.generated_at).toLocaleDateString("en-US", {
                      weekday: "long",
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                </div>
                <div
                  className={cn(
                    "flex items-center gap-2 rounded-lg px-4 py-2",
                    isHighRisk ? "bg-risk-high/10 text-risk-high" : "bg-risk-low/10 text-risk-low"
                  )}
                >
                  {isHighRisk ? <AlertTriangle className="h-5 w-5" /> : <CheckCircle className="h-5 w-5" />}
                  <span className="font-semibold uppercase">{isHighRisk ? "Critical" : "Stable"}</span>
                </div>
              </div>
            </div>

            <div className="border-b border-border p-8">
              <h2 className="mb-4 text-xl font-semibold text-foreground">1. Case Overview</h2>
              <div className="grid grid-cols-2 gap-6">
                <div className="flex flex-col gap-2">
                  <div className="flex justify-between border-b border-border/50 py-2">
                    <span className="text-muted-foreground">Subject ID</span>
                    <span className="font-mono text-foreground">{report.subject_id}</span>
                  </div>
                  <div className="flex justify-between border-b border-border/50 py-2">
                    <span className="text-muted-foreground">Admission ID</span>
                    <span className="font-mono text-foreground">{report.hadm_id}</span>
                  </div>
                  <div className="flex justify-between py-2">
                    <span className="text-muted-foreground">Pipeline Status</span>
                    <span className="capitalize text-foreground">{report.status}</span>
                  </div>
                </div>
                <div className="flex flex-col gap-2">
                  <div className="flex justify-between border-b border-border/50 py-2">
                    <span className="text-muted-foreground">Primary Concern</span>
                    <span className="font-medium text-foreground">{report.primary_concern}</span>
                  </div>
                  <div className="flex justify-between border-b border-border/50 py-2">
                    <span className="text-muted-foreground">SOFA Coverage</span>
                    <span className="text-foreground">{report.data_quality.sofa_coverage_pct}%</span>
                  </div>
                  <div className="flex justify-between py-2">
                    <span className="text-muted-foreground">Outliers Removed</span>
                    <span className="text-foreground">{report.data_quality.outliers_removed_count || 0}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="border-b border-border p-8">
              <h2 className="mb-4 text-xl font-semibold text-foreground">2. Clinical Summary</h2>
              <div className="rounded-lg border border-border bg-muted/30 p-5">
                <p className="leading-7 text-foreground">{report.clinical_summary}</p>
                <p className="mt-4 text-sm text-muted-foreground">{report.doctor_handoff}</p>
              </div>
              {progression && (
                <div className="mt-4 rounded-lg border border-border bg-background p-5">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="text-base font-semibold text-foreground">Disease Progression</h3>
                    <span
                      className={cn(
                        "rounded-full px-3 py-1 text-xs font-semibold uppercase",
                        progression.trendDirection === "worsening"
                          ? "bg-risk-high/10 text-risk-high"
                          : progression.trendDirection === "improving"
                          ? "bg-risk-low/10 text-risk-low"
                          : "bg-muted text-muted-foreground"
                      )}
                    >
                      {progression.trendDirection}
                    </span>
                  </div>
                  <p className="mt-3 text-sm text-foreground">{progression.summary}</p>
                  <p className="mt-2 text-sm text-muted-foreground">{progression.next24hOutlook}</p>
                </div>
              )}
            </div>

            <div className="border-b border-border p-8">
              <h2 className="mb-4 text-xl font-semibold text-foreground">3. Key Findings</h2>
              {displayAlerts.length > 0 ? (
                <div className="flex flex-col gap-3">
                  {displayAlerts.map((alert, index) => (
                    <div
                      key={alert.id}
                      className={cn(
                        "flex items-start gap-3 rounded-lg p-4",
                        alert.type === "critical"
                          ? "border border-risk-high/20 bg-risk-high/5"
                          : "border border-yellow-500/20 bg-yellow-500/5"
                      )}
                    >
                      <span
                        className={cn(
                          "flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold text-white",
                          alert.type === "critical" ? "bg-risk-high" : "bg-yellow-500"
                        )}
                      >
                        {index + 1}
                      </span>
                      <div>
                        <p className="font-medium text-foreground">{alert.message}</p>
                        <p className="mt-1 text-sm text-muted-foreground">{alert.timestamp}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-lg border border-risk-low/20 bg-risk-low/5 p-4">
                  <p className="text-foreground">No active findings were returned in this report.</p>
                </div>
              )}
            </div>

            <div className="border-b border-border p-8">
              <h2 className="mb-4 text-xl font-semibold text-foreground">4. Supporting Evidence</h2>
              <div className="mb-6">
                <h3 className="mb-3 text-lg font-medium text-foreground">Laboratory Timeline</h3>
                <div className="overflow-hidden rounded-lg border border-border">
                  <table className="w-full">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Test</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Value</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Range</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {labs.map((lab) => (
                        <tr key={lab.name} className="border-t border-border">
                          <td className="px-4 py-3 text-sm font-medium text-foreground">{lab.name}</td>
                          <td className="px-4 py-3 text-sm text-foreground">
                            {lab.value} {lab.unit}
                          </td>
                          <td className="px-4 py-3 text-sm text-muted-foreground">{lab.normalRange}</td>
                          <td className="px-4 py-3 text-sm capitalize text-foreground">{lab.status}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div>
                <h3 className="mb-3 text-lg font-medium text-foreground">Clinical Notes</h3>
                <ul className="flex flex-col gap-2">
                  {notes.map((note) => (
                    <li key={note.id} className="flex items-start gap-3">
                      <div className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                      <div>
                        <span className="text-sm text-foreground">{note.content}</span>
                        <span className="ml-2 text-xs text-muted-foreground">({note.timestamp})</span>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="border-b border-border p-8">
              <h2 className="mb-4 text-xl font-semibold text-foreground">5. Guideline Justification</h2>
              <div className="flex flex-col gap-4">
                {guidelines.map((guideline) => (
                  <div key={guideline.id} className="rounded-lg border border-border bg-muted/30 p-4">
                    <h4 className="font-semibold text-foreground">{guideline.title}</h4>
                    <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{guideline.description}</p>
                    <p className="mt-2 text-xs font-medium text-primary">Reference: {guideline.source}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="border-b border-border p-8">
              <h2 className="mb-4 text-xl font-semibold text-foreground">6. Prioritized Risks</h2>
              <div className="flex flex-col gap-4">
                {report.prioritized_risks.map((risk) => (
                  <div key={risk.risk_flag} className="rounded-lg border border-border bg-muted/30 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <h4 className="font-semibold text-foreground">{formatRiskFlag(risk.risk_flag)}</h4>
                      <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold uppercase text-primary">
                        {risk.status}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground">{risk.explanation}</p>
                    <p className="mt-2 text-xs font-medium text-primary">{risk.threshold}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="p-8">
              <h2 className="mb-4 text-xl font-semibold text-foreground">7. Recommended Actions</h2>
              <div className="flex flex-col gap-3">
                {report.recommended_actions.map((action, index) => (
                  <div key={action} className="flex items-start gap-3 rounded-lg border border-primary/20 bg-primary/5 p-4">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                      {index + 1}
                    </span>
                    <p className="text-sm text-foreground">{action}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="border-t border-border bg-muted/30 px-8 py-4">
              <p className="text-center text-xs text-muted-foreground">{report.safety_disclaimer}</p>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
