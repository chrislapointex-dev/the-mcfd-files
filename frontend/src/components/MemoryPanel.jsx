import { useState, useEffect } from 'react'

const REGION_META = {
  CORTEX:      { label: 'CORTEX',      desc: 'Active working memory',  color: 'text-amber-400',  border: 'border-amber-500/30',  bg: 'bg-amber-500/5'  },
  HIPPOCAMPUS: { label: 'HIPPOCAMPUS', desc: 'Recent history',         color: 'text-sky-400',    border: 'border-sky-500/30',    bg: 'bg-sky-500/5'    },
  NEOCORTEX:   { label: 'NEOCORTEX',   desc: 'Long-term knowledge',    color: 'text-violet-400', border: 'border-violet-500/30', bg: 'bg-violet-500/5' },
  AMYGDALA:    { label: 'AMYGDALA',    desc: 'Alerts & red flags',     color: 'text-red-400',    border: 'border-red-500/30',    bg: 'bg-red-500/5'    },
  PREFRONTAL:  { label: 'PREFRONTAL',  desc: 'Goals & plans',          color: 'text-emerald-400',border: 'border-emerald-500/30',bg: 'bg-emerald-500/5'},
}

const CATEGORY_ICONS = {
  search_query:     '›',
  viewed_decision:  '◈',
  red_flag:         '⚑',
  goal:             '◎',
  plan:             '◎',
  note:             '·',
}

function MemoryRow({ row }) {
  const icon = CATEGORY_ICONS[row.category] || '·'
  const val = row.value

  let label = row.key
  let detail = null

  if (row.category === 'search_query') {
    label = `"${val.query ?? row.key}"`
    detail = `${val.result_count ?? '?'} results`
  } else if (row.category === 'viewed_decision') {
    label = val.title ?? row.key
    detail = val.citation ?? null
  } else if (row.category === 'red_flag') {
    label = row.key
    detail = val.reason ?? null
  } else if (row.category === 'goal' || row.category === 'plan') {
    label = val.description ?? row.key
  } else if (val.data) {
    label = String(val.data).slice(0, 100)
  }

  const ts = row.created_at
    ? new Date(row.created_at).toLocaleString('en-CA', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false })
    : null

  return (
    <div className="flex items-start gap-2 py-1.5 border-b border-ink-700/40 last:border-0">
      <span className="text-slate-600 font-mono text-xs w-3 flex-shrink-0 pt-px">{icon}</span>
      <div className="flex-1 min-w-0">
        <p className="font-mono text-xs text-slate-300 leading-snug truncate">{label}</p>
        {detail && <p className="font-mono text-[10px] text-slate-600 mt-0.5">{detail}</p>}
      </div>
      {ts && <span className="font-mono text-[9px] text-slate-700 flex-shrink-0 pt-px">{ts}</span>}
    </div>
  )
}

function RegionBlock({ region, rows }) {
  const meta = REGION_META[region] ?? {
    label: region, desc: '', color: 'text-slate-400', border: 'border-slate-700', bg: 'bg-slate-800/20',
  }
  return (
    <div className={`rounded border ${meta.border} ${meta.bg} px-3 py-2 mb-3`}>
      <div className="flex items-baseline gap-2 mb-2">
        <span className={`font-mono text-[10px] font-bold tracking-widest ${meta.color}`}>{meta.label}</span>
        <span className="font-mono text-[9px] text-slate-700 tracking-wide">{meta.desc}</span>
        <span className="ml-auto font-mono text-[9px] text-slate-600">{rows.length}</span>
      </div>
      <div>
        {rows.map(r => <MemoryRow key={r.id} row={r} />)}
      </div>
    </div>
  )
}

export default function MemoryPanel({ onClose }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [tab, setTab] = useState('regions') // 'regions' | 'raw' | 'briefing'

  const load = () => {
    setLoading(true)
    fetch('/api/memory/context?limit_per_region=10')
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }

  useEffect(() => { load() }, [])

  const regionOrder = ['CORTEX', 'PREFRONTAL', 'AMYGDALA', 'HIPPOCAMPUS', 'NEOCORTEX']

  return (
    <div className="fixed inset-0 z-50 flex justify-end" onClick={onClose}>
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60" />

      {/* Panel */}
      <div
        className="relative w-full max-w-md h-full bg-ink-900 border-l border-ink-600 flex flex-col shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-ink-600 flex-shrink-0">
          <div>
            <span className="font-mono text-xs tracking-widest text-amber-400 font-bold">R2 MEMORY</span>
            <span className="font-mono text-[9px] text-slate-600 ml-2 tracking-wide">PERSISTENT CONTEXT ENGINE</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={load}
              className="font-mono text-[9px] text-slate-600 hover:text-slate-400 tracking-widest transition-colors"
            >
              REFRESH
            </button>
            <button
              onClick={onClose}
              className="font-mono text-xs text-slate-600 hover:text-slate-300 transition-colors px-1"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-ink-600 flex-shrink-0">
          {[['regions', 'REGIONS'], ['briefing', 'BRIEFING'], ['raw', 'RAW']].map(([key, lbl]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`flex-1 font-mono text-[10px] tracking-widest py-2 transition-colors border-b-2 ${
                tab === key
                  ? 'text-amber-400 border-amber-500'
                  : 'text-slate-600 border-transparent hover:text-slate-400'
              }`}
            >
              {lbl}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-4 py-4">
          {loading && (
            <div className="font-mono text-xs text-slate-600 text-center py-10 animate-pulse">
              READING MEMORY…
            </div>
          )}
          {error && (
            <div className="font-mono text-xs text-red-400 text-center py-10">
              ERROR: {error}
            </div>
          )}

          {!loading && data && tab === 'regions' && (
            <div>
              {regionOrder
                .filter(r => data.regions[r]?.length)
                .map(r => (
                  <RegionBlock key={r} region={r} rows={data.regions[r]} />
                ))}
              {Object.keys(data.regions).length === 0 && (
                <p className="font-mono text-xs text-slate-600 text-center py-10">
                  No memories yet. Run a search.
                </p>
              )}
            </div>
          )}

          {!loading && data && tab === 'briefing' && (
            <pre className="font-mono text-[10px] text-slate-400 leading-relaxed whitespace-pre-wrap">
              {data.briefing || '// empty'}
            </pre>
          )}

          {!loading && data && tab === 'raw' && (
            <pre className="font-mono text-[10px] text-slate-500 leading-relaxed whitespace-pre-wrap break-all">
              {JSON.stringify(data.regions, null, 2)}
            </pre>
          )}
        </div>

        {/* Footer */}
        {!loading && data && (
          <div className="border-t border-ink-600 px-4 py-2 flex-shrink-0">
            <span className="font-mono text-[9px] text-slate-700 tracking-widest">
              {Object.values(data.regions).reduce((n, rows) => n + rows.length, 0)} MEMORIES ACROSS{' '}
              {Object.keys(data.regions).length} REGIONS
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
