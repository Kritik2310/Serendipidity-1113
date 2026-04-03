"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { cn } from "@/lib/utils"
import { FileText, CheckCircle, LoaderCircle } from "lucide-react"
import { analyzePatient, buildAnalysisId } from "@/lib/api"
import type { RiskLevel } from "@/lib/patient-data"

interface ActionButtonProps {
  subjectId: number
  hadmId: number
  riskLevel: RiskLevel
}

export function ActionButton({ subjectId, hadmId, riskLevel }: ActionButtonProps) {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const isHighRisk = riskLevel === "high"

  async function handleAnalyze() {
    try {
      setLoading(true)
      await analyzePatient(subjectId, hadmId)
      router.push(`/report/${buildAnalysisId(subjectId, hadmId)}`)
      router.refresh()
    } catch (error) {
      window.alert(error instanceof Error ? error.message : "Failed to generate report")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="pointer-events-none fixed bottom-8 left-64 right-0 flex justify-center">
      <button
        type="button"
        onClick={handleAnalyze}
        disabled={loading}
        className={cn(
          "pointer-events-auto flex items-center gap-3 rounded-xl px-8 py-4 text-lg font-semibold shadow-lg transition-all duration-300 hover:scale-105",
          loading && "cursor-not-allowed opacity-80 hover:scale-100",
          isHighRisk
            ? "bg-risk-high text-white animate-pulse hover:animate-none hover:bg-risk-high/90"
            : "bg-risk-low text-white hover:bg-risk-low/90"
        )}
      >
        {loading && <LoaderCircle className="h-5 w-5 animate-spin" />}
        {isHighRisk ? (
          <>
            <FileText className="h-5 w-5" />
            Generate Critical Report
          </>
        ) : (
          <>
            <CheckCircle className="h-5 w-5" />
            Generate Stability Report
          </>
        )}
      </button>
    </div>
  )
}
