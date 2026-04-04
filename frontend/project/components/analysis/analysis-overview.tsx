"use client"

import { useMemo } from "react"
import { useRouter } from "next/navigation"
import { Activity, AlertTriangle, ArrowUpRight, CheckCircle2, Clock3, ShieldAlert } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { cn } from "@/lib/utils"
import type { PatientSummary } from "@/lib/api"

interface AnalysisOverviewProps {
  patients: PatientSummary[]
}

function riskTone(riskLevel: PatientSummary["riskLevel"]) {
  if (riskLevel === "high") return "text-risk-high"
  if (riskLevel === "medium") return "text-risk-medium"
  return "text-risk-low"
}

export function AnalysisOverview({ patients }: AnalysisOverviewProps) {
  const router = useRouter()

  const stats = useMemo(() => {
    const total = patients.length
    const high = patients.filter((p) => p.riskLevel === "high").length
    const medium = patients.filter((p) => p.riskLevel === "medium").length
    const low = patients.filter((p) => p.riskLevel === "low").length
    const active = patients.filter((p) => p.status.toLowerCase() !== "unknown").length

    return { total, high, medium, low, active }
  }, [patients])

  const sortedPatients = useMemo(
    () =>
      [...patients].sort((a, b) => {
        const riskOrder = { high: 0, medium: 1, low: 2 }
        const riskDiff = riskOrder[a.riskLevel] - riskOrder[b.riskLevel]
        if (riskDiff !== 0) return riskDiff
        return new Date(b.lastAnalyzed).getTime() - new Date(a.lastAnalyzed).getTime()
      }),
    [patients]
  )

  return (
    <div className="space-y-6 p-8">
      <div className="flex items-end justify-between gap-6">
        <div>
          <h1 className="text-3xl font-semibold text-foreground">Analysis Overview</h1>
          <p className="mt-2 text-base text-muted-foreground">
            Operational view across all analyzed ICU patients, prioritized by risk and recency.
          </p>
        </div>
        <Badge variant="outline" className="px-4 py-2 text-sm">
          <Clock3 className="mr-2 h-4 w-4" />
          {patients.length} active tracked cases
        </Badge>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm uppercase tracking-wide text-muted-foreground">All Patients</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-between">
            <span className="text-3xl font-semibold">{stats.total}</span>
            <Activity className="h-5 w-5 text-primary" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm uppercase tracking-wide text-muted-foreground">High Risk</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-between">
            <span className="text-3xl font-semibold text-risk-high">{stats.high}</span>
            <ShieldAlert className="h-5 w-5 text-risk-high" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm uppercase tracking-wide text-muted-foreground">Medium Risk</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-between">
            <span className="text-3xl font-semibold text-risk-medium">{stats.medium}</span>
            <AlertTriangle className="h-5 w-5 text-risk-medium" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm uppercase tracking-wide text-muted-foreground">Stable</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-between">
            <span className="text-3xl font-semibold text-risk-low">{stats.low}</span>
            <CheckCircle2 className="h-5 w-5 text-risk-low" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm uppercase tracking-wide text-muted-foreground">Reports Ready</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-between">
            <span className="text-3xl font-semibold">{stats.active}</span>
            <ArrowUpRight className="h-5 w-5 text-primary" />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-xl">Current Patient Queue</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-hidden rounded-lg border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Subject</TableHead>
                  <TableHead>Admission</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Primary Concern</TableHead>
                  <TableHead>Risk</TableHead>
                  <TableHead>Last Updated</TableHead>
                  <TableHead className="text-right">Open</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedPatients.map((patient) => (
                  <TableRow
                    key={patient.analysisId}
                    className="cursor-pointer hover:bg-muted/40"
                    onClick={() => router.push(`/analysis/${patient.analysisId}`)}
                  >
                    <TableCell className="font-mono">{patient.subjectId}</TableCell>
                    <TableCell className="font-mono">{patient.hadmId}</TableCell>
                    <TableCell className="capitalize">{patient.status}</TableCell>
                    <TableCell className="max-w-[340px] truncate">{patient.primaryConcern}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className={cn("capitalize", riskTone(patient.riskLevel))}>
                        {patient.riskLevel}
                      </Badge>
                    </TableCell>
                    <TableCell>{new Date(patient.lastAnalyzed).toLocaleString()}</TableCell>
                    <TableCell className="text-right text-primary">View analysis</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
