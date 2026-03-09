import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

const CATEGORY_LABELS = {
  supervision: 'SUPERVISION',
  placement: 'PLACEMENT',
  legal: 'LEGAL',
  court: 'COURT',
  administration: 'ADMINISTRATION',
}

const CATEGORY_COLORS = {
  supervision: 'text-amber-400 border-amber-500/30',
  placement: 'text-violet-400 border-violet-500/30',
  legal: 'text-red-400 border-red-500/30',
  court: 'text-red-500 border-red-600/40',
  administration: 'text-slate-400 border-slate-600/40',
}

export default function CostCalculator() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/api/costs')
      .then(r => r.json())
      .then(setData)
      .catch(() => setError('Failed to load cost data'))
      .finally(() => setLoading(false))
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
                ${data.grand_total.toLocaleString('en-CA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
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
                    Subtotal: <span className="text-white font-bold">${catData.subtotal.toLocaleString('en-CA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
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
                          <p className="font-mono text-[10px] text-slate-600 mt-0.5">{item.source}</p>
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
                            {item.total === 0 ? 'ON RECORD' : `$${item.total.toLocaleString('en-CA', { minimumFractionDigits: 2 })}`}
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
                ${data.grand_total.toLocaleString('en-CA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>

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
