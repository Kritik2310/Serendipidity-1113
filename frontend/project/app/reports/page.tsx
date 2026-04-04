import { DashboardLayout } from "@/components/dashboard-layout"
import { ReportsOverview } from "@/components/report/reports-overview"
import { fetchAllPatientReports } from "@/lib/api"

export default async function ReportsPage() {
  const bundles = await fetchAllPatientReports()

  return (
    <DashboardLayout>
      <ReportsOverview bundles={bundles} />
    </DashboardLayout>
  )
}
