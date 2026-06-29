import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from '@/components/AppShell'
import { ArtifactsPage } from '@/pages/Artifacts'
import { AuditPage } from '@/pages/Audit'
import { BenchmarksPage } from '@/pages/Benchmarks'
import { CapabilitiesPage } from '@/pages/Capabilities'
import { DashboardPage } from '@/pages/Dashboard'
import { DecisionsPage } from '@/pages/Decisions'
import { EvidencePage } from '@/pages/Evidence'
import { ExperiencesPage } from '@/pages/Experiences'
import { InsightsPage } from '@/pages/Insights'
import { MethodologyPage } from '@/pages/Methodology'
import { ResearchContextPage } from '@/pages/ResearchContext'
import { ResearchQueuePage } from '@/pages/ResearchQueue'
import { ResearchReadinessPage } from '@/pages/ResearchReadiness'
import { ResearchRoundsPage } from '@/pages/ResearchRounds'
import { ResearchWorkbenchPage } from '@/pages/ResearchWorkbench'
import { ReviewsPage } from '@/pages/Reviews'
import { SessionDetailPage, SessionsPage } from '@/pages/Sessions'
import { SourcesPage } from '@/pages/Sources'
import { StatusPage } from '@/pages/Status'

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/sources" element={<SourcesPage />} />
        <Route path="/insights" element={<InsightsPage />} />
        <Route path="/research" element={<ResearchWorkbenchPage />} />
        <Route path="/research/methodology" element={<MethodologyPage />} />
        <Route path="/research-queue" element={<ResearchQueuePage />} />
        <Route path="/research/context" element={<ResearchContextPage />} />
        <Route path="/research/readiness" element={<ResearchReadinessPage />} />
        <Route path="/research/rounds" element={<ResearchRoundsPage />} />
        <Route path="/sessions" element={<SessionsPage />} />
        <Route path="/sessions/:id" element={<SessionDetailPage />} />
        <Route path="/research/audit" element={<AuditPage />} />
        <Route path="/evidence" element={<EvidencePage />} />
        <Route path="/artifacts" element={<ArtifactsPage />} />
        <Route path="/benchmarks" element={<BenchmarksPage />} />
        <Route path="/reviews" element={<ReviewsPage />} />
        <Route path="/decisions" element={<DecisionsPage />} />
        <Route path="/knowledge/experiences" element={<ExperiencesPage />} />
        <Route path="/capabilities" element={<CapabilitiesPage />} />
        <Route path="/status" element={<StatusPage />} />
      </Route>
    </Routes>
  )
}
