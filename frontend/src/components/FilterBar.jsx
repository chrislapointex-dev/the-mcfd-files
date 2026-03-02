const selectCls =
  'bg-ink-700 border border-ink-500 text-slate-300 text-xs font-mono px-3 py-1.5 rounded outline-none hover:border-ink-400 focus:border-amber-500/50 transition-colors cursor-pointer appearance-none'

const inputCls =
  'w-[4.5rem] bg-ink-700 border border-ink-500 text-slate-300 text-xs font-mono px-2 py-1.5 rounded outline-none hover:border-ink-400 focus:border-amber-500/50 transition-colors text-center'

const SOURCE_LABELS = {
  bccourts: 'COURT DECISIONS',
  rcy: 'RCY REPORTS',
}

export default function FilterBar({
  filters,
  onChange,
  sources,
  courts,
  yearMin,
  yearMax,
  total,
  isSearch,
  query,
  loading,
}) {
  const set = (field, val) => onChange({ ...filters, [field]: val })
  const hasFilters = filters.source || filters.court || filters.dateFrom || filters.dateTo

  return (
    <div>
      {/* Source tabs — shown in search mode when multiple sources exist */}
      {isSearch && sources.length > 1 && (
        <div className="flex items-center gap-1 pt-4 pb-3 border-b border-ink-700">
          {[{ value: '', label: 'ALL' }, ...sources.map(s => ({ value: s, label: SOURCE_LABELS[s] ?? s.toUpperCase() }))].map(({ value, label }) => {
            const active = filters.source === value
            return (
              <button
                key={value}
                onClick={() => set('source', value)}
                className={`font-mono text-[11px] tracking-widest px-3 py-1 rounded transition-colors ${
                  active
                    ? value === 'rcy'
                      ? 'bg-teal-900/60 text-teal-400 border border-teal-700/60'
                      : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                    : 'text-slate-600 hover:text-slate-400 border border-transparent'
                }`}
              >
                {label}
              </button>
            )
          })}
        </div>
      )}

      {/* Main filter row */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 py-4 border-b border-ink-600">

        {/* Results count — left-anchored */}
        <div className="text-xs font-mono text-slate-500 mr-auto">
          {loading ? (
            <span className="text-slate-600 animate-pulse">SCANNING…</span>
          ) : isSearch ? (
            <>
              <span className="text-amber-500">{total.toLocaleString()}</span>
              {' '}RESULTS
              {query && <span className="text-slate-600"> · &ldquo;{query}&rdquo;</span>}
            </>
          ) : (
            <>
              <span className="text-amber-500">{total.toLocaleString()}</span>
              {' '}DECISIONS ON RECORD
            </>
          )}
        </div>

        {/* Source dropdown — browse mode only (search uses tabs above) */}
        {!isSearch && sources.length > 1 && (
          <select
            value={filters.source}
            onChange={e => set('source', e.target.value)}
            className={selectCls}
          >
            <option value="">ALL SOURCES</option>
            {sources.map(s => (
              <option key={s} value={s}>{SOURCE_LABELS[s] ?? s.toUpperCase()}</option>
            ))}
          </select>
        )}

        {/* Court filter — only show when not filtered to rcy (no courts) */}
        {filters.source !== 'rcy' && (
          <select
            value={filters.court}
            onChange={e => set('court', e.target.value)}
            className={selectCls}
          >
            <option value="">ALL COURTS</option>
            {courts.map(c => (
              <option key={c} value={c}>
                {c === 'BC Court of Appeal' ? 'BC COURT OF APPEAL' : c.toUpperCase()}
              </option>
            ))}
          </select>
        )}

        {/* Year range */}
        <div className="flex items-center gap-1.5 text-xs font-mono text-slate-600">
          <span>YEAR</span>
          <input
            type="number"
            placeholder={yearMin ?? 'YYYY'}
            min={yearMin}
            max={yearMax}
            value={filters.dateFrom ? filters.dateFrom.slice(0, 4) : ''}
            onChange={e => set('dateFrom', e.target.value ? `${e.target.value}-01-01` : '')}
            className={inputCls}
          />
          <span>–</span>
          <input
            type="number"
            placeholder={yearMax ?? 'YYYY'}
            min={yearMin}
            max={yearMax}
            value={filters.dateTo ? filters.dateTo.slice(0, 4) : ''}
            onChange={e => set('dateTo', e.target.value ? `${e.target.value}-12-31` : '')}
            className={inputCls}
          />
        </div>

        {/* Clear filters */}
        {hasFilters && (
          <button
            onClick={() => onChange({ source: '', court: '', dateFrom: '', dateTo: '' })}
            className="text-xs font-mono text-slate-600 hover:text-amber-500 transition-colors"
          >
            CLEAR ×
          </button>
        )}
      </div>
    </div>
  )
}
