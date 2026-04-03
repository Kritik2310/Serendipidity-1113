import { ArrowLeft, FlaskConical, ShieldCheck, TriangleAlert } from "lucide-react"
import Link from "next/link"
import { cn } from "@/lib/utils"

interface PatientHeaderProps {
  subjectId: number
  hadmId: number
  primaryConcern: string
  generatedAt: string
  ragAvailable: boolean
  sofaCoveragePct: number
}

export function PatientHeader({
  subjectId,
  hadmId,
  primaryConcern,
  generatedAt,
  ragAvailable,
  sofaCoveragePct,
}: PatientHeaderProps) {
  const isHighFocus =
    primaryConcern.toUpperCase().includes("SHOCK") ||
    primaryConcern.toUpperCase().includes("SEPSIS")

  return (
    <div className="border-b border-border bg-card px-8 py-6">
      <div className="mb-4 flex items-center gap-4">
        <Link
          href="/"
          className="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </Link>
      </div>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div
            className={cn(
              "flex h-14 w-14 items-center justify-center rounded-xl text-lg font-semibold",
              isHighFocus ? "bg-risk-high/10 text-risk-high" : "bg-risk-medium/10 text-risk-medium"
            )}
          >
            {String(subjectId).slice(-2)}
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground">{primaryConcern}</h1>
            <div className="mt-1 flex items-center gap-4 text-sm text-muted-foreground">
              <span className="font-mono">subject_id: {subjectId}</span>
              <span className="font-mono">hadm_id: {hadmId}</span>
              <span>Updated {new Date(generatedAt).toLocaleString()}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/50 px-4 py-2">
            <ShieldCheck className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium">{ragAvailable ? "RAG Active" : "RAG Offline"}</span>
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/50 px-4 py-2">
            <FlaskConical className="h-4 w-4 text-risk-medium" />
            <span className="text-sm font-medium">SOFA Coverage {sofaCoveragePct}%</span>
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/50 px-4 py-2">
            <TriangleAlert className="h-4 w-4 text-risk-high" />
            <span className="text-sm font-medium">Decision Support View</span>
          </div>
        </div>
      </div>
    </div>
  )
}
