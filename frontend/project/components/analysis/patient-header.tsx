import { ArrowLeft, Heart, Thermometer, Droplets, Activity } from "lucide-react"
import Link from "next/link"
import type { Patient } from "@/lib/patient-data"
import { cn } from "@/lib/utils"

interface PatientHeaderProps {
  patient: Patient
}

export function PatientHeader({ patient }: PatientHeaderProps) {
  return (
    <div className="border-b border-border bg-card px-8 py-6">
      <div className="flex items-center gap-4 mb-4">
        <Link
          href="/"
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
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
              patient.riskLevel === "high"
                ? "bg-risk-high/10 text-risk-high"
                : patient.riskLevel === "medium"
                ? "bg-risk-medium/10 text-risk-medium"
                : "bg-risk-low/10 text-risk-low"
            )}
          >
            {patient.name
              .split(" ")
              .map((n) => n[0])
              .join("")}
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground">{patient.name}</h1>
            <div className="mt-1 flex items-center gap-4 text-sm text-muted-foreground">
              <span>{patient.age} years old</span>
              <span>{patient.gender}</span>
              <span className="font-mono">{patient.id}</span>
              <span className="font-mono">{patient.bedNumber}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/50 px-4 py-2">
            <Heart className="h-4 w-4 text-risk-high" />
            <span className="text-sm font-medium">{patient.vitals.heartRate} bpm</span>
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/50 px-4 py-2">
            <Activity className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium">{patient.vitals.bloodPressure}</span>
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/50 px-4 py-2">
            <Thermometer className="h-4 w-4 text-risk-medium" />
            <span className="text-sm font-medium">{patient.vitals.temperature}°C</span>
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/50 px-4 py-2">
            <Droplets className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium">{patient.vitals.oxygenSaturation}%</span>
          </div>
        </div>
      </div>
    </div>
  )
}
