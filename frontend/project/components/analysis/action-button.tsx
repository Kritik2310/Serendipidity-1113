"use client"

import Link from "next/link"
import { cn } from "@/lib/utils"
import { FileText, CheckCircle } from "lucide-react"
import type { RiskLevel } from "@/lib/patient-data"

interface ActionButtonProps {
  patientId: string
  riskLevel: RiskLevel
}

export function ActionButton({ patientId, riskLevel }: ActionButtonProps) {
  const isHighRisk = riskLevel === "high"

  return (
    <div className="fixed bottom-8 left-64 right-0 flex justify-center pointer-events-none">
      <Link
        href={`/report/${patientId}`}
        className={cn(
          "pointer-events-auto flex items-center gap-3 rounded-xl px-8 py-4 text-lg font-semibold shadow-lg transition-all duration-300 hover:scale-105",
          isHighRisk
            ? "bg-risk-high text-white animate-pulse hover:animate-none hover:bg-risk-high/90"
            : "bg-risk-low text-white hover:bg-risk-low/90"
        )}
      >
        {isHighRisk ? (
          <>
            <FileText className="h-5 w-5" />
            View Critical Report
          </>
        ) : (
          <>
            <CheckCircle className="h-5 w-5" />
            View Stability Report
          </>
        )}
      </Link>
    </div>
  )
}
