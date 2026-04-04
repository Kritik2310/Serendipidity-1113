import { DashboardLayout } from "@/components/dashboard-layout"
import { AnalysisOverview } from "@/components/analysis/analysis-overview"
import { fetchPatientSummaries } from "@/lib/api"

export default async function AnalysisOverviewPage() {
  const patients = await fetchPatientSummaries()

  return (
    <DashboardLayout>
      <AnalysisOverview patients={patients} />
    </DashboardLayout>
  )
}
