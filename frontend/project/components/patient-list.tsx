"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { cn } from "@/lib/utils"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { ChevronRight } from "lucide-react"
import { fetchPatientSummaries, type PatientSummary } from "@/lib/api"
import type { RiskLevel } from "@/lib/patient-data"

function getRiskBadgeStyles(risk: RiskLevel) {
  switch (risk) {
    case "high":
      return "border-risk-high/[0.2] bg-risk-high/[0.08] text-risk-high shadow-[0_0_14px_rgba(220,38,38,0.08)]"
    case "medium":
      return "border-risk-medium/[0.2] bg-risk-medium/[0.08] text-risk-medium shadow-[0_0_14px_rgba(217,119,6,0.08)]"
    case "low":
      return "border-risk-low/[0.18] bg-risk-low/[0.07] text-risk-low"
  }
}

function getRiskLabel(risk: RiskLevel) {
  switch (risk) {
    case "high":
      return "High Risk"
    case "medium":
      return "Medium"
    case "low":
      return "Stable"
  }
}

function getRiskDot(risk: RiskLevel) {
  switch (risk) {
    case "high":
      return "bg-risk-high"
    case "medium":
      return "bg-risk-medium"
    case "low":
      return "bg-risk-low"
  }
}

export function PatientList() {
  const router = useRouter()
  const [patients, setPatients] = useState<PatientSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    async function loadPatients() {
      try {
        const summaries = await fetchPatientSummaries()
        if (active) {
          setPatients(summaries)
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to load patients")
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    void loadPatients()
    const intervalId = window.setInterval(() => {
      void loadPatients()
    }, 10000)

    return () => {
      active = false
      window.clearInterval(intervalId)
    }
  }, [])

  return (
    <section className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-semibold text-foreground">Patient Overview</h2>
          <p className="mt-1 text-base text-muted-foreground">
            {loading ? "Loading analyzed cases..." : `${patients.length} analyzed ICU cases`}
          </p>
        </div>
        <div className="flex items-center gap-5 text-base">
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-[3px] bg-risk-high shadow-[0_0_10px_rgba(220,38,38,0.28)]" />
            <span className="font-medium text-muted-foreground">High Risk</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-[3px] bg-risk-medium shadow-[0_0_10px_rgba(217,119,6,0.22)]" />
            <span className="font-medium text-muted-foreground">Medium</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-[3px] bg-risk-low" />
            <span className="font-medium text-muted-foreground">Stable</span>
          </div>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-[110px] py-4 text-sm font-semibold uppercase tracking-wide text-foreground">Subject</TableHead>
              <TableHead className="w-[120px] py-4 text-sm font-semibold uppercase tracking-wide text-foreground">Admission</TableHead>
              <TableHead className="w-[120px] py-4 text-sm font-semibold uppercase tracking-wide text-foreground">Status</TableHead>
              <TableHead className="py-4 text-sm font-semibold uppercase tracking-wide text-foreground">Primary Concern</TableHead>
              <TableHead className="py-4 text-sm font-semibold uppercase tracking-wide text-foreground">Last Updated</TableHead>
              <TableHead className="py-4 text-sm font-semibold uppercase tracking-wide text-foreground">Risk Level</TableHead>
              <TableHead className="w-[50px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {error && (
              <TableRow>
                <TableCell colSpan={7} className="py-10 text-center text-sm text-risk-high">
                  {error}
                </TableCell>
              </TableRow>
            )}
            {!loading && !error && patients.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="py-10 text-center text-sm text-muted-foreground">
                  No analyzed patients found yet.
                </TableCell>
              </TableRow>
            )}
            {patients.map((patient) => (
              <TableRow
                key={patient.analysisId}
                className={cn(
                  "group cursor-pointer transition-colors hover:bg-muted/50",
                  patient.riskLevel === "high" && "bg-risk-high/[0.04] hover:bg-risk-high/[0.08]",
                  patient.riskLevel === "medium" && "bg-risk-medium/[0.03] hover:bg-risk-medium/[0.06]"
                )}
                onClick={() => router.push(`/analysis/${patient.analysisId}`)}
              >
                <TableCell className="py-5 font-mono text-base text-muted-foreground">
                  {patient.subjectId}
                </TableCell>
                <TableCell className="font-mono text-base text-foreground">
                  {patient.hadmId}
                </TableCell>
                <TableCell className="text-base capitalize text-muted-foreground">
                  {patient.status}
                </TableCell>
                <TableCell>
                  <span className="text-base font-medium text-foreground">{patient.primaryConcern}</span>
                </TableCell>
                <TableCell>
                  <span className="text-sm text-muted-foreground">
                    {new Date(patient.lastAnalyzed).toLocaleString()}
                  </span>
                </TableCell>
                <TableCell>
                  <Badge
                    variant="outline"
                    className={cn(
                      "rounded-full px-3.5 py-1.5 text-sm font-semibold tracking-wide",
                      getRiskBadgeStyles(patient.riskLevel)
                    )}
                  >
                    <span className={cn("mr-2 h-2.5 w-2.5 rounded-[3px]", getRiskDot(patient.riskLevel))} />
                    {getRiskLabel(patient.riskLevel)}
                  </Badge>
                </TableCell>
                <TableCell>
                  <ChevronRight className="h-5 w-5 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </section>
  )
}
