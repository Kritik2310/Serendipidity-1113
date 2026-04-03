import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { BookOpen, ExternalLink } from "lucide-react"
import type { Guideline } from "@/lib/patient-data"

interface GuidelinesPanelProps {
  guidelines: Guideline[]
}

export function GuidelinesPanel({ guidelines }: GuidelinesPanelProps) {
  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-muted-foreground" />
          <CardTitle className="text-lg font-semibold">Clinical Guidelines</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col gap-3">
          {guidelines.map((guideline) => (
            <div
              key={guideline.id}
              className="rounded-lg border border-border bg-muted/30 p-4"
            >
              <div className="flex items-start justify-between gap-2">
                <h4 className="font-medium text-foreground">{guideline.title}</h4>
                <ExternalLink className="h-4 w-4 shrink-0 text-muted-foreground" />
              </div>
              <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                {guideline.description}
              </p>
              <p className="mt-2 text-xs text-primary font-medium">
                Source: {guideline.source}
              </p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
