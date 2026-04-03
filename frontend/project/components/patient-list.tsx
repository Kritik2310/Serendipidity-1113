"use client"

import { useRouter } from "next/navigation"
import { patients, type RiskLevel } from "@/lib/patient-data"
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
import { ChevronRight, Heart, Thermometer, Droplets } from "lucide-react"

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

  return (
    <section className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-semibold text-foreground">Patient Overview</h2>
          <p className="mt-1 text-base text-muted-foreground">
            {patients.length} patients currently in ICU
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

      <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-[100px] py-4 text-sm font-semibold uppercase tracking-wide text-foreground">Patient ID</TableHead>
              <TableHead className="py-4 text-sm font-semibold uppercase tracking-wide text-foreground">Name</TableHead>
              <TableHead className="w-[80px] py-4 text-sm font-semibold uppercase tracking-wide text-foreground">Age</TableHead>
              <TableHead className="py-4 text-sm font-semibold uppercase tracking-wide text-foreground">Bed</TableHead>
              <TableHead className="py-4 text-sm font-semibold uppercase tracking-wide text-foreground">Condition</TableHead>
              <TableHead className="py-4 text-sm font-semibold uppercase tracking-wide text-foreground">Vitals</TableHead>
              <TableHead className="py-4 text-sm font-semibold uppercase tracking-wide text-foreground">Risk Level</TableHead>
              <TableHead className="w-[50px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {patients.map((patient) => (
              <TableRow
                key={patient.id}
                className={cn(
                  "group cursor-pointer transition-colors hover:bg-muted/50",
                  patient.riskLevel === "high" && "bg-risk-high/[0.04] hover:bg-risk-high/[0.08]",
                  patient.riskLevel === "medium" && "bg-risk-medium/[0.03] hover:bg-risk-medium/[0.06]"
                )}
                onClick={() => router.push(`/analysis/${patient.id}`)}
              >
                <TableCell className="py-5 font-mono text-base text-muted-foreground">
                  {patient.id}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-3">
                    <div
                      className={cn(
                        "flex h-11 w-11 items-center justify-center rounded-full text-base font-semibold",
                        patient.riskLevel === "high"
                          ? "bg-risk-high/15 text-risk-high ring-2 ring-risk-high/20"
                          : patient.riskLevel === "medium"
                          ? "bg-risk-medium/15 text-risk-medium ring-2 ring-risk-medium/20"
                          : "bg-risk-low/12 text-risk-low ring-2 ring-risk-low/20"
                      )}
                    >
                      {patient.name
                        .split(" ")
                        .map((n) => n[0])
                        .join("")}
                    </div>
                    <div>
                      <p className="text-lg font-semibold text-foreground">{patient.name}</p>
                      <p className="text-sm text-muted-foreground">{patient.gender}</p>
                    </div>
                  </div>
                </TableCell>
                <TableCell className="text-base text-muted-foreground">{patient.age}</TableCell>
                <TableCell>
                  <span className="font-mono text-base font-medium">{patient.bedNumber}</span>
                </TableCell>
                <TableCell>
                  <span className="text-base font-medium text-foreground">{patient.condition}</span>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-5 text-sm text-muted-foreground">
                    <div className="flex items-center gap-1.5">
                      <Heart className="h-4 w-4" />
                      <span className="font-medium">{patient.vitals.heartRate}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Thermometer className="h-4 w-4" />
                      <span>{patient.vitals.temperature}°C</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Droplets className="h-4 w-4" />
                      <span>{patient.vitals.oxygenSaturation}%</span>
                    </div>
                  </div>
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
