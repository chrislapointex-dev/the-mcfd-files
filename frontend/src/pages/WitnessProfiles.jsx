import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'

const SOURCE_COLORS = {
  foi:      'text-amber-400 border-amber-500/40 bg-amber-900/20',
  personal: 'text-violet-400 border-violet-500/40 bg-violet-900/20',
}

export default function WitnessProfiles() {
  const [witnesses, setWitnesses] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState(null)  // { name, role, file, chunks }
  const [profileLoading, setProfileLoading] = useState(false)
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
    try {
      const r = await fetch(`/api/witnesses/${encodeURIComponent(name)}`)
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const data = await r.json()
      setSelected(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setProfileLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-ink-900 font-sans text-slate-200">
      <div className="h-px bg-gradient-to-r from-transparent via-violet-500/60 to-transparent" />

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

            <div className="border border-ink-600 bg-ink-800 rounded-lg p-5 mb-6">
              <h2 className="font-display text-2xl text-white">{selected.name}</h2>
              <p className="font-mono text-xs text-slate-500 mt-1 tracking-wide">{selected.role} · {selected.file}</p>
              <div className="flex gap-3 mt-4">
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
                    <div className="flex items-center gap-2">
                      <span className={`font-mono text-[9px] px-1.5 py-0.5 rounded border tracking-widest ${SOURCE_COLORS[chunk.source] ?? 'text-slate-500 border-slate-600'}`}>
                        {chunk.source?.toUpperCase()}
                      </span>
                      {chunk.citation && (
                        <span className="font-mono text-[9px] text-slate-600 truncate">{chunk.citation}</span>
                      )}
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
