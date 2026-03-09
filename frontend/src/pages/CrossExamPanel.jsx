import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import TrialBanner from '../components/TrialBanner'

const SEVERITY_STYLE = {
  DIRECT: 'text-red-400 border-red-500/40 bg-red-900/20',
  PARTIAL: 'text-amber-400 border-amber-500/40 bg-amber-900/20',
  NONE: 'text-green-400 border-green-500/40 bg-green-900/20',
}

function SeverityBadge({ severity }) {
  const s = (severity || 'NONE').toUpperCase()
  const cls = SEVERITY_STYLE[s] || SEVERITY_STYLE.NONE
  return (
    <span className={`font-mono text-[10px] tracking-widest border rounded px-1.5 py-0.5 ${cls}`}>
      {s}
    </span>
  )
}

export default function CrossExamPanel() {
  const [contradictions, setContradictions] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [questions, setQuestions] = useState(null)   // { questions_text, generated_at, model_used } | null
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Load all contradictions on mount
  useEffect(() => {
    fetch('/api/contradictions')
      .then(r => r.json())
      .catch(() => [])
      .then(data => setContradictions(Array.isArray(data) ? data : []))
  }, [])

  // Load existing questions when a contradiction is selected
  useEffect(() => {
    if (selectedId === null) return
    setQuestions(null)
    setError(null)
    fetch(`/api/crossexam/${selectedId}`)
      .then(r => {
        if (r.status === 404) return null
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(data => setQuestions(data))
      .catch(err => setError(err.message))
  }, [selectedId])

  async function handleGenerate() {
    if (selectedId === null) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/crossexam/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contradiction_id: selectedId }),
      })
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        throw new Error(d.detail || `HTTP ${res.status}`)
      }
      const data = await res.json()
      setQuestions(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const selected = contradictions.find(c => c.id === selectedId) || null

  return (
    <div className="min-h-screen bg-ink-900 font-sans text-slate-200">
      <div className="h-px bg-gradient-to-r from-transparent via-amber-500/60 to-transparent" />

      {/* Header */}
      <header className="sticky top-0 z-20 border-b border-ink-600 bg-ink-900/90 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl tracking-[0.12em] text-white leading-none">
              CROSS-EXAMINATION QUESTIONS
            </h1>
            <p className="font-mono text-[10px] text-slate-600 tracking-widest mt-1 uppercase">
              PC 19700 · Trial May 19, 2026
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link to="/contradictions" className="text-[10px] font-mono text-slate-500 border border-slate-700 px-2 py-1 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors">
              CONTRADICTIONS
            </Link>
            <Link to="/trial" className="text-[10px] font-mono text-slate-500 border border-slate-700 px-2 py-1 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors">
              TRIAL
            </Link>
          </div>
        </div>
      </header>

      <TrialBanner />

      <main className="max-w-6xl mx-auto px-4 py-6">
        <div className="flex gap-4 h-[calc(100vh-180px)]">

          {/* Left column — contradiction list */}
          <div className="w-72 flex-shrink-0 overflow-y-auto border border-ink-700 rounded-lg bg-ink-800/40">
            <div className="sticky top-0 bg-ink-800 border-b border-ink-700 px-3 py-2">
              <p className="font-mono text-[10px] text-slate-500 tracking-widest uppercase">
                {contradictions.length} Contradictions
              </p>
            </div>
            {contradictions.length === 0 ? (
              <p className="font-mono text-[10px] text-slate-600 px-3 py-4 text-center">Loading...</p>
            ) : (
              contradictions.map(c => (
                <button
                  key={c.id}
                  onClick={() => setSelectedId(c.id)}
                  className={`w-full text-left px-3 py-3 border-b border-ink-700 transition-colors ${
                    selectedId === c.id
                      ? 'bg-sky-900/30 border-l-2 border-l-sky-500'
                      : 'hover:bg-ink-700/50'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <SeverityBadge severity={c.severity} />
                    <span className="font-mono text-[9px] text-slate-600">#{c.id}</span>
                  </div>
                  <p className="font-mono text-[10px] text-slate-400 leading-snug line-clamp-2">
                    {(c.claim || '').slice(0, 80)}{c.claim?.length > 80 ? '…' : ''}
                  </p>
                </button>
              ))
            )}
          </div>

          {/* Right column — detail + questions */}
          <div className="flex-1 overflow-y-auto">
            {selected === null ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <p className="font-mono text-xs text-slate-600 tracking-widest">SELECT A CONTRADICTION</p>
                  <p className="font-mono text-[10px] text-slate-700 mt-2">
                    Click any contradiction on the left to view or generate cross-examination questions.
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Contradiction detail card */}
                <div className="border border-ink-700 rounded-lg bg-ink-800/40 p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <SeverityBadge severity={selected.severity} />
                    <span className="font-mono text-[10px] text-slate-600">Contradiction #{selected.id}</span>
                    {selected.source_doc && (
                      <span className="font-mono text-[9px] text-slate-600 ml-auto">{selected.source_doc}</span>
                    )}
                  </div>
                  <div className="space-y-2">
                    <div>
                      <p className="font-mono text-[9px] text-slate-500 tracking-widest mb-1">STATEMENT A (SWORN)</p>
                      <p className="font-mono text-[11px] text-slate-300 leading-relaxed">{selected.claim}</p>
                    </div>
                    {selected.evidence && (
                      <div>
                        <p className="font-mono text-[9px] text-slate-500 tracking-widest mb-1 mt-3">STATEMENT B (CONTRADICTING)</p>
                        <p className="font-mono text-[11px] text-red-300/80 leading-relaxed">{selected.evidence}</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Questions section */}
                <div className="border border-ink-700 rounded-lg bg-ink-800/40 p-4">
                  <div className="flex items-center justify-between mb-3">
                    <p className="font-mono text-[10px] text-slate-500 tracking-widest uppercase">
                      Cross-Examination Questions
                    </p>
                    {questions && (
                      <button
                        onClick={handleGenerate}
                        disabled={loading}
                        className="font-mono text-[9px] text-slate-400 border border-slate-600 px-2 py-1 rounded tracking-widest hover:text-slate-200 hover:border-slate-400 transition-colors disabled:opacity-40"
                      >
                        {loading ? 'GENERATING…' : 'REGENERATE'}
                      </button>
                    )}
                  </div>

                  {error && (
                    <p className="font-mono text-[10px] text-red-400 mb-3">{error}</p>
                  )}

                  {loading ? (
                    <div className="flex items-center gap-2 py-8">
                      <div className="w-2 h-2 bg-sky-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-2 h-2 bg-sky-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-2 h-2 bg-sky-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                      <span className="font-mono text-[10px] text-slate-500 ml-2">Generating questions via Claude…</span>
                    </div>
                  ) : questions ? (
                    <div>
                      <pre className="font-mono text-[11px] text-slate-200 leading-relaxed whitespace-pre-wrap break-words">
                        {questions.questions_text}
                      </pre>
                      <p className="font-mono text-[9px] text-slate-600 mt-4">
                        Generated {new Date(questions.generated_at).toLocaleString()} · {questions.model_used}
                      </p>
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <p className="font-mono text-[10px] text-slate-600 mb-4">No questions generated yet for this contradiction.</p>
                      <button
                        onClick={handleGenerate}
                        disabled={loading}
                        className="font-mono text-[10px] text-sky-400 border border-sky-500/40 px-4 py-2 rounded tracking-widest hover:text-sky-300 hover:border-sky-400/60 transition-colors disabled:opacity-40"
                      >
                        GENERATE QUESTIONS
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
