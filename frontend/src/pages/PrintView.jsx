import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

const TRIAL_DATE = new Date('2026-05-19')
const TODAY = new Date()
const DAYS_TO_TRIAL = Math.ceil((TRIAL_DATE - TODAY) / (1000 * 60 * 60 * 24))

const SEVERITY_ORDER = { critical: 0, high: 1, medium: 2, low: 3 }

export default function PrintView() {
  const [summary, setSummary] = useState(null)
  const [events, setEvents] = useState([])
  const [crossExamMap, setCrossExamMap] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const load = async () => {
      try {
        const [summaryRes, eventsRes] = await Promise.all([
          fetch('/api/export/trial-summary'),
          fetch('/api/timeline/events'),
        ])
        if (!summaryRes.ok) throw new Error(`trial-summary: HTTP ${summaryRes.status}`)
        const summaryData = await summaryRes.json()
        setSummary(summaryData)

        if (eventsRes.ok) {
          const evData = await eventsRes.json()
          setEvents(Array.isArray(evData) ? evData : (evData.events || []))
        }

        // Fetch cross-exam questions for each contradiction in parallel
        const contras = summaryData.contradictions || []
        const results = await Promise.allSettled(
          contras.map(c => fetch(`/api/crossexam/${c.id}`).then(r => r.ok ? r.json() : null))
        )
        const map = {}
        results.forEach((r, i) => {
          if (r.status === 'fulfilled' && r.value?.questions_text) {
            map[contras[i].id] = r.value.questions_text
          }
        })
        setCrossExamMap(map)
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <p className="font-mono text-sm text-slate-500 tracking-widest animate-pulse">LOADING COURT SUMMARY...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <p className="font-mono text-sm text-red-500">Error: {error}</p>
      </div>
    )
  }

  const contradictions = [...(summary?.contradictions || [])]
    .sort((a, b) => (SEVERITY_ORDER[a.severity] ?? 3) - (SEVERITY_ORDER[b.severity] ?? 3))

  const stats = summary?.stats || {}

  return (
    <div className="bg-white text-black min-h-screen font-mono text-sm">
      <style>{`
        @media print {
          .no-print { display: none !important; }
          body { background: white !important; color: black !important; }
          .print-section { page-break-before: always; }
          .print-avoid-break { page-break-inside: avoid; }
        }
        @media screen {
          body { background: #f8f9fa; }
        }
      `}</style>

      {/* Print / Nav controls — hidden on print */}
      <div className="no-print bg-slate-800 text-white px-6 py-3 flex items-center gap-4 sticky top-0 z-10">
        <Link to="/trial" className="text-[10px] font-mono text-slate-400 hover:text-white tracking-widest">← BACK</Link>
        <span className="text-[10px] text-slate-500 tracking-widest flex-1">PRINT VIEW — PC 19700</span>
        <button
          onClick={() => window.print()}
          className="text-[10px] font-mono bg-amber-500 text-black px-4 py-1.5 rounded tracking-widest hover:bg-amber-400 transition-colors"
        >
          PRINT / SAVE PDF
        </button>
      </div>

      <div className="max-w-4xl mx-auto px-8 py-10">

        {/* ── Header ── */}
        <div className="border-b-2 border-black pb-6 mb-8">
          <h1 className="text-2xl font-bold tracking-tight uppercase">
            EVIDENCE SUMMARY
          </h1>
          <p className="text-lg tracking-wide mt-1">PC 19700 | C.L. v MCFD Director</p>
          <div className="flex gap-8 mt-3 text-xs text-slate-600">
            <span>Generated: {TODAY.toISOString().split('T')[0]}</span>
            <span>Days to Trial: <strong className="text-black">{DAYS_TO_TRIAL}</strong></span>
            <span>Trial: May 19–21, 2026</span>
          </div>
        </div>

        {/* ── Section 1: Stats ── */}
        <div className="mb-10 print-avoid-break">
          <h2 className="text-base font-bold uppercase tracking-widest border-b border-slate-300 pb-1 mb-4">
            1. Summary Statistics
          </h2>
          <table className="w-full text-xs border-collapse">
            <tbody>
              {Object.entries(stats).map(([k, v]) => (
                <tr key={k} className="border-b border-slate-200">
                  <td className="py-1.5 pr-6 text-slate-600 capitalize">{k.replace(/_/g, ' ')}</td>
                  <td className="py-1.5 font-bold">{String(v)}</td>
                </tr>
              ))}
              <tr className="border-b border-slate-200">
                <td className="py-1.5 pr-6 text-slate-600">Total Contradictions</td>
                <td className="py-1.5 font-bold">{contradictions.length}</td>
              </tr>
              <tr className="border-b border-slate-200">
                <td className="py-1.5 pr-6 text-slate-600">Cross-Exam Sets Generated</td>
                <td className="py-1.5 font-bold">{Object.keys(crossExamMap).length} / {contradictions.length}</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* ── Section 2: Contradictions ── */}
        <div className="print-section">
          <h2 className="text-base font-bold uppercase tracking-widest border-b border-slate-300 pb-1 mb-6">
            2. Contradictions ({contradictions.length})
          </h2>
          <div className="space-y-10">
            {contradictions.map((c, idx) => {
              const questions = crossExamMap[c.id]
              const topChunks = (summary?.foi_chunks || [])
                .filter(ch => (ch.citation || ch.title || '').toLowerCase().includes((c.source_doc || '').toLowerCase()))
                .slice(0, 3)

              return (
                <div key={c.id} className="print-avoid-break border border-slate-300 p-5">
                  <div className="flex items-start gap-3 mb-3">
                    <span className="text-xs font-bold text-slate-500">#{idx + 1}</span>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className={`text-[10px] px-1.5 py-0.5 border font-bold uppercase tracking-widest ${
                          c.severity === 'critical' ? 'border-red-600 text-red-700' :
                          c.severity === 'high'     ? 'border-orange-500 text-orange-600' :
                          c.severity === 'medium'   ? 'border-yellow-500 text-yellow-600' :
                                                       'border-slate-400 text-slate-500'
                        }`}>
                          {c.severity}
                        </span>
                        {c.source_doc && <span className="text-[10px] text-slate-500">{c.source_doc}</span>}
                      </div>
                      <p className="text-xs font-bold mb-1">{c.claim || c.statement_a || `Contradiction #${c.id}`}</p>
                      {c.statement_a && c.statement_b && (
                        <div className="grid grid-cols-2 gap-3 mt-2 text-xs">
                          <div className="border-l-2 border-slate-400 pl-2">
                            <p className="text-[9px] uppercase text-slate-500 mb-0.5">Statement A</p>
                            <p className="text-slate-700 leading-snug">{c.statement_a}</p>
                          </div>
                          <div className="border-l-2 border-red-400 pl-2">
                            <p className="text-[9px] uppercase text-slate-500 mb-0.5">Statement B</p>
                            <p className="text-slate-700 leading-snug">{c.statement_b}</p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* FOI Evidence */}
                  {topChunks.length > 0 && (
                    <div className="mt-3 pl-5 border-t border-slate-200 pt-3">
                      <p className="text-[9px] uppercase text-slate-500 mb-2 tracking-widest">FOI Evidence</p>
                      {topChunks.map((ch, i) => (
                        <div key={i} className="mb-2 text-xs text-slate-700 leading-snug">
                          <span className="font-bold text-[9px] text-slate-500">[{ch.source?.toUpperCase()}] </span>
                          {ch.text?.slice(0, 300)}{ch.text?.length > 300 ? '…' : ''}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Cross-Exam Questions */}
                  <div className="mt-3 pl-5 border-t border-slate-200 pt-3">
                    <p className="text-[9px] uppercase text-slate-500 mb-2 tracking-widest">Cross-Examination Questions</p>
                    {questions ? (
                      <pre className="text-xs text-slate-800 whitespace-pre-wrap leading-relaxed font-mono">{questions}</pre>
                    ) : (
                      <p className="text-xs text-slate-400 italic">Questions not yet generated.</p>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* ── Section 3: Timeline ── */}
        {events.length > 0 && (
          <div className="print-section mt-12">
            <h2 className="text-base font-bold uppercase tracking-widest border-b border-slate-300 pb-1 mb-6">
              3. Case Timeline ({events.length} events)
            </h2>
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="border-b-2 border-black">
                  <th className="text-left py-1.5 pr-4 w-24">Date</th>
                  <th className="text-left py-1.5 pr-4 w-20">Category</th>
                  <th className="text-left py-1.5 pr-3 w-16">Severity</th>
                  <th className="text-left py-1.5">Event</th>
                </tr>
              </thead>
              <tbody>
                {events.map((e, i) => (
                  <tr key={i} className="border-b border-slate-200 print-avoid-break">
                    <td className="py-1.5 pr-4 text-slate-600 align-top">{e.date || ''}</td>
                    <td className="py-1.5 pr-4 text-slate-600 align-top capitalize">{e.category || ''}</td>
                    <td className="py-1.5 pr-3 align-top">
                      {e.severity && (
                        <span className={`text-[9px] font-bold uppercase ${
                          e.severity === 'critical' ? 'text-red-600' :
                          e.severity === 'high'     ? 'text-orange-500' :
                          e.severity === 'medium'   ? 'text-yellow-600' : 'text-slate-400'
                        }`}>{e.severity}</span>
                      )}
                    </td>
                    <td className="py-1.5 align-top">
                      <p className="font-bold">{e.title}</p>
                      {e.description && <p className="text-slate-600 mt-0.5 leading-snug">{e.description}</p>}
                      {e.source_ref && <p className="text-[9px] text-slate-400 mt-0.5">{e.source_ref}</p>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* ── Footer ── */}
        <div className="mt-16 pt-6 border-t-2 border-black text-center text-xs text-slate-500">
          <p className="font-bold tracking-widest uppercase">The MCFD Files | Pro Patria</p>
          <p className="mt-1">PC 19700 · SC 64242 · SC 064851 · Trial May 19–21, 2026</p>
          <p className="mt-1 text-[10px]">CONFIDENTIAL — PREPARED FOR COURT USE</p>
        </div>

      </div>
    </div>
  )
}
