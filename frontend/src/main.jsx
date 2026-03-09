import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import About from './pages/About.jsx'
import PatternMapper from './pages/PatternMapper.jsx'
import ContradictionEngine from './pages/ContradictionEngine.jsx'
import CaseTimeline from './pages/CaseTimeline.jsx'
import TrialDashboard from './pages/TrialDashboard.jsx'
import WitnessProfiles from './pages/WitnessProfiles.jsx'
import HearingChecklist from './pages/HearingChecklist.jsx'
import ComplaintsTracker from './pages/ComplaintsTracker.jsx'
import EventTimeline from './pages/EventTimeline.jsx'
import CrossExamPanel from './pages/CrossExamPanel.jsx'
import PrintView from './pages/PrintView.jsx'
import CostCalculator from './pages/CostCalculator.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'
import PublicShare from './pages/PublicShare.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<TrialDashboard />} />
          <Route path="/trial" element={<TrialDashboard />} />
          <Route path="/search" element={<App />} />
          <Route path="/about" element={<About />} />
          <Route path="/patterns" element={<PatternMapper />} />
          <Route path="/contradictions" element={<ContradictionEngine />} />
          <Route path="/timeline" element={<CaseTimeline />} />
          <Route path="/witnesses" element={<WitnessProfiles />} />
          <Route path="/checklist" element={<HearingChecklist />} />
          <Route path="/complaints" element={<ComplaintsTracker />} />
          <Route path="/events" element={<EventTimeline />} />
          <Route path="/crossexam" element={<CrossExamPanel />} />
          <Route path="/print" element={<PrintView />} />
          <Route path="/costs" element={<CostCalculator />} />
          <Route path="/share" element={<PublicShare />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  </StrictMode>,
)
