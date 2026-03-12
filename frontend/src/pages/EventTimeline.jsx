import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

const SEVERITY_DOT = {
  critical: 'bg-red-600',
  high:     'bg-amber-500',
  medium:   'bg-blue-500',
  low:      'bg-slate-400',
}

const SEVERITY_BORDER = {
  critical: 'border-red-600/50',
  high:     'border-amber-500/50',
  medium:   'border-blue-500/50',
  low:      'border-slate-600',
}

const SEVERITY_LABEL = {
  critical: 'text-red-400',
  high:     'text-amber-400',
  medium:   'text-blue-400',
  low:      'text-slate-400',
}

const CATEGORY_STYLE = {
  mcfd_action:   'text-red-400 border-red-500/40',
  complaint:     'text-amber-400 border-amber-500/40',
  legal_filing:  'text-blue-400 border-blue-500/40',
  evidence:      'text-green-400 border-green-500/40',
  personal:      'text-slate-400 border-slate-500/40',
}

const CATEGORY_LABEL = {
  mcfd_action:  'MCFD ACTION',
  complaint:    'COMPLAINT',
  legal_filing: 'LEGAL FILING',
  evidence:     'EVIDENCE',
  personal:     'PERSONAL',
}

function CategoryBadge({ category }) {
  const cls = CATEGORY_STYLE[category] || 'text-slate-400 border-slate-500/40'
  return (
    <span className={`font-mono text-[9px] tracking-widest border rounded px-1.5 py-0.5 ${cls}`}>
      {CATEGORY_LABEL[category] || (category || 'OTHER').toUpperCase()}
    </span>
  )
}

export default function EventTimeline() {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [expanded, setExpanded] = useState({})

  useEffect(() => {
    fetch('/api/timeline/events')
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(data => setEvents(Array.isArray(data) ? data : []))
      .catch(() => setError('Failed to load timeline events'))
      .finally(() => setLoading(false))
  }, [])

  function toggle(id) {
    setExpanded(prev => ({ ...prev, [id]: !prev[id] }))
  }

  return (
    <div className="min-h-screen bg-ink-900 font-sans text-slate-200">
      <div className="h-px bg-gradient-to-r from-transparent via-red-600/60 to-transparent" />

      <header className="sticky top-0 z-20 border-b border-ink-600 bg-ink-900/90 backdrop-blur-sm">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center gap-4 flex-wrap">
          <Link
            to="/"
            className="font-mono text-[10px] text-slate-500 hover:text-slate-300 tracking-widest transition-colors"
          >
            ← BACK
          </Link>
          <h1 className="font-display text-xl tracking-[0.12em] text-white">EVENT TIMELINE</h1>
          <span className="font-mono text-[10px] text-red-400/70 tracking-widest ml-auto">
            COORDINATION · REMOVAL · FILING
          </span>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8">
        {loading && (
          <div className="py-24 text-center font-mono text-xs text-slate-600 tracking-widest animate-pulse">
            LOADING TIMELINE...
          </div>
        )}

        {error && (
          <div className="font-mono text-xs text-red-400 border border-red-500/30 bg-red-900/10 rounded px-3 py-2">
            {error}
          </div>
        )}

        {!loading && !error && (
          <>
            <p className="font-mono text-[10px] text-slate-600 tracking-widest mb-8">
              {events.length} KEY EVENT{events.length !== 1 ? 'S' : ''} · CHRONOLOGICAL ORDER
            </p>

            <div className="relative">
              {/* Vertical spine */}
              <div className="absolute left-[7px] top-2 bottom-2 w-px bg-ink-700" />

              <div className="space-y-0">
                {events.map((ev, i) => {
                  const isTrialDate = ev.event_date === '2026-05-19'
                  const dotCls = SEVERITY_DOT[ev.severity] || 'bg-slate-500'
                  const borderCls = SEVERITY_BORDER[ev.severity] || 'border-slate-600'
                  const labelCls = SEVERITY_LABEL[ev.severity] || 'text-slate-400'
                  const isOpen = !!expanded[ev.id]

                  return (
                    <div key={ev.id} className="flex gap-5 pb-8">
                      {/* Dot */}
                      <div className="flex flex-col items-center flex-shrink-0 pt-1">
                        <div
                          className={`w-4 h-4 rounded-full flex-shrink-0 z-10 border-2 border-ink-900 ${dotCls} ${isTrialDate ? 'ring-2 ring-red-500/50 ring-offset-1 ring-offset-ink-900' : ''}`}
                        />
                      </div>

                      {/* Card */}
                      <div className={`flex-1 min-w-0 border rounded-lg px-4 py-3 ${borderCls} ${isTrialDate ? 'bg-red-950/20 animate-pulse-slow' : 'bg-ink-800/50'}`}>
                        {/* Date + severity + category row */}
                        <div className="flex items-center gap-2 flex-wrap mb-1.5">
                          <span className="font-mono text-[11px] text-slate-400 tracking-widest">
                            {ev.event_date}
                          </span>
                          <span className={`font-mono text-[9px] tracking-widest font-bold ${labelCls}`}>
                            {(ev.severity || '').toUpperCase()}
                          </span>
                          <CategoryBadge category={ev.category} />
                        </div>

                        {/* Title */}
                        <h3 className={`font-mono text-sm font-bold tracking-wide mb-1.5 ${isTrialDate ? 'text-red-300' : 'text-white'}`}>
                          {ev.title}
                        </h3>

                        {/* Description — toggle */}
                        {ev.description && (
                          <button
                            onClick={() => toggle(ev.id)}
                            className="text-left w-full"
                          >
                            <p className={`text-xs leading-relaxed text-slate-400 ${isOpen ? '' : 'line-clamp-2'}`}>
                              {ev.description}
                            </p>
                            {ev.description.length > 120 && (
                              <span className="font-mono text-[9px] text-slate-600 hover:text-slate-400 tracking-widest mt-1 inline-block transition-colors">
                                {isOpen ? 'COLLAPSE ▲' : 'EXPAND ▼'}
                              </span>
                            )}
                          </button>
                        )}

                        {/* Source ref */}
                        {ev.source_ref && (
                          <div className="mt-2">
                            <span className="font-mono text-[9px] text-slate-600 tracking-widest">
                              SOURCE: {ev.source_ref}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  )
}
