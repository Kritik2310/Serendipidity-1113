"use client"

import { BadgeCheck, HeartHandshake, Languages } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface FamilyCommunication {
  time_window_hours: number
  regional_language: string
  regional_language_code: string
  english_summary: string
  regional_summary: string
  generated_at: string
}

interface FamilyCommunicationPanelProps {
  familyCommunication: FamilyCommunication
}

function toBulletPoints(text: string): string[] {
  return text
    .split(/(?<=[.!?।])\s+/)
    .map((sentence) => sentence.trim())
    .filter(Boolean)
}

export function FamilyCommunicationPanel({ familyCommunication }: FamilyCommunicationPanelProps) {
  const englishPoints = toBulletPoints(familyCommunication.english_summary)
  const regionalPoints = toBulletPoints(familyCommunication.regional_summary)

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-3">
          <BadgeCheck className="h-5 w-5 text-primary" />
          <div>
            <CardTitle className="text-2xl font-semibold">Family Communication</CardTitle>
            <p className="mt-1 text-lg text-muted-foreground">
              Simple update covering the last {familyCommunication.time_window_hours} hours.
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="rounded-lg border border-border bg-muted/20 p-5">
          <p className="mb-4 text-3xl font-semibold uppercase tracking-wide text-muted-foreground">English</p>
          <ul className="space-y-3">
            {englishPoints.map((point, index) => (
              <li key={`english-${index}`} className="flex items-start gap-3">
                <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-primary" />
                <p className="text-base leading-7 text-foreground text-2xl">{point}</p>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-lg border border-border bg-muted/20 p-5">
          <div className="mb-3 flex items-center gap-2">
            <Languages className="h-4 w-4 text-primary" />
            <p className="text-lg font-semibold uppercase tracking-wide text-muted-foreground">
              {familyCommunication.regional_language}
            </p>
          </div>
          <ul className="space-y-3">
            {regionalPoints.map((point, index) => (
              <li key={`regional-${index}`} className="flex items-start gap-3 text-3xl">
                <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-primary" />
                <p className="text-base leading-7 text-foreground text-2xl">{point}</p>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-lg border border-primary/20 bg-primary/5 p-4">
          <p className="text-sm text-foreground">
            This section is meant for family communication and does not replace direct discussion with the care team.
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            Generated {new Date(familyCommunication.generated_at).toLocaleString()}
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
