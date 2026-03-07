import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import About from './pages/About.jsx'
import PatternMapper from './pages/PatternMapper.jsx'
import ContradictionEngine from './pages/ContradictionEngine.jsx'
import CaseTimeline from './pages/CaseTimeline.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<App />} />
          <Route path="/about" element={<About />} />
          <Route path="/patterns" element={<PatternMapper />} />
          <Route path="/contradictions" element={<ContradictionEngine />} />
          <Route path="/timeline" element={<CaseTimeline />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  </StrictMode>,
)
