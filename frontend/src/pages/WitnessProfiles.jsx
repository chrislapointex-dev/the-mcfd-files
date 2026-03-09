import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import TrialBanner from '../components/TrialBanner'

const SOURCE_COLORS = {
  foi:      'text-amber-400 border-amber-500/40 bg-amber-900/20',
  personal: 'text-violet-400 border-violet-500/40 bg-violet-900/20',
}

const SEVERITY_COLORS = {
  critical: 'text-red-400 border-red-500/40 bg-red-900/20',
  high:     'text-orange-400 border-orange-500/40 bg-orange-900/20',
  medium:   'text-yellow-400 border-yellow-500/40 bg-yellow-900/20',
  low:      'text-slate-400 border-slate-600 bg-slate-900/20',
}

export default function WitnessProfiles() {
  const [witnesses, setWitnesses] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState(null)  // { name, role, file, phone, email, notes, chunks }
  const [profileLoading, setProfileLoading] = useState(false)
  const [relatedContradictions, setRelatedContradictions] = useState([])
  const [relatedEvents, setRelatedEvents] = useState([])
  const navigate = useNavigate()

  useEffect(() => {
    fetch('/api/witnesses')
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(setWitnesses)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const handleViewProfile = async (name) => {
    setProfileLoading(true)
    setRelatedContradictions([])
    setRelatedEvents([])
    try {
      const [profileRes, contraRes, eventsRes] = await Promise.all([
        fetch(`/api/witnesses/${encodeURIComponent(name)}`),
        fetch('/api/contradictions'),
        fetch('/api/timeline/events'),
      ])
      if (!profileRes.ok) throw new Error(`HTTP ${profileRes.status}`)
      const data = await profileRes.json()
      setSelected(data)

      if (contraRes.ok) {
        const contras = await contraRes.json()
        const nameLower = name.toLowerCase()
        const related = contras.filter(c =>
          (c.claim || '').toLowerCase().includes(nameLower) ||
          (c.evidence || '').toLowerCase().includes(nameLower) ||
          (c.source_doc || '').toLowerCase().includes(nameLower) ||
          (c.statement_a || '').toLowerCase().includes(nameLower) ||
          (c.statement_b || '').toLowerCase().includes(nameLower)
        )
        setRelatedContradictions(related)
      }

      if (eventsRes.ok) {
        const events = await eventsRes.json()
        const nameLower = name.toLowerCase()
        const evList = Array.isArray(events) ? events : (events.events || [])
        const related = evList.filter(e =>
          (e.title || '').toLowerCase().includes(nameLower) ||
          (e.description || '').toLowerCase().includes(nameLower)
        )
        setRelatedEvents(related)
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setProfileLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-ink-900 font-sans text-slate-200">
      <div className="h-px bg-gradient-to-r from-transparent via-violet-500/60 to-transparent" />
      <div className="max-w-4xl mx-auto px-4 pt-3"><TrialBanner /></div>

      <header className="sticky top-0 z-20 border-b border-ink-600 bg-ink-900/90 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
          <div>
            <h1 className="font-display text-3xl tracking-[0.12em] text-white leading-none">
              THE MCFD FILES
            </h1>
            <p className="font-mono text-[10px] text-slate-600 tracking-widest mt-1 uppercase">
              Witness Profiles
            </p>
          </div>
          <nav className="flex items-center gap-2 flex-wrap justify-end">
            <Link to="/trial" className="text-[10px] font-mono text-slate-500 border border-slate-700 px-2 py-1 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors hidden sm:block">TRIAL</Link>
            <Link to="/search" className="text-[10px] font-mono text-slate-500 border border-slate-700 px-2 py-1 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors hidden sm:block">SEARCH</Link>
            <Link to="/witnesses" className="text-[10px] font-mono text-violet-400 border border-violet-500/40 px-2 py-1 rounded tracking-widest hidden sm:block">WITNESSES</Link>
            <Link to="/contradictions" className="text-[10px] font-mono text-slate-500 border border-slate-700 px-2 py-1 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors hidden sm:block">CONTRADICTIONS</Link>
            <Link to="/timeline" className="text-[10px] font-mono text-slate-500 border border-slate-700 px-2 py-1 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors hidden sm:block">TIMELINE</Link>
            <span className="text-[10px] font-mono text-amber-500/60 border border-amber-500/25 px-2 py-1 rounded tracking-widest hidden sm:block">UNREDACTED</span>
          </nav>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">

        {loading && (
          <div className="py-24 text-center font-mono text-xs text-slate-600 tracking-widest animate-pulse">
            LOADING WITNESSES...
          </div>
        )}

        {error && (
          <div className="py-12 text-center font-mono text-sm text-red-400">Error: {error}</div>
        )}

        {/* ── Profile view ── */}
        {selected && !profileLoading && (
          <div>
            <button
              onClick={() => setSelected(null)}
              className="font-mono text-[10px] text-slate-500 hover:text-slate-300 tracking-widest mb-6 transition-colors"
            >
              ← BACK TO LIST
            </button>

            <div className="border border-ink-600 bg-ink-800 rounded-lg p-5 mb-6 space-y-4">
              <div>
                <h2 className="font-display text-2xl text-white">{selected.name}</h2>
                <p className="font-mono text-xs text-slate-500 mt-1 tracking-wide">{selected.role} · {selected.file}</p>
              </div>

              {/* Contact info */}
              {(selected.phone || selected.email) && (
                <div className="border-t border-ink-700 pt-3 space-y-1">
                  <p className="font-mono text-[9px] text-slate-600 tracking-widest uppercase">Contact</p>
                  {selected.phone && <p className="font-mono text-xs text-slate-400">📞 {selected.phone}</p>}
                  {selected.email && <p className="font-mono text-xs text-slate-400">✉ {selected.email}</p>}
                </div>
              )}

              {/* Notes */}
              {selected.notes && (
                <div className="border-t border-ink-700 pt-3">
                  <p className="font-mono text-[9px] text-slate-600 tracking-widest uppercase mb-1">Notes</p>
                  <p className="font-mono text-xs text-slate-300 leading-relaxed">{selected.notes}</p>
                </div>
              )}

              {/* Related Contradictions */}
              {relatedContradictions.length > 0 && (
                <div className="border-t border-ink-700 pt-3">
                  <p className="font-mono text-[9px] text-slate-600 tracking-widest uppercase mb-2">
                    Related Contradictions ({relatedContradictions.length})
                  </p>
                  <div className="space-y-1.5">
                    {relatedContradictions.map(c => (
                      <div key={c.id} className="flex items-start gap-2">
                        <span className={`font-mono text-[9px] px-1.5 py-0.5 rounded border tracking-widest flex-shrink-0 ${SEVERITY_COLORS[c.severity] ?? SEVERITY_COLORS.low}`}>
                          {(c.severity || 'low').toUpperCase()}
                        </span>
                        <p className="font-mono text-[10px] text-slate-400 leading-tight">{c.claim || c.statement_a || `Contradiction #${c.id}`}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Related Timeline Events */}
              {relatedEvents.length > 0 && (
                <div className="border-t border-ink-700 pt-3">
                  <p className="font-mono text-[9px] text-slate-600 tracking-widest uppercase mb-2">
                    Related Timeline Events ({relatedEvents.length})
                  </p>
                  <div className="space-y-1">
                    {relatedEvents.map((e, i) => (
                      <div key={i} className="flex items-start gap-2">
                        <span className="font-mono text-[9px] text-slate-600 flex-shrink-0">{e.date || ''}</span>
                        <p className="font-mono text-[10px] text-slate-400 leading-tight">{e.title}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex gap-3 pt-1 border-t border-ink-700">
                <button
                  onClick={() => navigate(`/search?ask=Summarize everything the FOI says about ${encodeURIComponent(selected.name)}`)}
                  className="font-mono text-[10px] text-sky-400 border border-sky-500/30 px-3 py-1.5 rounded tracking-widest hover:bg-sky-900/20 transition-colors"
                >
                  ASK AI
                </button>
                <Link
                  to="/contradictions"
                  className="font-mono text-[10px] text-amber-400 border border-amber-500/30 px-3 py-1.5 rounded tracking-widest hover:bg-amber-900/20 transition-colors"
                >
                  ANALYZE CONTRADICTIONS
                </Link>
              </div>
            </div>

            {selected.chunks.length === 0 ? (
              <p className="font-mono text-xs text-slate-600 py-8 text-center">
                No chunks found for this witness in FOI/personal documents.
              </p>
            ) : (
              <div className="space-y-4">
                <p className="font-mono text-[10px] text-slate-600 tracking-widest uppercase">
                  {selected.chunks.length} chunk{selected.chunks.length !== 1 ? 's' : ''} found
                </p>
                {selected.chunks.map((chunk) => (
                  <div key={chunk.chunk_id} className="border border-ink-700 bg-ink-800 rounded-lg p-4 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className={`font-mono text-[9px] px-1.5 py-0.5 rounded border tracking-widest flex-shrink-0 ${SOURCE_COLORS[chunk.source] ?? 'text-slate-500 border-slate-600'}`}>
                          {chunk.source?.toUpperCase()}
                        </span>
                        {chunk.citation && (
                          <span className="font-mono text-[9px] text-slate-600 truncate">{chunk.citation}</span>
                        )}
                      </div>
                      <button
                        onClick={() => navigator.clipboard.writeText(
                          `Source: ${chunk.source} | ${chunk.citation}\n\n${chunk.text}`
                        )}
                        className="font-mono text-[9px] text-ink-400 border border-ink-600 px-1.5 py-0.5 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors flex-shrink-0"
                      >
                        COPY
                      </button>
                    </div>
                    <p className="font-mono text-xs text-slate-300 leading-relaxed whitespace-pre-line">
                      {chunk.text}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {profileLoading && (
          <div className="py-24 text-center font-mono text-xs text-slate-600 tracking-widest animate-pulse">
            LOADING PROFILE...
          </div>
        )}

        {/* ── Witness list ── */}
        {!selected && !profileLoading && witnesses && (
          <div>
            <p className="font-mono text-[10px] text-slate-600 tracking-widest uppercase mb-6">
              {witnesses.length} witnesses · FOI + Personal Documents
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {witnesses.map(w => (
                <div key={w.name} className="border border-ink-600 bg-ink-800 rounded-lg p-5 space-y-3">
                  <div>
                    <h3 className="font-display text-lg text-white">{w.name}</h3>
                    <p className="font-mono text-[10px] text-slate-500 tracking-wide mt-0.5">{w.role}</p>
                    <p className="font-mono text-[9px] text-slate-600 tracking-widest">{w.file}</p>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className={`font-mono text-xs px-2 py-0.5 rounded border ${
                      w.chunk_count > 0
                        ? 'text-violet-400 border-violet-500/40 bg-violet-900/20'
                        : 'text-slate-600 border-slate-700'
                    }`}>
                      {w.chunk_count} chunk{w.chunk_count !== 1 ? 's' : ''}
                    </span>
                    <button
                      onClick={() => handleViewProfile(w.name)}
                      className="font-mono text-[10px] text-sky-400 border border-sky-500/30 px-3 py-1 rounded tracking-widest hover:bg-sky-900/20 transition-colors"
                    >
                      VIEW PROFILE
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

      </main>

      <footer className="border-t border-ink-600 mt-20 py-8">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <p className="font-mono text-[10px] text-slate-700 uppercase tracking-widest">
            The MCFD Files · Witness Profiles · Trial May 19–21, 2026
          </p>
        </div>
      </footer>
    </div>
  )
}
