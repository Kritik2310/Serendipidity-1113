import { notFound } from "next/navigation"
import { fetchReport, parseAnalysisId } from "@/lib/api"
import { LiveReportView } from "@/components/report/live-report-view"

interface ReportPageProps {
  params: Promise<{ id: string }>
}

export default async function ReportPage({ params }: ReportPageProps) {
  const { id } = await params

  try {
    const { subjectId, hadmId } = parseAnalysisId(id)
    const report = await fetchReport(subjectId, hadmId)
    return <LiveReportView initialReport={report} analysisId={id} />
  } catch {
    notFound()
  }
}
