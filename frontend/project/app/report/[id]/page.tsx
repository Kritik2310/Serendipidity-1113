import { notFound } from "next/navigation"
import { DashboardLayout } from "@/components/dashboard-layout"
import { ArrowLeft, Printer, Download, AlertTriangle, CheckCircle } from "lucide-react"
import Link from "next/link"
import { cn } from "@/lib/utils"
import {
  getPatientById,
  getLabResultsForPatient,
  getAlertsForPatient,
  getNotesForPatient,
  getGuidelinesForPatient,
  patients,
} from "@/lib/patient-data"
import { Button } from "@/components/ui/button"

interface ReportPageProps {
  params: Promise<{ id: string }>
}

export function generateStaticParams() {
  return patients.map((patient) => ({ id: patient.id }))
}

export default async function ReportPage({ params }: ReportPageProps) {
  const { id } = await params
  const patient = getPatientById(id)

  if (!patient) {
    notFound()
  }

  const labs = getLabResultsForPatient(id)
  const alerts = getAlertsForPatient(id)
  const notes = getNotesForPatient(id)
  const guidelines = getGuidelinesForPatient(id)

  const isHighRisk = patient.riskLevel === "high"
  const criticalAlerts = alerts.filter((a) => a.type === "critical")

  return (
    <DashboardLayout>
      <div className="min-h-screen bg-background">
        {/* Header */}
        <div className="border-b border-border bg-card px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                href={`/analysis/${id}`}
                className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to Analysis
              </Link>
            </div>
            <div className="flex items-center gap-3">
              <Button variant="outline" size="sm">
                <Printer className="h-4 w-4 mr-2" />
                Print
              </Button>
              <Button variant="outline" size="sm">
                <Download className="h-4 w-4 mr-2" />
                Export PDF
              </Button>
            </div>
          </div>
        </div>

        {/* Report Content */}
        <div className="mx-auto max-w-4xl px-8 py-8">
          <div className="rounded-xl border border-border bg-card shadow-sm">
            {/* Report Header */}
            <div className="border-b border-border p-8">
              <div className="flex items-start justify-between">
                <div>
                  <h1 className="text-3xl font-bold text-foreground">Clinical Risk Report</h1>
                  <p className="mt-2 text-muted-foreground">
                    Generated on {new Date().toLocaleDateString("en-US", {
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
                    isHighRisk
                      ? "bg-risk-high/10 text-risk-high"
                      : "bg-risk-low/10 text-risk-low"
                  )}
                >
                  {isHighRisk ? (
                    <AlertTriangle className="h-5 w-5" />
                  ) : (
                    <CheckCircle className="h-5 w-5" />
                  )}
                  <span className="font-semibold uppercase">
                    {isHighRisk ? "Critical" : "Stable"}
                  </span>
                </div>
              </div>
            </div>

            {/* Section 1: Patient Overview */}
            <div className="border-b border-border p-8">
              <h2 className="text-xl font-semibold text-foreground mb-4">1. Patient Overview</h2>
              <div className="grid grid-cols-2 gap-6">
                <div className="flex flex-col gap-2">
                  <div className="flex justify-between py-2 border-b border-border/50">
                    <span className="text-muted-foreground">Patient Name</span>
                    <span className="font-medium text-foreground">{patient.name}</span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-border/50">
                    <span className="text-muted-foreground">Patient ID</span>
                    <span className="font-mono text-foreground">{patient.id}</span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-border/50">
                    <span className="text-muted-foreground">Age</span>
                    <span className="text-foreground">{patient.age} years</span>
                  </div>
                  <div className="flex justify-between py-2">
                    <span className="text-muted-foreground">Gender</span>
                    <span className="text-foreground">{patient.gender}</span>
                  </div>
                </div>
                <div className="flex flex-col gap-2">
                  <div className="flex justify-between py-2 border-b border-border/50">
                    <span className="text-muted-foreground">Bed Number</span>
                    <span className="font-mono text-foreground">{patient.bedNumber}</span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-border/50">
                    <span className="text-muted-foreground">Admission Date</span>
                    <span className="text-foreground">{patient.admissionDate}</span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-border/50">
                    <span className="text-muted-foreground">Status</span>
                    <span className="text-foreground">{patient.status}</span>
                  </div>
                  <div className="flex justify-between py-2">
                    <span className="text-muted-foreground">Primary Condition</span>
                    <span className="font-medium text-foreground">{patient.condition}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Section 2: Risk Level */}
            <div className="border-b border-border p-8">
              <h2 className="text-xl font-semibold text-foreground mb-4">2. Risk Level Assessment</h2>
              <div
                className={cn(
                  "rounded-xl p-6",
                  isHighRisk ? "bg-risk-high/5 border border-risk-high/20" : "bg-risk-low/5 border border-risk-low/20"
                )}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div
                      className={cn(
                        "flex h-12 w-12 items-center justify-center rounded-lg",
                        isHighRisk ? "bg-risk-high/20" : "bg-risk-low/20"
                      )}
                    >
                      {isHighRisk ? (
                        <AlertTriangle className="h-6 w-6 text-risk-high" />
                      ) : (
                        <CheckCircle className="h-6 w-6 text-risk-low" />
                      )}
                    </div>
                    <div>
                      <p
                        className={cn(
                          "text-2xl font-bold",
                          isHighRisk ? "text-risk-high" : "text-risk-low"
                        )}
                      >
                        {isHighRisk ? "HIGH RISK" : "STABLE"}
                      </p>
                      <p className="text-muted-foreground">{patient.condition}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-muted-foreground">AI Confidence</p>
                    <p
                      className={cn(
                        "text-3xl font-bold",
                        isHighRisk ? "text-risk-high" : "text-risk-low"
                      )}
                    >
                      {isHighRisk ? "89%" : "95%"}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Section 3: Key Findings */}
            <div className="border-b border-border p-8">
              <h2 className="text-xl font-semibold text-foreground mb-4">3. Key Findings</h2>
              {criticalAlerts.length > 0 ? (
                <div className="flex flex-col gap-3">
                  {criticalAlerts.map((alert, index) => (
                    <div
                      key={alert.id}
                      className="flex items-start gap-3 rounded-lg border border-risk-high/20 bg-risk-high/5 p-4"
                    >
                      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-risk-high text-xs font-bold text-white">
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
                  <p className="text-foreground">No critical findings. Patient vitals are within normal range.</p>
                </div>
              )}
            </div>

            {/* Section 4: Supporting Evidence */}
            <div className="border-b border-border p-8">
              <h2 className="text-xl font-semibold text-foreground mb-4">4. Supporting Evidence</h2>
              
              {/* Lab Results */}
              <div className="mb-6">
                <h3 className="text-lg font-medium text-foreground mb-3">Laboratory Results</h3>
                <div className="overflow-hidden rounded-lg border border-border">
                  <table className="w-full">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Test</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Value</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Normal Range</th>
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
                          <td className="px-4 py-3">
                            <span
                              className={cn(
                                "rounded-full px-2 py-1 text-xs font-medium",
                                lab.status === "critical"
                                  ? "bg-risk-high/10 text-risk-high"
                                  : lab.status === "abnormal"
                                  ? "bg-risk-medium/10 text-risk-medium"
                                  : "bg-risk-low/10 text-risk-low"
                              )}
                            >
                              {lab.status.charAt(0).toUpperCase() + lab.status.slice(1)}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Clinical Notes */}
              <div>
                <h3 className="text-lg font-medium text-foreground mb-3">Clinical Notes</h3>
                <ul className="flex flex-col gap-2">
                  {notes.map((note) => (
                    <li key={note.id} className="flex items-start gap-3">
                      <div className="mt-2 h-1.5 w-1.5 rounded-full bg-primary shrink-0" />
                      <div>
                        <span className="text-sm text-foreground">{note.content}</span>
                        <span className="ml-2 text-xs text-muted-foreground">({note.timestamp})</span>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Section 5: Guideline Justification */}
            <div className="border-b border-border p-8">
              <h2 className="text-xl font-semibold text-foreground mb-4">5. Guideline Justification</h2>
              <div className="flex flex-col gap-4">
                {guidelines.map((guideline) => (
                  <div key={guideline.id} className="rounded-lg border border-border bg-muted/30 p-4">
                    <h4 className="font-semibold text-foreground">{guideline.title}</h4>
                    <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                      {guideline.description}
                    </p>
                    <p className="mt-2 text-xs font-medium text-primary">
                      Reference: {guideline.source}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Section 6: Suggested Actions */}
            <div className="p-8">
              <h2 className="text-xl font-semibold text-foreground mb-4">6. Suggested Actions</h2>
              {isHighRisk ? (
                <div className="flex flex-col gap-3">
                  <div className="flex items-start gap-3 rounded-lg border border-primary/20 bg-primary/5 p-4">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                      1
                    </span>
                    <div>
                      <p className="font-medium text-foreground">Immediate Assessment</p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        Review patient vitals and perform bedside assessment within 15 minutes
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 rounded-lg border border-primary/20 bg-primary/5 p-4">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                      2
                    </span>
                    <div>
                      <p className="font-medium text-foreground">Laboratory Re-evaluation</p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        Order stat repeat labs including comprehensive metabolic panel and lactate
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 rounded-lg border border-primary/20 bg-primary/5 p-4">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                      3
                    </span>
                    <div>
                      <p className="font-medium text-foreground">Treatment Protocol</p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        Consider initiating sepsis bundle protocol per clinical guidelines
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 rounded-lg border border-primary/20 bg-primary/5 p-4">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                      4
                    </span>
                    <div>
                      <p className="font-medium text-foreground">Specialist Consultation</p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        Consider nephrology and/or infectious disease consultation
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col gap-3">
                  <div className="flex items-start gap-3 rounded-lg border border-risk-low/20 bg-risk-low/5 p-4">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-risk-low text-xs font-bold text-white">
                      1
                    </span>
                    <div>
                      <p className="font-medium text-foreground">Continue Monitoring</p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        Maintain current monitoring protocol with vitals every 4 hours
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 rounded-lg border border-risk-low/20 bg-risk-low/5 p-4">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-risk-low text-xs font-bold text-white">
                      2
                    </span>
                    <div>
                      <p className="font-medium text-foreground">Routine Labs</p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        Continue scheduled laboratory monitoring as per protocol
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="border-t border-border bg-muted/30 px-8 py-4">
              <p className="text-xs text-muted-foreground text-center">
                This report was generated by AI-Powered ICU Assistant. All clinical decisions should be made by qualified healthcare professionals.
              </p>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
