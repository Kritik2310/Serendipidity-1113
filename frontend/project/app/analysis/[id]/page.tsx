import { notFound } from "next/navigation"
import { fetchReport, parseAnalysisId } from "@/lib/api"
import { LiveAnalysisView } from "@/components/analysis/live-analysis-view"

interface AnalysisPageProps {
  params: Promise<{ id: string }>
}

export default async function AnalysisPage({ params }: AnalysisPageProps) {
  const { id } = await params

  try {
    const { subjectId, hadmId } = parseAnalysisId(id)
    const report = await fetchReport(subjectId, hadmId)
    return <LiveAnalysisView initialReport={report} />
  } catch {
    notFound()
  }
}
