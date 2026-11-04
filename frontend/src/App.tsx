import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { DashboardPage } from './pages/DashboardPage'
import { NewInterviewPage } from './pages/NewInterviewPage'
import { InterviewRoomPage } from './pages/InterviewRoomPage'
import { InterviewReportPage } from './pages/InterviewReportPage'
import { PlaceholderPage } from './pages/PlaceholderPage'
import { NotFoundPage } from './pages/NotFoundPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="interviews/new" element={<NewInterviewPage />} />
          <Route
            path="interviews/:interviewId/room"
            element={<InterviewRoomPage />}
          />
          <Route
            path="interviews/:interviewId/report"
            element={<InterviewReportPage />}
          />
          <Route
            path="interviews"
            element={
              <PlaceholderPage
                title="Interview Management"
                subtitle="Live interview sessions, candidate flows, and dynamic evaluation histories."
                milestone="Phase 2 - Live Interview Experience"
              />
            }
          />
          <Route
            path="questions"
            element={
              <PlaceholderPage
                title="Adaptive Question Bank"
                subtitle="Curated interview questions, criteria weighting, and follow-up generation templates."
                milestone="Phase 3 - Question & Criteria Authoring"
              />
            }
          />
          <Route
            path="analytics"
            element={
              <PlaceholderPage
                title="Evaluation Analytics"
                subtitle="Aggregate rubric scores, candidate skill distribution, and LLM evaluator consistency metrics."
                milestone="Phase 4 - Analytics & Insights"
              />
            }
          />
          <Route
            path="settings"
            element={
              <PlaceholderPage
                title="Platform Settings"
                subtitle="Configure Ollama model bindings, FastAPI endpoints, prompt instructions, and database parameters."
                milestone="Phase 5 - Configuration"
              />
            }
          />
          <Route path="404" element={<NotFoundPage />} />
          <Route path="*" element={<Navigate to="/404" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
