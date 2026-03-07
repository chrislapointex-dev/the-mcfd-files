import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

const SOURCE_STYLE = {
  foi: 'text-violet-400 border-violet-500/40',
  personal: 'text-teal-400 border-teal-500/40',
}

function SourceBadge({ source }) {
  const cls = SOURCE_STYLE[source] || 'text-slate-400 border-slate-500/40'
  return (
    <span className={`font-mono text-[10px] tracking-widest border rounded px-1.5 py-0.5 ${cls}`}>
      {(source || 'doc').toUpperCase()}
    </span>
  )
}

function EventModal({ event, onClose }) {
  if (!event) return null
  return (
    <div
      className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-ink-800 border border-ink-600 rounded-lg max-w-xl w-full p-5 space-y-3"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <SourceBadge source={event.source} />
          <button onClick={onClose} className="font-mono text-[10px] text-slate-600 hover:text-slate-300 tracking-widest">
            CLOSE
          </button>
        </div>
        {event.citation && (
          <p className="font-mono text-[10px] text-slate-500 tracking-widest">{event.citation}</p>
        )}
        <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">{event.text}</p>
      </div>
    </div>
  )
}

export default function CaseTimeline() {
  const [timeline, setTimeline] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [modal, setModal] = useState(null)

  useEffect(() => {
    fetch('/api/timeline')
      .then(r => r.json())
      .then(data => setTimeline(data.timeline || []))
      .catch(() => setError('Failed to load timeline'))
      .finally(() => setLoading(false))
  }, [])

  // Client-side date filter
  const filtered = timeline.filter(entry => {
    if (dateFrom && entry.date < dateFrom) return false
    if (dateTo && entry.date > dateTo) return false
    return true
  })

  return (
    <div className="min-h-screen bg-ink-900 font-sans text-slate-200">
      <div className="h-px bg-gradient-to-r from-transparent via-amber-500/60 to-transparent" />

      <header className="sticky top-0 z-20 border-b border-ink-600 bg-ink-900/90 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-4 flex-wrap">
          <Link to="/" className="font-mono text-[10px] text-slate-500 hover:text-slate-300 tracking-widest transition-colors">
            ← BACK
          </Link>
          <h1 className="font-display text-xl tracking-[0.12em] text-white">CASE TIMELINE</h1>

          {/* Date range filter */}
          <div className="flex items-center gap-2 ml-auto">
            <label className="font-mono text-[10px] text-slate-600 tracking-widest">FROM</label>
            <input
              type="date"
              value={dateFrom}
              onChange={e => setDateFrom(e.target.value)}
              className="bg-ink-800 border border-ink-600 rounded px-2 py-1 text-xs text-slate-300 font-mono focus:outline-none focus:border-amber-500/50"
            />
            <label className="font-mono text-[10px] text-slate-600 tracking-widest">TO</label>
            <input
              type="date"
              value={dateTo}
              onChange={e => setDateTo(e.target.value)}
              className="bg-ink-800 border border-ink-600 rounded px-2 py-1 text-xs text-slate-300 font-mono focus:outline-none focus:border-amber-500/50"
            />
            {(dateFrom || dateTo) && (
              <button
                onClick={() => { setDateFrom(''); setDateTo('') }}
                className="font-mono text-[10px] text-slate-600 hover:text-slate-300 tracking-widest transition-colors"
              >
                CLEAR
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        {loading && (
          <div className="py-24 text-center font-mono text-xs text-slate-600 tracking-widest animate-pulse">
            BUILDING TIMELINE...
          </div>
        )}

        {error && (
          <div className="font-mono text-xs text-red-400 border border-red-500/30 bg-red-900/10 rounded px-3 py-2">
            {error}
          </div>
        )}

        {!loading && !error && filtered.length === 0 && (
          <div className="py-24 text-center font-mono text-xs text-slate-600 tracking-widest">
            {timeline.length === 0
              ? 'No dated events found in personal case files.'
              : 'No events match the selected date range.'}
          </div>
        )}

        {!loading && filtered.length > 0 && (
          <div className="space-y-0">
            <p className="font-mono text-[10px] text-slate-600 tracking-widest mb-6">
              {filtered.length} DATE{filtered.length !== 1 ? 'S' : ''} · {filtered.reduce((a, e) => a + e.events.length, 0)} EVENT{filtered.reduce((a, e) => a + e.events.length, 0) !== 1 ? 'S' : ''}
            </p>

            {filtered.map((entry, i) => (
              <div key={entry.date} className="flex gap-4">
                {/* Timeline spine */}
                <div className="flex flex-col items-center flex-shrink-0 w-4">
                  <div className="w-2 h-2 rounded-full bg-amber-500/60 mt-1.5 flex-shrink-0" />
                  {i < filtered.length - 1 && <div className="w-px flex-1 bg-ink-600 mt-1" />}
                </div>

                {/* Content */}
                <div className="pb-6 flex-1 min-w-0">
                  <div className="font-mono text-[10px] text-amber-400/70 tracking-widest mb-2">{entry.date}</div>
                  <div className="space-y-2">
                    {entry.events.map((ev, j) => (
                      <button
                        key={j}
                        onClick={() => setModal(ev)}
                        className="w-full text-left bg-ink-800/60 border border-ink-700 rounded px-3 py-2 hover:border-ink-500 hover:bg-ink-800 transition-colors"
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <SourceBadge source={ev.source} />
                          {ev.citation && (
                            <span className="font-mono text-[10px] text-slate-600 truncate">{ev.citation}</span>
                          )}
                        </div>
                        <p className="text-xs text-slate-400 leading-relaxed line-clamp-2">{ev.text}</p>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      <EventModal event={modal} onClose={() => setModal(null)} />
    </div>
  )
}
