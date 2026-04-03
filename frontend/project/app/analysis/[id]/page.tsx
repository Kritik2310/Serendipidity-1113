import { notFound } from "next/navigation"
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
  getPatientById,
  getLabResultsForPatient,
  getAlertsForPatient,
  getNotesForPatient,
  getGuidelinesForPatient,
  getDiseaseProgressionForPatient,
  patients,
} from "@/lib/patient-data"

interface AnalysisPageProps {
  params: Promise<{ id: string }>
}

export function generateStaticParams() {
  return patients.map((patient) => ({ id: patient.id }))
}

export default async function AnalysisPage({ params }: AnalysisPageProps) {
  const { id } = await params
  const patient = getPatientById(id)

  if (!patient) {
    notFound()
  }

  const labs = getLabResultsForPatient(id)
  const alerts = getAlertsForPatient(id)
  const notes = getNotesForPatient(id)
  const guidelines = getGuidelinesForPatient(id)
  const progression = getDiseaseProgressionForPatient(id)

  return (
    <DashboardLayout>
      <PatientHeader patient={patient} />
      <div className="p-8 pb-32">
        {/* Risk Panel - Most Important */}
        <div className="mb-6">
          <RiskPanel patient={patient} />
        </div>

        {progression && (
          <div className="mb-6">
            <DiseaseProgressionPanel progression={progression} />
          </div>
        )}

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column: Lab Trends */}
          <LabTrends labs={labs} />

          {/* Right Column: Alerts */}
          <AlertsPanel alerts={alerts} />
        </div>

        {/* Bottom Row */}
        <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Notes */}
          <NotesPanel notes={notes} />

          {/* Guidelines */}
          <GuidelinesPanel guidelines={guidelines} />
        </div>
      </div>

      {/* Action Button */}
      <ActionButton patientId={id} riskLevel={patient.riskLevel} />
    </DashboardLayout>
  )
}
