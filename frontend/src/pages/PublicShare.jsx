import { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'

const SEVERITY_ORDER = { DIRECT: 0, PARTIAL: 1, NONE: 2 }

function SeverityBadge({ severity }) {
  const colors = {
    DIRECT: 'bg-red-900/60 text-red-300 border border-red-700/50',
    PARTIAL: 'bg-amber-900/60 text-amber-300 border border-amber-700/50',
    NONE: 'bg-slate-800 text-slate-400 border border-slate-700/50',
  }
  return (
    <span className={`font-mono text-[9px] px-1.5 py-0.5 rounded tracking-widest ${colors[severity] || colors.NONE}`}>
      {severity}
    </span>
  )
}

function StatCard({ value, label, sub }) {
  return (
    <div className="border border-slate-700/50 rounded bg-slate-900/60 p-5 flex flex-col gap-1">
      <div className="font-mono text-2xl text-red-400 font-bold tracking-tight">{value}</div>
      <div className="font-mono text-[11px] text-slate-300 leading-snug">{label}</div>
      {sub && <div className="font-mono text-[9px] text-slate-600 mt-1 leading-snug">{sub}</div>}
    </div>
  )
}

function CaseStrength({ strength }) {
  if (!strength) return null

  const ratingColor = {
    STRONG: 'text-green-400',
    SOLID: 'text-amber-400',
    DEVELOPING: 'text-red-400',
  }[strength.rating] || 'text-slate-400'

  const ratingBg = {
    STRONG: 'bg-green-900/40 border-green-700/50 text-green-300',
    SOLID: 'bg-amber-900/40 border-amber-700/50 text-amber-300',
    DEVELOPING: 'bg-red-900/40 border-red-700/50 text-red-300',
  }[strength.rating] || 'bg-slate-800 border-slate-700/50 text-slate-400'

  return (
    <section>
      <div className="flex items-baseline justify-between mb-4">
        <h2 className="text-[11px] tracking-[0.25em] text-slate-400 uppercase">
          Case Strength Score
        </h2>
        <span className={`font-mono text-[9px] px-2 py-0.5 rounded border tracking-widest ${ratingBg}`}>
          {strength.rating}
        </span>
      </div>

      <div className="border border-slate-800 rounded bg-slate-900/40 p-5">
        {/* Score display */}
        <div className="flex items-end gap-3 mb-5">
          <span className={`font-mono text-5xl font-bold ${ratingColor}`}>
            {strength.total_score}
          </span>
          <span className="font-mono text-[13px] text-slate-600 mb-1.5">/ {strength.max_score}</span>
        </div>

        {/* Breakdown table */}
        <div className="border border-slate-800 rounded overflow-hidden text-[11px]">
          <div className="flex text-[9px] text-slate-600 uppercase tracking-widest px-3 py-1.5 bg-slate-950 border-b border-slate-800">
            <span className="flex-1">Category</span>
            <span className="w-16 text-right">Points</span>
            <span className="w-10 text-right">Max</span>
          </div>
          {strength.breakdown.map((row, i) => (
            <div key={i} className="flex items-center px-3 py-2 border-b border-slate-800 last:border-0">
              <div className="flex-1 min-w-0">
                <span className="text-slate-300">{row.category}</span>
                {row.note && (
                  <span className="ml-2 text-[9px] text-slate-600">{row.note}</span>
                )}
              </div>
              <span className="w-16 text-right text-slate-200 font-mono">{row.points}</span>
              <span className="w-10 text-right text-slate-700 font-mono">{row.max}</span>
            </div>
          ))}
        </div>

        {/* Disclaimer */}
        <p className="text-[10px] text-slate-600 italic mt-3 leading-relaxed">
          {strength.disclaimer}
        </p>
      </div>
    </section>
  )
}

export default function PublicShare() {
  const [costs, setCosts] = useState(null)
  const [scale, setScale] = useState(null)
  const [allContradictions, setAllContradictions] = useState([])
  const [contraTotal, setContraTotal] = useState(0)
  const [timeline, setTimeline] = useState([])
  const [viewCount, setViewCount] = useState(null)
  const [copied, setCopied] = useState(false)
  const [strength, setStrength] = useState(null)

  // Contradiction search/filter state
  const [searchTerm, setSearchTerm] = useState('')
  const [severityFilter, setSeverityFilter] = useState('all')
  const [showAll, setShowAll] = useState(false)

  useEffect(() => {
    fetch('/api/costs').then(r => r.json()).then(setCosts).catch(() => {})
    fetch('/api/costs/scale').then(r => r.json()).then(setScale).catch(() => {})
    fetch('/api/share/contradictions').then(r => r.json()).then(d => {
      const items = Array.isArray(d) ? d : (d.items || d.contradictions || [])
      setContraTotal(items.length)
      const sorted = [...items].sort((a, b) => {
        const sev = (SEVERITY_ORDER[a.severity] ?? 2) - (SEVERITY_ORDER[b.severity] ?? 2)
        if (sev !== 0) return sev
        return (b.id || 0) - (a.id || 0)
      })
      setAllContradictions(sorted)
    }).catch(() => {})
    // Fire-and-forget view tracking
    fetch('/api/share/view', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ referrer: document.referrer || null }),
    }).then(r => r.json()).catch(() => {})
    fetch('/api/share/views').then(r => r.json()).then(d => {
      setViewCount(d.total_views ?? null)
    }).catch(() => {})
    fetch('/api/share/strength').then(r => r.json()).then(setStrength).catch(() => {})
    fetch('/api/share/timeline').then(r => r.json()).then(d => {
      const items = Array.isArray(d) ? d : (d.events || d.items || [])
      const sorted = [...items].sort((a, b) => {
        const sev = (SEVERITY_ORDER[a.severity] ?? 2) - (SEVERITY_ORDER[b.severity] ?? 2)
        if (sev !== 0) return sev
        return 0
      })
      setTimeline(sorted.slice(0, 5))
    }).catch(() => {})
  }, [])

  // Client-side filter + search
  const filteredContradictions = useMemo(() => {
    let items = allContradictions
    if (severityFilter !== 'all') {
      items = items.filter(c => c.severity === severityFilter)
    }
    if (searchTerm.trim()) {
      const term = searchTerm.trim().toLowerCase()
      items = items.filter(c =>
        (c.claim || '').toLowerCase().includes(term) ||
        (c.evidence || '').toLowerCase().includes(term)
      )
    }
    return items
  }, [allContradictions, severityFilter, searchTerm])

  const displayedContradictions = showAll ? filteredContradictions : filteredContradictions.slice(0, 5)

  const shareText = encodeURIComponent(
    '$175,041.32 taxpayer cost. 23 documented contradictions. ' +
    '906 vs 1,792 FOI pages unaccounted for. ' +
    'BC child protection case PC 19700. ' +
    'OIPC complaint INV-F-26-00220 active. ' +
    '#BCPolitics #MCFD #ProtectBCKids'
  )
  const shareUrl = encodeURIComponent(window.location.href)

  const grandTotal = costs?.grand_total ?? 175041.32
  const byCategory = costs?.by_category || {}
  const scaleLoBC = scale?.bc_low_formatted || '$1.4B'
  const scaleHiBC = scale?.bc_high_formatted || '$2.1B'

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-mono">
      {/* Top gradient bar */}
      <div className="h-1 bg-gradient-to-r from-red-900 via-red-500 to-red-900" />

      {/* Header */}
      <header className="py-12 px-4 text-center border-b border-slate-800">
        <div className="max-w-3xl mx-auto">
          <div className="text-[10px] text-red-400 tracking-[0.3em] uppercase mb-3">
            Public Accountability Record
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-white tracking-[0.08em] mb-2">
            THE MCFD FILES
          </h1>
          <div className="text-[11px] text-slate-500 tracking-[0.2em] mb-6">
            PC 19700 · British Columbia, Canada
          </div>
          <p className="text-[13px] text-slate-400 leading-relaxed max-w-2xl mx-auto">
            This record documents the publicly-verifiable costs, contradictions, and systemic failures
            associated with a single MCFD child-protection file. All figures are derived from BC
            government-published rates, FOI-disclosed documents, and sworn court statements.
            Trial date: <span className="text-slate-200">May 19–21, 2026</span>.
          </p>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-10 space-y-14">

        {/* Stat Cards */}
        <section>
          <div className="grid grid-cols-2 md:grid-cols-2 gap-4">
            <StatCard
              value={`$${(grandTotal).toLocaleString('en-CA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
              label="Documented taxpayer cost — one case, 214 days"
              sub="Based on publicly available BC government rates"
            />
            <StatCard
              value={contraTotal > 0 ? `${contraTotal}` : "…"}
              label="Documented contradictions in sworn MCFD statements"
              sub="Severity: DIRECT | PARTIAL | reviewed by AI engine"
            />
            <StatCard
              value="906 vs 1,792"
              label="Pages received vs. pages MCFD told OIPC existed"
              sub="FOI disclosure gap — confirmed by OIPC complaint record"
            />
            <StatCard
              value={`${scaleLoBC} – ${scaleHiBC}`}
              label="Estimated BC-wide annual cost (5,000 children)"
              sub="Source: BC MCFD Annual Service Plan 2024-25"
            />
          </div>
        </section>

        {/* Case Strength Score */}
        <CaseStrength strength={strength} />

        {/* Contradictions */}
        <section>
          <div className="flex items-baseline justify-between mb-4">
            <h2 className="text-[11px] tracking-[0.25em] text-slate-400 uppercase">
              Contradiction Record ({contraTotal} total)
            </h2>
          </div>

          {/* Search + filter controls */}
          <div className="flex flex-wrap gap-2 mb-3">
            <input
              type="text"
              placeholder="Search contradictions..."
              value={searchTerm}
              onChange={e => { setSearchTerm(e.target.value); setShowAll(false) }}
              className="flex-1 min-w-[160px] bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-[12px] text-slate-300 placeholder-slate-600 font-mono outline-none focus:border-slate-500"
            />
            {['all', 'DIRECT', 'PARTIAL'].map(sev => (
              <button
                key={sev}
                onClick={() => { setSeverityFilter(sev); setShowAll(false) }}
                className={`font-mono text-[10px] tracking-widest px-3 py-1.5 rounded border transition-colors ${
                  severityFilter === sev
                    ? 'bg-white text-slate-900 border-white'
                    : 'bg-slate-900 text-slate-500 border-slate-700 hover:border-slate-500 hover:text-slate-300'
                }`}
              >
                {sev.toUpperCase()}
              </button>
            ))}
          </div>

          <div className="border border-slate-800 rounded overflow-hidden">
            {filteredContradictions.length === 0 ? (
              <div className="p-6 text-center text-[11px] text-slate-600">
                {allContradictions.length === 0
                  ? 'Contradiction data loading…'
                  : 'No contradictions match your search.'}
              </div>
            ) : (
              displayedContradictions.map((c, i) => (
                <div
                  key={c.id || i}
                  className="flex items-start gap-3 px-4 py-3 border-b border-slate-800 last:border-0 hover:bg-slate-900/40 transition-colors"
                >
                  <div className="pt-0.5 shrink-0">
                    <SeverityBadge severity={c.severity || 'NONE'} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[12px] text-slate-300 leading-snug">
                      {(c.claim || '').length > 120
                        ? (c.claim || '').slice(0, 120) + '…'
                        : (c.claim || '')}
                    </p>
                    {c.source_doc && (
                      <p className="text-[10px] text-slate-600 mt-1 truncate">{c.source_doc}</p>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Show all / show fewer toggle */}
          {filteredContradictions.length > 5 && (
            <button
              onClick={() => setShowAll(v => !v)}
              className="mt-2 text-[10px] text-slate-500 hover:text-slate-300 transition-colors"
            >
              {showAll
                ? `Show fewer ↑`
                : `Show all ${filteredContradictions.length} contradictions ↓`}
            </button>
          )}
          {filteredContradictions.length <= 5 && (
            <p className="text-[10px] text-slate-600 mt-2">
              Full contradiction record available upon request. Trial subpoena in progress.
            </p>
          )}
        </section>

        {/* Cost Breakdown */}
        <section>
          <h2 className="text-[11px] tracking-[0.25em] text-slate-400 uppercase mb-4">
            Cost Breakdown by Category
          </h2>
          {Object.keys(byCategory).length === 0 ? (
            <div className="text-[11px] text-slate-600 py-4">Cost data loading…</div>
          ) : (
            <div className="border border-slate-800 rounded overflow-hidden">
              {Object.entries(byCategory).map(([cat, subtotal], i) => (
                <div
                  key={cat}
                  className="flex items-center justify-between px-4 py-2.5 border-b border-slate-800 last:border-0"
                >
                  <span className="text-[11px] text-slate-400 uppercase tracking-widest">{cat}</span>
                  <span className="text-[12px] text-slate-200">
                    ${Number(subtotal?.subtotal ?? subtotal).toLocaleString('en-CA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </div>
              ))}
            </div>
          )}
          <p className="text-[10px] text-slate-600 mt-2">
            <a href="/costs" className="hover:text-slate-400 transition-colors underline underline-offset-2">
              Full breakdown →
            </a>
            {' '}All figures based on publicly available BC government rates and published estimates.
          </p>
        </section>

        {/* Timeline Highlights */}
        <section>
          <h2 className="text-[11px] tracking-[0.25em] text-slate-400 uppercase mb-4">
            Timeline Highlights
          </h2>
          {timeline.length === 0 ? (
            <div className="text-[11px] text-slate-600 py-4">
              Timeline data available upon request.
            </div>
          ) : (
            <div className="space-y-2">
              {timeline.map((ev, i) => {
                const sevColor = {
                  critical: 'bg-red-500',
                  high: 'bg-amber-500',
                  medium: 'bg-yellow-500',
                  low: 'bg-slate-500',
                }[ev.severity] || 'bg-slate-600'
                return (
                  <div key={ev.id || i} className="flex items-start gap-3 py-2 border-b border-slate-800/60">
                    <div className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${sevColor}`} />
                    <div>
                      <span className="text-[10px] text-slate-600 mr-2">{ev.event_date || ev.date || ''}</span>
                      <span className="text-[12px] text-slate-300">{ev.title || ev.name || ''}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </section>

        {/* Footer */}
        <footer className="border-t border-slate-800 pt-8 pb-4 space-y-2">
          <p className="text-[10px] text-slate-600">
            OIPC Complaint filed · Trial: May 19–21, 2026, BC Provincial Court, Kamloops
          </p>
          <p className="text-[10px] text-slate-600">
            All evidence preserved under <em>Canadian Charter of Rights and Freedoms</em> s.7, s.8, s.15
          </p>
          <p className="text-[10px] text-slate-600">
            Media / legal inquiries: PC 19700 public file — contact available upon request
          </p>
          <p className="text-[10px] text-slate-700 mt-4">
            Pro Patria · The MCFD Files · Generated {new Date().toLocaleDateString('en-CA')}
          </p>
          <div className="flex items-center gap-4 flex-wrap mt-1">
            {viewCount !== null && (
              <span className="text-[10px] text-slate-700">👁 {viewCount} views</span>
            )}
            <Link
              to="/methodology"
              className="text-[10px] text-slate-600 hover:text-slate-400 transition-colors"
            >
              Methodology
            </Link>
            <Link
              to="/press"
              className="text-[10px] text-slate-600 hover:text-slate-400 transition-colors"
            >
              Press Kit
            </Link>
          </div>
          <div className="flex gap-4 mt-2 flex-wrap">
            <a
              href={`https://twitter.com/intent/tweet?text=${shareText}&url=${shareUrl}`}
              target="_blank" rel="noopener noreferrer"
              className="text-[10px] text-slate-600 hover:text-slate-400 transition-colors"
            >
              Share on X
            </a>
            <a
              href={`mailto:?subject=THE MCFD FILES — Public Accountability Record&body=${shareText}%20${decodeURIComponent(shareUrl)}`}
              className="text-[10px] text-slate-600 hover:text-slate-400 transition-colors"
            >
              Share via Email
            </a>
            <button
              onClick={() => {
                navigator.clipboard.writeText(window.location.href)
                setCopied(true)
                setTimeout(() => setCopied(false), 2000)
              }}
              className="text-[10px] text-slate-600 hover:text-slate-400 transition-colors"
            >
              {copied ? 'Copied!' : 'Copy Link'}
            </button>
          </div>
        </footer>
      </main>
    </div>
  )
}
