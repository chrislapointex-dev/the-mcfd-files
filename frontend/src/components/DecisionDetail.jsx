import { useState, useEffect } from 'react'

function courtAbbr(court) {
  if (court === 'BC Court of Appeal') return 'BCCA'
  if (court === 'BC Supreme Court') return 'BCSC'
  if (court === 'BC Provincial Court') return 'BCPC'
  return court ?? '—'
}

function MetaField({ label, value }) {
  return (
    <div>
      <div className="text-[10px] font-mono text-slate-600 uppercase tracking-widest mb-1">{label}</div>
      <div className="font-mono text-xs text-slate-300">{value ?? '—'}</div>
    </div>
  )
}

export default function DecisionDetail({ id, onBack }) {
  const [decision, setDecision] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [citationCopied, setCitationCopied] = useState(false)

  const handleCopyCitation = (citation, title) => {
    navigator.clipboard.writeText(citation || title || '')
    setCitationCopied(true)
    setTimeout(() => setCitationCopied(false), 2000)
  }

  useEffect(() => {
    setLoading(true)
    setDecision(null)
    setError(null)
    fetch(`/api/decisions/${id}`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(d => { setDecision(d); setLoading(false) })
      .catch(err => { setError(err.message); setLoading(false) })
  }, [id])

  if (loading) {
    return (
      <div className="space-y-3 animate-fade-up">
        <div className="h-5 w-32 bg-ink-700 rounded animate-pulse" />
        <div className="h-8 w-2/3 bg-ink-700 rounded animate-pulse mt-4" />
        <div className="h-4 w-1/2 bg-ink-700 rounded animate-pulse" />
        <div className="h-[60vh] bg-ink-800 rounded-lg animate-pulse mt-6" />
      </div>
    )
  }

  if (error || !decision) {
    return (
      <div className="text-center py-24">
        <p className="font-mono text-sm text-red-400 mb-4">
          {error ?? 'Decision not found.'}
        </p>
        <button onClick={onBack} className="font-mono text-xs text-amber-500 hover:text-amber-400 transition-colors">
          ← BACK TO DECISIONS
        </button>
      </div>
    )
  }

  const charCount = decision.full_text ? (decision.full_text.length / 1000).toFixed(1) : null

  return (
    <div className="animate-fade-up">

      {/* Back */}
      <button
        onClick={onBack}
        className="group flex items-center gap-2 text-xs font-mono text-slate-500 hover:text-amber-500 transition-colors mb-8"
      >
        <span className="group-hover:-translate-x-1 transition-transform inline-block">←</span>
        ALL DECISIONS
      </button>

      {/* File header card */}
      <div className="border border-ink-600 bg-ink-800 rounded-lg p-6 mb-5">

        {/* Classification row */}
        <div className="flex items-center justify-between mb-5 pb-4 border-b border-ink-600">
          <div className="flex items-center gap-3">
            {decision.source === 'rcy' ? (
              <span className="text-[10px] font-mono font-bold text-teal-400 border border-teal-500/40 px-2 py-0.5 rounded tracking-widest uppercase">
                RCY REPORT
              </span>
            ) : (
              <span className="text-[10px] font-mono font-bold text-amber-500 border border-amber-500/40 px-2 py-0.5 rounded tracking-widest uppercase">
                CASE FILE
              </span>
            )}
            <span className="text-[10px] font-mono text-slate-600 uppercase tracking-widest">
              {decision.source}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => handleCopyCitation(decision.citation, decision.title)}
              className="text-[11px] font-mono text-slate-500 hover:text-amber-500 transition-colors"
            >
              {citationCopied ? 'COPIED ✓' : 'COPY CITATION'}
            </button>
            <button
              onClick={() => window.print()}
              className="text-[11px] font-mono text-slate-500 hover:text-slate-300 transition-colors"
            >
              PRINT
            </button>
            {decision.vault_file && (
              <a
                href={`/api/vault/${decision.vault_file}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[11px] font-mono font-bold text-amber-500 border border-amber-500/40 px-2 py-0.5 rounded hover:bg-amber-500/10 transition-colors"
              >
                VIEW SOURCE PDF ↗
              </a>
            )}
            <a
              href={decision.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[11px] font-mono text-slate-500 hover:text-amber-500 transition-colors"
            >
              SOURCE DOC →
            </a>
          </div>
        </div>

        {/* Citation */}
        <div className="font-mono text-sm text-amber-500 tracking-wider mb-2">
          {decision.citation ?? 'NO CITATION'}
        </div>

        {/* Title */}
        <h1 className="text-2xl font-medium text-white leading-tight mb-6">
          {decision.title}
        </h1>

        {/* Metadata grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-5">
          <MetaField label="Court" value={courtAbbr(decision.court)} />
          <MetaField label="Full Court" value={decision.court} />
          <MetaField label="Date" value={decision.date} />
          <MetaField
            label="Added"
            value={decision.scraped_at ? decision.scraped_at.slice(0, 10) : null}
          />
        </div>
      </div>

      {/* Full text */}
      <div className="border border-ink-600 bg-ink-800 rounded-lg">
        <div className="flex items-center justify-between px-6 py-3 border-b border-ink-600">
          <span className="text-[10px] font-mono text-slate-600 uppercase tracking-widest">
            Full Decision Text
          </span>
          {charCount && (
            <span className="text-[10px] font-mono text-slate-700">
              {charCount}K chars
            </span>
          )}
        </div>
        <div className="p-6 max-h-[72vh] overflow-y-auto">
          <pre className="font-mono text-sm text-slate-400 leading-[1.8] whitespace-pre-wrap break-words">
            {decision.full_text ?? 'No text available.'}
          </pre>
        </div>
      </div>
    </div>
  )
}
