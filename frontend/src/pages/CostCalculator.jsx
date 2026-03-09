import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

const CATEGORY_LABELS = {
  supervision: 'SUPERVISION',
  placement: 'PLACEMENT',
  legal: 'LEGAL',
  court: 'COURT',
  administration: 'ADMINISTRATION',
  enforcement: 'ENFORCEMENT',
}

const CATEGORY_COLORS = {
  supervision: 'text-amber-400 border-amber-500/30',
  placement: 'text-violet-400 border-violet-500/30',
  legal: 'text-red-400 border-red-500/30',
  court: 'text-red-500 border-red-600/40',
  administration: 'text-slate-400 border-slate-600/40',
  enforcement: 'text-orange-400 border-orange-500/30',
}

function fmt(n) {
  return n.toLocaleString('en-CA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function fmtB(n) {
  if (n >= 1e9) return `$${(n / 1e9).toFixed(1)}B`
  if (n >= 1e6) return `$${(n / 1e6).toFixed(0)}M`
  return `$${fmt(n)}`
}

export default function CostCalculator() {
  const [data, setData] = useState(null)
  const [scale, setScale] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/api/costs')
      .then(r => r.json())
      .then(setData)
      .catch(() => setError('Failed to load cost data'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    fetch('/api/costs/scale')
      .then(r => r.json())
      .then(setScale)
      .catch(() => {/* scale section just won't render */})
  }, [])

  const handleExport = () => {
    if (!data) return
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'taxpayer-cost-report-PC19700.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="min-h-screen bg-ink-900 font-sans text-slate-200">
      <div className="h-px bg-gradient-to-r from-transparent via-red-500/60 to-transparent" />

      {/* Header */}
      <header className="sticky top-0 z-20 border-b border-ink-600 bg-ink-900/90 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl tracking-[0.12em] text-white leading-none">
              TAXPAYER COST TRACKER
            </h1>
            <p className="font-mono text-[10px] text-slate-600 tracking-widest mt-1 uppercase">
              PC 19700 — LaPointe, Christopher · Based on publicly available BC government rates
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to="/"
              className="text-[10px] font-mono text-slate-500 border border-slate-700 px-2 py-1 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors"
            >
              ← BACK
            </Link>
            <button
              onClick={handleExport}
              disabled={!data}
              className="text-[10px] font-mono text-amber-400 border border-amber-500/40 px-2 py-1 rounded tracking-widest hover:text-amber-300 hover:border-amber-400/60 transition-colors disabled:opacity-40"
            >
              EXPORT JSON
            </button>
            <a
              href="/api/export/media-package"
              download="mcfd-media-package.json"
              className="text-[10px] font-mono text-slate-400 border border-slate-700 px-2 py-1 rounded tracking-widest hover:text-slate-200 hover:border-slate-500 transition-colors"
            >
              MEDIA PACKAGE
            </a>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">

        {loading && (
          <div className="py-24 text-center">
            <p className="font-mono text-xs text-slate-600 tracking-widest animate-pulse">LOADING COST DATA...</p>
          </div>
        )}

        {error && (
          <div className="py-24 text-center">
            <p className="font-mono text-sm text-red-400">{error}</p>
          </div>
        )}

        {data && (
          <>
            {/* Grand total counter */}
            <div className="mb-8 border border-red-500/30 bg-red-900/10 rounded-lg p-6 text-center">
              <p className="font-mono text-[10px] text-slate-500 tracking-widest mb-2 uppercase">
                Estimated Public Cost — {data.days_in_care} Days in Care
              </p>
              <p className="font-mono text-5xl font-bold text-red-400 tracking-tight">
                ${fmt(data.grand_total)}
              </p>
              <p className="font-mono text-[10px] text-slate-600 tracking-widest mt-2">
                {data.case_ref}
              </p>
            </div>

            {/* Category breakdown */}
            {Object.entries(data.by_category).map(([cat, catData]) => (
              <div key={cat} className="mb-6">
                {/* Category header */}
                <div className="flex items-center justify-between mb-2">
                  <span className={`font-mono text-[10px] tracking-widest border rounded px-2 py-0.5 ${CATEGORY_COLORS[cat] || 'text-slate-400 border-slate-600/40'}`}>
                    {CATEGORY_LABELS[cat] || cat.toUpperCase()}
                  </span>
                  <span className="font-mono text-xs text-slate-400">
                    Subtotal: <span className="text-white font-bold">${fmt(catData.subtotal)}</span>
                  </span>
                </div>

                {/* Line items table */}
                <div className="border border-ink-600 rounded overflow-hidden">
                  {catData.items.map((item, i) => {
                    const isBreach = item.total === 0 && item.line_item.toLowerCase().includes('breach')
                    return (
                      <div
                        key={item.id}
                        className={`flex items-start gap-4 px-4 py-3 text-xs ${
                          i > 0 ? 'border-t border-ink-700' : ''
                        } ${
                          isBreach
                            ? 'bg-red-900/10 border-red-500/20'
                            : 'bg-ink-800/50'
                        }`}
                      >
                        {/* Line item description */}
                        <div className="flex-1 min-w-0">
                          <p className={`font-mono text-xs leading-snug ${isBreach ? 'text-red-400' : 'text-slate-300'}`}>
                            {item.line_item}
                            {isBreach && (
                              <span className="ml-2 text-[9px] border border-red-500/40 text-red-400 px-1 py-0.5 rounded tracking-widest">
                                DOCUMENTED BREACH
                              </span>
                            )}
                          </p>
                          <p className="font-mono text-[10px] text-slate-600 mt-0.5">
                            {item.source_url ? (
                              <a
                                href={item.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-500/70 hover:text-blue-400 underline underline-offset-2"
                              >
                                {item.source}
                              </a>
                            ) : (
                              item.source
                            )}
                          </p>
                        </div>

                        {/* Per unit */}
                        <div className="text-right flex-shrink-0 w-20 hidden sm:block">
                          <p className="font-mono text-[10px] text-slate-600 uppercase tracking-widest">Per unit</p>
                          <p className="font-mono text-xs text-slate-400">
                            {item.amount_per_unit === 0 ? '—' : `$${item.amount_per_unit.toLocaleString('en-CA', { minimumFractionDigits: 2 })}`}
                          </p>
                        </div>

                        {/* Units */}
                        <div className="text-right flex-shrink-0 w-12 hidden sm:block">
                          <p className="font-mono text-[10px] text-slate-600 uppercase tracking-widest">Units</p>
                          <p className="font-mono text-xs text-slate-400">{item.units}</p>
                        </div>

                        {/* Total */}
                        <div className="text-right flex-shrink-0 w-24">
                          <p className="font-mono text-[10px] text-slate-600 uppercase tracking-widest">Total</p>
                          <p className={`font-mono text-sm font-bold ${isBreach ? 'text-red-400' : 'text-white'}`}>
                            {item.total === 0 ? 'ON RECORD' : `$${fmt(item.total)}`}
                          </p>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}

            {/* Grand total row */}
            <div className="border border-red-500/40 bg-red-900/5 rounded px-4 py-4 flex items-center justify-between mt-6">
              <span className="font-mono text-xs text-slate-400 tracking-widest uppercase">Grand Total — {data.days_in_care} days in care</span>
              <span className="font-mono text-2xl font-bold text-red-400">
                ${fmt(data.grand_total)}
              </span>
            </div>

            {/* Section A — Missing cost categories */}
            <div className="mt-8 border border-amber-500/30 bg-amber-900/5 rounded-lg p-5">
              <p className="font-mono text-[10px] text-amber-400 tracking-widest uppercase mb-2">
                Missing Cost Categories — Not Yet Quantified
              </p>
              <p className="font-mono text-xs text-slate-400 leading-relaxed">
                The following costs are documented but not yet quantifiable from public data:
                psychological assessments ordered by MCFD, private investigator activity,
                child's therapy costs, VAC benefit misclassification impact, CRA dispute costs.
                These represent additional undisclosed public expenditure not reflected in the totals above.
              </p>
            </div>

            {/* Section B — BC Scale Projection */}
            {scale && (
              <div className="mt-6 border border-red-500/30 bg-red-900/5 rounded-lg p-5">
                <p className="font-mono text-[10px] text-red-400 tracking-widest uppercase mb-4">
                  BC Scale Projection — Public Accountability
                </p>
                <div className="space-y-3">
                  <div className="flex items-center justify-between border-b border-ink-700 pb-3">
                    <span className="font-mono text-xs text-slate-400">This case (documented)</span>
                    <span className="font-mono text-sm font-bold text-white">${fmt(scale.this_case.total)}</span>
                  </div>
                  <div className="flex items-center justify-between border-b border-ink-700 pb-3">
                    <span className="font-mono text-xs text-slate-400">Estimated true cost (this case)</span>
                    <span className="font-mono text-sm font-bold text-amber-400">
                      ${fmt(scale.estimated_true_total.low)} – ${fmt(scale.estimated_true_total.high)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between border-b border-ink-700 pb-3">
                    <div>
                      <span className="font-mono text-xs text-slate-400">BC provincial projection (5,000 children)</span>
                      <span className="block font-mono text-[10px] text-slate-600 mt-0.5">
                        Source:{' '}
                        <a
                          href={scale.bc_scale.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-500/70 hover:text-blue-400 underline underline-offset-2"
                        >
                          {scale.bc_scale.source}
                        </a>
                      </span>
                    </div>
                    <span className="font-mono text-sm font-bold text-red-400">
                      {fmtB(scale.bc_scale.projected_annual_low)} – {fmtB(scale.bc_scale.projected_annual_high)}/yr
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-slate-400">Kamloops / Thompson Nicola region</span>
                    <span className="font-mono text-sm font-bold text-orange-400">
                      {fmtB(scale.kamloops_region.projected_annual_low)} – {fmtB(scale.kamloops_region.projected_annual_high)}/yr
                    </span>
                  </div>
                </div>
                <p className="font-mono text-[10px] text-slate-600 italic mt-4 leading-relaxed">
                  {scale.disclaimer}
                </p>
              </div>
            )}

            {/* Disclaimer */}
            <p className="font-mono text-[10px] text-slate-600 italic mt-6 text-center leading-relaxed">
              {data.disclaimer}
            </p>
          </>
        )}
      </main>

      <footer className="border-t border-ink-600 mt-20 py-8">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <p className="font-mono text-[10px] text-slate-700 uppercase tracking-widest">
            The MCFD Files · Taxpayer Cost Tracker · PC 19700
          </p>
        </div>
      </footer>
    </div>
  )
}
