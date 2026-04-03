import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { AlertTriangle, AlertCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import type { Alert } from "@/lib/patient-data"

interface AlertsPanelProps {
  alerts: Alert[]
}

export function AlertsPanel({ alerts }: AlertsPanelProps) {
  const criticalAlerts = alerts.filter((a) => a.type === "critical")
  const abnormalAlerts = alerts.filter((a) => a.type === "abnormal")

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg font-semibold">Alerts</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {criticalAlerts.length > 0 && (
          <div>
            <h4 className="mb-2 flex items-center gap-2 text-sm font-semibold text-risk-high">
              <AlertTriangle className="h-4 w-4" />
              Critical Alerts
            </h4>
            <div className="flex flex-col gap-2">
              {criticalAlerts.map((alert) => (
                <div
                  key={alert.id}
                  className="rounded-lg border border-risk-high/20 bg-risk-high/5 p-3"
                >
                  <p className="text-sm font-medium text-foreground">
                    {alert.message}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {alert.timestamp}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {abnormalAlerts.length > 0 && (
          <div>
            <h4 className="mb-2 flex items-center gap-2 text-sm font-semibold text-risk-medium">
              <AlertCircle className="h-4 w-4" />
              Abnormal Findings
            </h4>
            <div className="flex flex-col gap-2">
              {abnormalAlerts.map((alert) => (
                <div
                  key={alert.id}
                  className="rounded-lg border border-risk-medium/20 bg-risk-medium/5 p-3"
                >
                  <p className="text-sm font-medium text-foreground">
                    {alert.message}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {alert.timestamp}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {criticalAlerts.length === 0 && abnormalAlerts.length === 0 && (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-risk-low/10">
              <AlertCircle className="h-6 w-6 text-risk-low" />
            </div>
            <p className="mt-3 text-sm font-medium text-foreground">No Active Alerts</p>
            <p className="text-xs text-muted-foreground">Patient vitals are within normal range</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
