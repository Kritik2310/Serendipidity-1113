import { AlertTriangle, CheckCircle, AlertCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import type { PrioritizedRisk } from "@/lib/api"
import type { RiskLevel } from "@/lib/patient-data"

interface RiskPanelProps {
  primaryConcern: string
  riskLevel: RiskLevel
  prioritizedRisks: PrioritizedRisk[]
}

export function RiskPanel({ primaryConcern, riskLevel, prioritizedRisks }: RiskPanelProps) {
  const isHighRisk = riskLevel === "high"
  const isMediumRisk = riskLevel === "medium"
  const supportedCount = prioritizedRisks.filter((risk) => risk.status === "supported").length

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-xl border p-6",
        isHighRisk
          ? "border-risk-high/30 bg-risk-high/5"
          : isMediumRisk
          ? "border-risk-medium/30 bg-risk-medium/5"
          : "border-risk-low/30 bg-risk-low/5"
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <div
            className={cn(
              "flex h-14 w-14 items-center justify-center rounded-xl",
              isHighRisk
                ? "bg-risk-high/20"
                : isMediumRisk
                ? "bg-risk-medium/20"
                : "bg-risk-low/20"
            )}
          >
            {isHighRisk ? (
              <AlertTriangle className="h-7 w-7 text-risk-high" />
            ) : isMediumRisk ? (
              <AlertCircle className="h-7 w-7 text-risk-medium" />
            ) : (
              <CheckCircle className="h-7 w-7 text-risk-low" />
            )}
          </div>
          <div>
            <div className="flex items-center gap-3">
              <span
                className={cn(
                  "text-2xl font-bold uppercase tracking-wide",
                  isHighRisk
                    ? "text-risk-high"
                    : isMediumRisk
                    ? "text-risk-medium"
                    : "text-risk-low"
                )}
              >
                {isHighRisk ? "High Risk" : isMediumRisk ? "Medium Risk" : "Stable"}
              </span>
              {isHighRisk && (
                <span className="relative flex h-3 w-3">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-risk-high opacity-75"></span>
                  <span className="relative inline-flex h-3 w-3 rounded-full bg-risk-high"></span>
                </span>
              )}
            </div>
            <p className="mt-1 text-lg font-medium text-foreground">{primaryConcern}</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-sm text-muted-foreground">Supported Risks</p>
          <p
            className={cn(
              "text-3xl font-bold",
              isHighRisk
                ? "text-risk-high"
                : isMediumRisk
                ? "text-risk-medium"
                : "text-risk-low"
            )}
          >
            {supportedCount}/{prioritizedRisks.length}
          </p>
        </div>
      </div>
    </div>
  )
}
