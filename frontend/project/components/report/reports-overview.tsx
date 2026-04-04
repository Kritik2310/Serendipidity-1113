"use client"

import { useMemo } from "react"
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { AnalyzeResponse, PatientReportBundle } from "@/lib/api"

interface ReportsOverviewProps {
  bundles: PatientReportBundle[]
}

function isToday(dateString: string) {
  const date = new Date(dateString)
  const now = new Date()
  return (
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  )
}

function hourLabel(dateString: string) {
  return new Date(dateString).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

export function ReportsOverview({ bundles }: ReportsOverviewProps) {
  const todayReports = useMemo(
    () => bundles.filter((bundle) => bundle.report && isToday(bundle.report.generated_at)),
    [bundles]
  )

  const riskDistribution = useMemo(() => {
    const high = todayReports.filter((b) => b.summary.riskLevel === "high").length
    const medium = todayReports.filter((b) => b.summary.riskLevel === "medium").length
    const low = todayReports.filter((b) => b.summary.riskLevel === "low").length
    return [
      { name: "High", value: high, fill: "#dc2626" },
      { name: "Medium", value: medium, fill: "#d97706" },
      { name: "Stable", value: low, fill: "#16a34a" },
    ]
  }, [todayReports])

  const hourlyTrend = useMemo(() => {
    const counts = new Map<string, number>()
    todayReports.forEach((bundle) => {
      const label = hourLabel(bundle.report!.generated_at)
      counts.set(label, (counts.get(label) || 0) + 1)
    })
    return Array.from(counts.entries()).map(([time, reports]) => ({ time, reports }))
  }, [todayReports])

  const topConcerns = useMemo(() => {
    const counts = new Map<string, number>()
    todayReports.forEach((bundle) => {
      const concern = bundle.report?.primary_concern || "Unknown"
      counts.set(concern, (counts.get(concern) || 0) + 1)
    })
    return Array.from(counts.entries())
      .map(([concern, count]) => ({ concern, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5)
  }, [todayReports])

  const totalOutliersRemoved = useMemo(
    () =>
      todayReports.reduce(
        (sum, bundle) => sum + Number(bundle.report?.data_quality.outliers_removed_count || 0),
        0
      ),
    [todayReports]
  )

  return (
    <div className="space-y-6 p-8">
      <div className="flex items-end justify-between gap-6">
        <div>
          <h1 className="text-3xl font-semibold text-foreground">Daily Reports Overview</h1>
          <p className="mt-2 text-base text-muted-foreground">
            Same-day trends across generated reports, risk distribution, and dominant clinical concerns.
          </p>
        </div>
        <Badge variant="outline" className="px-4 py-2 text-sm">
          {todayReports.length} reports generated today
        </Badge>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm uppercase tracking-wide text-muted-foreground">Today&apos;s Reports</CardTitle>
          </CardHeader>
          <CardContent className="text-3xl font-semibold">{todayReports.length}</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm uppercase tracking-wide text-muted-foreground">Outliers Removed</CardTitle>
          </CardHeader>
          <CardContent className="text-3xl font-semibold">{totalOutliersRemoved}</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm uppercase tracking-wide text-muted-foreground">Most Common Concern</CardTitle>
          </CardHeader>
          <CardContent className="text-lg font-semibold">
            {topConcerns[0]?.concern || "No reports yet"}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Report Volume By Time</CardTitle>
          </CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={hourlyTrend}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="time" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="reports" radius={[8, 8, 0, 0]} fill="hsl(var(--primary))" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Risk Distribution</CardTitle>
          </CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={riskDistribution} dataKey="value" nameKey="name" innerRadius={70} outerRadius={110} paddingAngle={4}>
                  {riskDistribution.map((entry) => (
                    <Cell key={entry.name} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Top Clinical Concerns Today</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {topConcerns.length === 0 ? (
              <p className="text-muted-foreground">No reports generated today yet.</p>
            ) : (
              topConcerns.map((item) => (
                <div
                  key={item.concern}
                  className="flex items-center justify-between rounded-lg border border-border bg-muted/20 px-4 py-3"
                >
                  <span className="font-medium text-foreground">{item.concern}</span>
                  <Badge variant="outline">{item.count} reports</Badge>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
