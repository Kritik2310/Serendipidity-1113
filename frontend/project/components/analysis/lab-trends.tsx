"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { LabResult } from "@/lib/patient-data"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts"
import { cn } from "@/lib/utils"

interface LabTrendsProps {
  labs: LabResult[]
}

export function LabTrends({ labs }: LabTrendsProps) {
  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg font-semibold">Lab Trends</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {labs.map((lab) => (
          <div key={lab.name} className="rounded-lg border border-border bg-muted/30 p-4">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <h4 className="font-medium text-foreground">{lab.name}</h4>
                <span
                  className={cn(
                    "rounded-full px-2 py-0.5 text-xs font-medium",
                    lab.status === "critical"
                      ? "bg-risk-high/10 text-risk-high"
                      : lab.status === "abnormal"
                      ? "bg-risk-medium/10 text-risk-medium"
                      : "bg-risk-low/10 text-risk-low"
                  )}
                >
                  {lab.status === "critical"
                    ? "Critical"
                    : lab.status === "abnormal"
                    ? "Abnormal"
                    : "Normal"}
                </span>
              </div>
              <div className="text-right">
                <span
                  className={cn(
                    "text-lg font-bold",
                    lab.status === "critical"
                      ? "text-risk-high"
                      : lab.status === "abnormal"
                      ? "text-risk-medium"
                      : "text-foreground"
                  )}
                >
                  {lab.value} {lab.unit}
                </span>
                <p className="text-xs text-muted-foreground">
                  Normal: {lab.normalRange}
                </p>
              </div>
            </div>
            <div className="h-24">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={lab.trend}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                  <XAxis
                    dataKey="time"
                    tick={{ fontSize: 10 }}
                    className="text-muted-foreground"
                    stroke="currentColor"
                  />
                  <YAxis
                    tick={{ fontSize: 10 }}
                    className="text-muted-foreground"
                    stroke="currentColor"
                    domain={["auto", "auto"]}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      borderColor: "hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                    labelStyle={{ color: "hsl(var(--foreground))" }}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke={
                      lab.status === "critical"
                        ? "hsl(var(--risk-high))"
                        : lab.status === "abnormal"
                        ? "hsl(var(--risk-medium))"
                        : "hsl(var(--primary))"
                    }
                    strokeWidth={2}
                    dot={(props) => {
                      const { cx, cy, index } = props
                      const isLast = index === lab.trend.length - 1
                      if (lab.status === "critical" && isLast) {
                        return (
                          <circle
                            key={index}
                            cx={cx}
                            cy={cy}
                            r={5}
                            fill="hsl(var(--risk-high))"
                            stroke="hsl(var(--card))"
                            strokeWidth={2}
                          />
                        )
                      }
                      return (
                        <circle
                          key={index}
                          cx={cx}
                          cy={cy}
                          r={3}
                          fill={
                            lab.status === "critical"
                              ? "hsl(var(--risk-high))"
                              : lab.status === "abnormal"
                              ? "hsl(var(--risk-medium))"
                              : "hsl(var(--primary))"
                          }
                        />
                      )
                    }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
