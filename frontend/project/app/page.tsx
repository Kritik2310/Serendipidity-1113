import { DashboardLayout } from "@/components/dashboard-layout"
import { HeroSection } from "@/components/hero-section"
import { PatientList } from "@/components/patient-list"

export default function HomePage() {
  return (
    <DashboardLayout>
      <HeroSection />
      <PatientList />
    </DashboardLayout>
  )
}
