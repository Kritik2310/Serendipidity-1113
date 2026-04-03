"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { DiseaseProgression } from "@/lib/patient-data"
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

interface DiseaseProgressionPanelProps {
  progression: DiseaseProgression
}

function getChartDirectionStyles(progression: DiseaseProgression) {
  const firstScore = progression.timeline[0]?.score ?? 0
  const lastScore = progression.timeline[progression.timeline.length - 1]?.score ?? 0

  if (lastScore > firstScore) {
    return {
      line: "#16a34a",
      glow: "rgba(22, 163, 74, 0.28)",
    }
  }

  if (lastScore < firstScore) {
    return {
      line: "#dc2626",
      glow: "rgba(220, 38, 38, 0.28)",
    }
  }

  return {
    line: "hsl(var(--risk-medium))",
    glow: "rgba(217, 119, 6, 0.22)",
  }
}

function getTrendStyles(trendDirection: DiseaseProgression["trendDirection"]) {
  if (trendDirection === "worsening") {
    return {
      label: "Increasing Risk",
      badge: "bg-risk-high/10 text-risk-high border-risk-high/30",
    }
  }

  if (trendDirection === "improving") {
    return {
      label: "Falling Risk",
      badge: "bg-risk-low/10 text-risk-low border-risk-low/30",
    }
  }

  return {
    label: "Stable",
    badge: "bg-risk-medium/10 text-risk-medium border-risk-medium/30",
  }
}

export function DiseaseProgressionPanel({ progression }: DiseaseProgressionPanelProps) {
  const styles = getTrendStyles(progression.trendDirection)
  const chartStyles = getChartDirectionStyles(progression)

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle className="text-3xl font-semibold">Disease Progression</CardTitle>
            <p className="mt-1 text-lg text-muted-foreground">{progression.stage}</p>
          </div>
          <Badge variant="outline" className={cn("px-4 py-1.5 text-base font-semibold", styles.badge)}>
            {styles.label}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        <div className="rounded-lg border border-border bg-muted/20 p-5">
          <p className="text-lg font-medium leading-8 text-foreground">{progression.summary}</p>
          <p className="mt-3 text-base text-muted-foreground">Next 24h outlook: {progression.next24hOutlook}</p>
        </div>

        <div className="h-60 rounded-lg border border-border bg-card p-3">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={progression.timeline}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="time" tick={{ fontSize: 15, fontWeight: 700 }} stroke="currentColor" />
              <YAxis hide domain={[30, 90]} />
              <Tooltip
                formatter={(value: number, _name, payload) => [
                  `Score ${value}`,
                  payload?.payload.source,
                ]}
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  borderColor: "hsl(var(--border))",
                  borderRadius: "8px",
                }}
              />
              <ReferenceArea x1="-30m" x2="Now" fill="hsl(var(--primary))" fillOpacity={0.08} />
              <Line
                type="monotone"
                dataKey="score"
                stroke={chartStyles.line}
                strokeWidth={6}
                dot={(props) => {
                  const { cx, cy, payload, index } = props
                  const isRealtime = payload.source === "Real-time"
                  return (
                    <g key={index}>
                      <circle
                        cx={cx}
                        cy={cy}
                        r={isRealtime ? 11 : 8}
                        fill={chartStyles.glow}
                      />
                      <circle
                        cx={cx}
                        cy={cy}
                        r={isRealtime ? 7.5 : 5.5}
                        fill={isRealtime ? "hsl(var(--card))" : chartStyles.line}
                        stroke={chartStyles.line}
                        strokeWidth={isRealtime ? 4 : 3}
                      />
                    </g>
                  )
                }}
                activeDot={{
                  r: 9,
                  fill: "hsl(var(--card))",
                  stroke: chartStyles.line,
                  strokeWidth: 4,
                }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-lg border border-border bg-muted/20 p-5">
            <p className="mb-3 text-base font-semibold uppercase tracking-wide text-muted-foreground">
              Historic Insights
            </p>
            <ul className="space-y-2">
              {progression.historicInsights.map((insight) => (
                <li key={insight.id} className="text-lg">
                  <p className="font-medium text-foreground">{insight.window}: {insight.signal}</p>
                  <p className="text-base text-muted-foreground">{insight.impact}</p>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-lg border border-border bg-muted/20 p-5">
            <p className="mb-3 text-base font-semibold uppercase tracking-wide text-muted-foreground">
              Real-time Insights
            </p>
            <ul className="space-y-2">
              {progression.realTimeInsights.map((insight) => (
                <li key={insight.id} className="flex items-start justify-between gap-3 text-lg">
                  <div>
                    <p className="font-medium text-foreground">{insight.metric}</p>
                    <p className="text-base text-muted-foreground">Updated {insight.updatedAt}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-foreground">{insight.value}</p>
                    <span
                      className={cn(
                        "inline-block rounded-full px-3 py-1 text-sm font-semibold uppercase",
                        insight.status === "critical"
                          ? "bg-risk-high/10 text-risk-high"
                          : insight.status === "watch"
                          ? "bg-risk-medium/10 text-risk-medium"
                          : "bg-risk-low/10 text-risk-low"
                      )}
                    >
                      {insight.status}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
