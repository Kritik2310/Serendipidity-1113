import { Activity, Brain, Shield } from "lucide-react"

export function HeroSection() {
  return (
    <section className="relative overflow-hidden border-b border-border bg-card px-8 py-12">
      <div className="relative z-10 flex items-center justify-between gap-12">
        <div className="max-w-2xl">
          <h1 className="text-4xl font-bold tracking-tight text-foreground">
            AI-Powered ICU Assistant
          </h1>
          <p className="mt-4 text-lg text-muted-foreground leading-relaxed">
            Real-time patient monitoring, risk detection, and clinical insights for faster decision-making.
          </p>
          <div className="mt-8 flex items-center gap-8">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Activity className="h-5 w-5 text-primary" />
              </div>
              <span className="text-sm font-medium text-foreground">Real-time Monitoring</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Brain className="h-5 w-5 text-primary" />
              </div>
              <span className="text-sm font-medium text-foreground">AI Risk Detection</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Shield className="h-5 w-5 text-primary" />
              </div>
              <span className="text-sm font-medium text-foreground">Clinical Insights</span>
            </div>
          </div>
        </div>
        <div className="hidden lg:block">
          <div className="relative">
            <div className="absolute -inset-4 rounded-2xl bg-primary/5" />
            <div className="relative flex h-48 w-64 flex-col items-center justify-center rounded-xl border border-border bg-card p-6 shadow-sm">
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 animate-pulse rounded-full bg-risk-low" />
                <div className="h-3 w-3 animate-pulse rounded-full bg-risk-medium" style={{ animationDelay: "150ms" }} />
                <div className="h-3 w-3 animate-pulse rounded-full bg-risk-high" style={{ animationDelay: "300ms" }} />
              </div>
              <svg className="mt-4 h-20 w-full" viewBox="0 0 200 60">
                <path
                  d="M0,30 L20,30 L25,10 L30,50 L35,25 L40,35 L45,30 L200,30"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className="text-primary"
                />
              </svg>
              <p className="mt-4 text-sm font-medium text-muted-foreground">Live Patient Vitals</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
