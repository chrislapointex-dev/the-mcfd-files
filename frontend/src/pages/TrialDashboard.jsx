import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import TrialBanner from '../components/TrialBanner'

const SEVERITY_COLORS = {
  DIRECT:  'text-red-400 border-red-500/40 bg-red-900/20',
  PARTIAL: 'text-amber-400 border-amber-500/40 bg-amber-900/20',
  NONE:    'text-slate-500 border-slate-600 bg-ink-800',
}

export default function TrialDashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [checklistPending, setChecklistPending] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    fetch('/api/trialprep/summary')
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))

    fetch('/api/checklist')
      .then(r => r.ok ? r.json() : {})
      .then(grouped => {
        const all = Object.values(grouped).flat()
        setChecklistPending(all.filter(i => !i.done).length)
      })
      .catch(() => {})
  }, [])

  const countdownColor = (days) => {
    if (days < 30) return 'text-red-400'
    if (days < 60) return 'text-amber-400'
    return 'text-emerald-400'
  }

  return (
    <div className="min-h-screen bg-ink-900 font-sans text-slate-200">
      {/* Top accent line */}
      <div className="h-px bg-gradient-to-r from-transparent via-red-500/60 to-transparent" />
      <div className="max-w-5xl mx-auto px-4 pt-3 print:hidden"><TrialBanner /></div>

      {/* Header */}
      <header className="sticky top-0 z-20 border-b border-ink-600 bg-ink-900/90 backdrop-blur-sm print:hidden">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
          <div>
            <h1 className="font-display text-3xl tracking-[0.12em] text-white leading-none">
              THE MCFD FILES
            </h1>
            <p className="font-mono text-[10px] text-slate-600 tracking-widest mt-1 uppercase">
              Trial Prep Dashboard · May 19–21, 2026
            </p>
          </div>
          <nav className="flex items-center gap-2 flex-wrap justify-end">
            <Link to="/trial" className="text-[10px] font-mono text-red-400 border border-red-500/40 px-2 py-1 rounded tracking-widest hidden sm:block">TRIAL</Link>
            <Link to="/search" className="text-[10px] font-mono text-slate-500 border border-slate-700 px-2 py-1 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors hidden sm:block">SEARCH</Link>
            <Link to="/witnesses" className="text-[10px] font-mono text-slate-500 border border-slate-700 px-2 py-1 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors hidden sm:block">WITNESSES</Link>
            <Link to="/contradictions" className="text-[10px] font-mono text-slate-500 border border-slate-700 px-2 py-1 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors hidden sm:block">CONTRADICTIONS</Link>
            <Link to="/timeline" className="text-[10px] font-mono text-slate-500 border border-slate-700 px-2 py-1 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors hidden sm:block">TIMELINE</Link>
            <Link to="/patterns" className="text-[10px] font-mono text-slate-500 border border-slate-700 px-2 py-1 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors hidden sm:block">PATTERNS</Link>
            <Link to="/checklist" className="text-[10px] font-mono text-slate-500 border border-slate-700 px-2 py-1 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors hidden sm:block">
              CHECKLIST{checklistPending !== null && checklistPending > 0 ? ` (${checklistPending})` : ''}
            </Link>
            <Link to="/complaints" className="text-[10px] font-mono text-slate-500 border border-slate-700 px-2 py-1 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors hidden sm:block">COMPLAINTS</Link>
            <span className="text-[10px] font-mono text-amber-500/60 border border-amber-500/25 px-2 py-1 rounded tracking-widest hidden sm:block">UNREDACTED</span>
          </nav>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8">
        {loading && (
          <div className="py-24 text-center font-mono text-xs text-slate-600 tracking-widest animate-pulse">
            LOADING TRIAL DATA...
          </div>
        )}

        {error && (
          <div className="py-24 text-center font-mono text-sm text-red-400">
            Error loading trial summary: {error}
          </div>
        )}

        {data && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

            {/* ── LEFT COLUMN ── */}
            <div className="space-y-5">

              {/* Countdown */}
              <div className="border border-ink-600 bg-ink-800 rounded-lg p-6">
                <p className="font-mono text-[10px] text-slate-600 tracking-widest mb-2 uppercase">Days to Trial</p>
                <p className={`font-display text-6xl sm:text-8xl font-bold tracking-tight leading-none ${countdownColor(data.days_remaining)}`}>
                  {data.days_remaining}
                </p>
                <p className="font-mono text-xs text-slate-500 mt-3 tracking-widest">MAY 19–21, 2026</p>
              </div>

              {/* Case info */}
              <div className="border border-ink-600 bg-ink-800 rounded-lg p-5 space-y-3">
                <p className="font-mono text-[10px] text-slate-600 tracking-widest uppercase">Case Numbers</p>
                {['PC 19700', 'PC 19709', 'SC 64242', 'SC 064851'].map(cn => (
                  <div key={cn} className="font-mono text-sm text-slate-300 tracking-wider">{cn}</div>
                ))}
              </div>

              {/* Stats row */}
              <div className="grid grid-cols-2 gap-3">
                <div className="border border-ink-600 bg-ink-800 rounded-lg p-4 text-center">
                  <p className="font-display text-3xl text-amber-400">{data.contradiction_count}</p>
                  <p className="font-mono text-[10px] text-slate-600 tracking-widest mt-1 uppercase">Contradictions</p>
                </div>
                <div className="border border-ink-600 bg-ink-800 rounded-lg p-4 text-center">
                  <p className="font-display text-3xl text-violet-400">{data.personal_chunks.toLocaleString()}</p>
                  <p className="font-mono text-[10px] text-slate-600 tracking-widest mt-1 uppercase">Personal Chunks</p>
                </div>
              </div>

              {/* Key witnesses */}
              <div className="border border-ink-600 bg-ink-800 rounded-lg p-5">
                <p className="font-mono text-[10px] text-slate-600 tracking-widest uppercase mb-4">Key Witnesses</p>
                <div className="space-y-2">
                  {data.key_witnesses.map(name => (
                    <div key={name} className="flex items-center justify-between gap-3">
                      <span className="font-mono text-xs text-slate-300">{name}</span>
                      <button
                        onClick={() => navigate(`/search?ask=What does the FOI say about ${encodeURIComponent(name)}`)}
                        className="font-mono text-[10px] text-sky-400 border border-sky-500/30 px-2 py-0.5 rounded tracking-widest hover:bg-sky-900/20 transition-colors flex-shrink-0"
                      >
                        SEARCH
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* ── RIGHT COLUMN ── */}
            <div className="space-y-5">

              {/* Top contradictions */}
              <div className="border border-ink-600 bg-ink-800 rounded-lg p-5">
                <div className="flex items-center justify-between mb-4">
                  <p className="font-mono text-[10px] text-slate-600 tracking-widest uppercase">Top Contradictions</p>
                  <Link to="/contradictions" className="font-mono text-[10px] text-amber-500 hover:text-amber-400 tracking-widest transition-colors">
                    VIEW ALL →
                  </Link>
                </div>
                {data.top_contradictions.length === 0 ? (
                  <p className="font-mono text-xs text-slate-600">No contradictions yet. Use the Contradiction Engine.</p>
                ) : (
                  <div className="space-y-3">
                    {data.top_contradictions.map(c => (
                      <div key={c.id} className="border border-ink-700 rounded p-3 space-y-1.5">
                        <div className="flex items-start gap-2">
                          <span className={`font-mono text-[9px] px-1.5 py-0.5 rounded border tracking-widest flex-shrink-0 ${SEVERITY_COLORS[c.severity] ?? SEVERITY_COLORS.NONE}`}>
                            {c.severity || 'NONE'}
                          </span>
                          <p className="font-mono text-[10px] text-slate-400 leading-relaxed line-clamp-2">
                            {c.claim}
                          </p>
                        </div>
                        {c.source_doc && (
                          <p className="font-mono text-[9px] text-slate-600 pl-8">
                            {c.source_doc}{c.page_ref ? ` · p.${c.page_ref}` : ''}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Timeline gaps */}
              <div className="border border-ink-600 bg-ink-800 rounded-lg p-5">
                <div className="flex items-center justify-between mb-4">
                  <p className="font-mono text-[10px] text-slate-600 tracking-widest uppercase">Timeline Gaps</p>
                  <span className="font-mono text-[9px] text-slate-600">Aug 7 – Sep 8, 2025</span>
                </div>
                {data.timeline_gaps.length === 0 ? (
                  <p className="font-mono text-xs text-slate-600">No gaps &gt; 3 days in critical period.</p>
                ) : (
                  <div className="space-y-2">
                    {data.timeline_gaps.map((gap, i) => (
                      <div key={i} className="flex items-center justify-between border border-red-900/30 bg-red-900/10 rounded px-3 py-2">
                        <div className="font-mono text-[10px] text-red-300">
                          {gap.start} → {gap.end}
                        </div>
                        <div className="font-mono text-[10px] text-red-400 font-bold">
                          {gap.days}d
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                <Link to="/timeline" className="mt-3 block font-mono text-[10px] text-slate-600 hover:text-slate-400 tracking-widest transition-colors">
                  FULL TIMELINE →
                </Link>
              </div>

              {/* Export button */}
              <div className="border border-ink-600 bg-ink-800 rounded-lg p-5">
                <p className="font-mono text-[10px] text-slate-600 tracking-widest uppercase mb-3">Export</p>
                <button
                  onClick={() => { window.location = '/api/export/trial-package' }}
                  className="w-full font-mono text-xs tracking-widest px-4 py-3 rounded border border-amber-500/40 text-amber-400 bg-amber-900/10 hover:bg-amber-900/20 hover:border-amber-500/60 transition-colors"
                >
                  EXPORT TRIAL PACKAGE
                </button>
                <button
                  onClick={async () => {
                    const data = await fetch('/api/export/trial-summary').then(r => r.json());
                    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `trial_summary_${new Date().toISOString().slice(0,10)}.json`;
                    a.click();
                    URL.revokeObjectURL(url);
                  }}
                  className="w-full font-mono text-xs tracking-widest px-4 py-3 rounded border border-amber-500/40 text-amber-400 bg-amber-900/10 hover:bg-amber-900/20 hover:border-amber-500/60 transition-colors mt-2"
                >
                  EXPORT TRIAL SUMMARY (JSON)
                </button>
                <button
                  onClick={() => window.print()}
                  className="w-full font-mono text-xs tracking-widest px-4 py-3 rounded border border-slate-600 text-slate-400 bg-ink-900/20 hover:bg-ink-700 hover:border-slate-500 transition-colors mt-2 print:hidden"
                >
                  PRINT TRIAL SUMMARY
                </button>
                <p className="font-mono text-[9px] text-slate-700 mt-2 text-center tracking-wide">
                  Downloads ZIP with contradictions, timeline, witness profiles
                </p>
              </div>

            </div>
          </div>
        )}
      </main>

      <footer className="border-t border-ink-600 mt-20 py-8">
        <div className="max-w-5xl mx-auto px-4 text-center">
          <p className="font-mono text-[10px] text-slate-700 uppercase tracking-widest">
            The MCFD Files · Trial Prep · May 19–21, 2026
          </p>
        </div>
      </footer>
    </div>
  )
}
