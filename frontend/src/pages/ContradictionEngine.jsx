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

function exportTxt(contradictions) {
  if (!contradictions.length) return
  const lines = contradictions.map((c, i) =>
    `[${i + 1}] SEVERITY: ${c.severity || 'NONE'}\nCLAIM: ${c.claim}\nEVIDENCE: ${c.evidence || '—'}\nSOURCE: ${c.source_doc || '—'} ${c.page_ref ? `(${c.page_ref})` : ''}\n`
  )
  const blob = new Blob(['CONTRADICTION REPORT\n\n' + lines.join('\n---\n\n')], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'contradiction_report.txt'
  a.click()
  URL.revokeObjectURL(url)
}

export default function ContradictionEngine() {
  const [claim, setClaim] = useState('')
  const [sourceFilter, setSourceFilter] = useState('personal')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)
  const [history, setHistory] = useState([])

  // Load history on mount
  useEffect(() => {
    fetch('/api/contradictions')
      .then(r => r.json())
      .catch(() => [])
      .then(data => setHistory(Array.isArray(data) ? data : []))
  }, [])

  async function handleAnalyze(e) {
    e.preventDefault()
    if (!claim.trim()) return
    setLoading(true)
    setError(null)
    setResults(null)
    try {
      const res = await fetch('/api/contradictions/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ claim: claim.trim(), source_filter: sourceFilter }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Request failed')
      setResults(data.contradictions || [])
      // Refresh history
      fetch('/api/contradictions')
        .then(r => r.json())
        .catch(() => [])
        .then(d => setHistory(Array.isArray(d) ? d : []))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-ink-900 font-sans text-slate-200">
      <div className="h-px bg-gradient-to-r from-transparent via-amber-500/60 to-transparent" />
      <div className="max-w-4xl mx-auto px-4 pt-3"><TrialBanner /></div>

      <header className="sticky top-0 z-20 border-b border-ink-600 bg-ink-900/90 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-4">
          <Link to="/" className="font-mono text-[10px] text-slate-500 hover:text-slate-300 tracking-widest transition-colors">
            ← BACK
          </Link>
          <h1 className="font-display text-xl tracking-[0.12em] text-white">CONTRADICTION ENGINE</h1>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-8">

        {/* Input form */}
        <form onSubmit={handleAnalyze} className="space-y-3">
          <label className="font-mono text-[10px] text-slate-500 tracking-widest uppercase block">
            Sworn Statement Claim
          </label>
          <textarea
            value={claim}
            onChange={e => setClaim(e.target.value)}
            placeholder="Enter sworn statement claim to analyze for contradictions..."
            rows={4}
            className="w-full bg-ink-800 border border-ink-600 rounded px-3 py-2 text-sm text-slate-200 placeholder-slate-600 resize-none focus:outline-none focus:border-amber-500/50"
          />

          <div className="flex items-center gap-3">
            {/* Source filter toggle */}
            <div className="flex rounded border border-ink-500 overflow-hidden flex-shrink-0">
              {[
                { id: 'personal', label: 'MY FILES' },
                { id: 'all', label: 'ALL DOCS' },
              ].map(({ id, label }) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setSourceFilter(id)}
                  className={`font-mono text-[10px] tracking-widest px-2 py-1.5 transition-colors border-r last:border-r-0 border-ink-500 ${
                    sourceFilter === id
                      ? 'bg-violet-900/60 text-violet-400'
                      : 'bg-ink-700 text-slate-600 hover:text-slate-400'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            <button
              type="submit"
              disabled={loading || !claim.trim()}
              className="font-mono text-[10px] tracking-widest px-4 py-1.5 rounded bg-amber-500/15 text-amber-400 border border-amber-500/30 hover:bg-amber-500/25 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {loading ? 'ANALYZING...' : 'ANALYZE'}
            </button>
          </div>
        </form>

        {/* Error */}
        {error && (
          <div className="font-mono text-xs text-red-400 border border-red-500/30 bg-red-900/10 rounded px-3 py-2">
            ERROR: {error}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="py-8 text-center font-mono text-xs text-slate-500 tracking-widest animate-pulse">
            ANALYZING CLAIM AGAINST DOCUMENTS...
          </div>
        )}

        {/* Results */}
        {results !== null && !loading && (
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-mono text-[10px] text-slate-500 tracking-widest uppercase">
                Results — {results.length} contradiction{results.length !== 1 ? 's' : ''} found
              </h2>
              {results.length > 0 && (
                <button
                  onClick={() => exportTxt(results)}
                  className="font-mono text-[10px] tracking-widest px-2 py-1 rounded border border-slate-600 text-slate-500 hover:text-slate-300 hover:border-slate-400 transition-colors"
                >
                  EXPORT TXT
                </button>
              )}
            </div>

            {results.length === 0 ? (
              <div className="py-8 text-center font-mono text-xs text-slate-600">
                No contradictions found in the analyzed documents.
              </div>
            ) : (
              <div className="space-y-3">
                {results.map((c, i) => (
                  <div key={i} className="bg-ink-800 border border-ink-600 rounded-lg p-4 space-y-2">
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-sm text-slate-300 leading-relaxed flex-1">{c.claim}</p>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <SeverityBadge severity={c.severity} />
                        <button
                          onClick={() => navigator.clipboard.writeText(
                            `CLAIM: ${c.claim}\nEVIDENCE: ${c.evidence || '—'}\nSOURCE: ${c.source_doc || '—'}\nSEVERITY: ${c.severity}`
                          )}
                          className="font-mono text-[9px] text-ink-400 border border-ink-600 px-1.5 py-0.5 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors"
                        >
                          COPY
                        </button>
                      </div>
                    </div>
                    {c.evidence && (
                      <div className="border-l-2 border-ink-500 pl-3">
                        <p className="font-mono text-[10px] text-slate-600 tracking-widest mb-1">EVIDENCE</p>
                        <p className="text-xs text-slate-400 leading-relaxed">{c.evidence}</p>
                      </div>
                    )}
                    {(c.source_doc || c.page_ref) && (
                      <p className="font-mono text-[10px] text-slate-600 tracking-widest">
                        {c.source_doc}{c.page_ref ? ` · ${c.page_ref}` : ''}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* History */}
        {history.length > 0 && (
          <section>
            <h2 className="font-mono text-[10px] text-slate-600 tracking-widest uppercase mb-3">
              Previous Runs ({history.length})
            </h2>
            <div className="space-y-2">
              {history.slice(0, 20).map(c => (
                <div key={c.id} className="flex items-start gap-3 bg-ink-800/50 border border-ink-700 rounded px-3 py-2">
                  <SeverityBadge severity={c.severity} />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-slate-400 truncate">{c.claim}</p>
                    {c.source_doc && (
                      <p className="font-mono text-[10px] text-slate-600 mt-0.5 truncate">{c.source_doc}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      onClick={() => navigator.clipboard.writeText(
                        `CLAIM: ${c.claim}\nEVIDENCE: ${c.evidence || '—'}\nSOURCE: ${c.source_doc || '—'}\nSEVERITY: ${c.severity}`
                      )}
                      className="font-mono text-[9px] text-ink-400 border border-ink-600 px-1.5 py-0.5 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors"
                    >
                      COPY
                    </button>
                    <span className="font-mono text-[10px] text-slate-700">
                      {c.created_at?.slice(0, 10)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  )
}
