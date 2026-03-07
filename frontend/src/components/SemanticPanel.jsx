import { useState, useMemo } from 'react'

const PERSONAL_SOURCES = new Set(['foi', 'personal'])

function SourceBadge({ source }) {
  if (!source) return null
  const color = PERSONAL_SOURCES.has(source)
    ? 'text-violet-400/70 border-violet-500/20'
    : source === 'rcy'
      ? 'text-teal-400/70 border-teal-500/20'
      : 'text-amber-400/50 border-amber-500/20'
  return (
    <span className={`font-mono text-[9px] border px-1 py-0.5 rounded tracking-widest uppercase ${color}`}>
      {source}
    </span>
  )
}

function ScoreBadge({ score }) {
  const pct = Math.round(score * 100)
  const color =
    score >= 0.70 ? 'text-emerald-400 border-emerald-500/30' :
    score >= 0.50 ? 'text-amber-400 border-amber-500/30' :
                   'text-slate-500 border-slate-600'
  return (
    <span className={`font-mono text-[10px] border px-1.5 py-0.5 rounded flex-shrink-0 ${color}`}>
      {pct}%
    </span>
  )
}

export default function SemanticPanel({ query, results, loading, onSelectDecision }) {
  const [expandedIds, setExpandedIds] = useState(new Set())

  // Group chunks by decision_id, preserving order by best-chunk score
  const grouped = useMemo(() => {
    if (!results) return []
    const seen = new Map()
    const groups = []
    for (const chunk of results.results) {
      if (!seen.has(chunk.decision_id)) {
        const g = { decision_id: chunk.decision_id, best: chunk, extra: [] }
        seen.set(chunk.decision_id, g)
        groups.push(g)
      } else {
        seen.get(chunk.decision_id).extra.push(chunk)
      }
    }
    return groups
  }, [results])

  const toggleExpand = (id) => setExpandedIds(prev => {
    const next = new Set(prev)
    if (next.has(id)) next.delete(id); else next.add(id)
    return next
  })

  if (loading) {
    return (
      <div className="mt-6">
        <div className="border border-violet-500/20 rounded bg-ink-800/50 p-5">
          <div className="flex items-center gap-3 mb-4">
            <span className="font-mono text-[10px] text-violet-400/60 tracking-widest uppercase">Embedding</span>
            <span className="flex gap-1">
              {[0, 1, 2].map(i => (
                <span
                  key={i}
                  className="inline-block w-1 h-1 rounded-full bg-violet-400/60 animate-pulse"
                  style={{ animationDelay: `${i * 200}ms` }}
                />
              ))}
            </span>
          </div>
          <p className="font-mono text-xs text-slate-600 italic">"{query}"</p>
        </div>
      </div>
    )
  }

  if (!results) return null

  return (
    <div className="mt-6 space-y-3">
      {/* Header */}
      <div className="flex items-center gap-3">
        <span className="font-mono text-[10px] text-violet-400/70 tracking-widest uppercase">
          Vector · {grouped.length} decisions · {results.total} chunks
        </span>
        <span className="font-mono text-[10px] text-slate-600 italic">"{query}"</span>
      </div>

      {grouped.length === 0 && (
        <p className="font-mono text-xs text-slate-600 py-12 text-center">
          No similar chunks found. Try a lower threshold or different phrasing.
        </p>
      )}

      {grouped.map(({ decision_id, best, extra }) => {
        const isExpanded = expandedIds.has(decision_id)
        return (
          <div key={decision_id} className="border border-ink-600 hover:border-violet-500/30 rounded bg-ink-800 transition-colors">

            {/* Best chunk — click to open decision */}
            <button
              onClick={() => onSelectDecision(decision_id)}
              className="w-full text-left p-4 group"
            >
              <div className="flex items-center gap-3 mb-2">
                <ScoreBadge score={best.score} />
                <SourceBadge source={best.source} />
                <span className="font-mono text-[10px] text-amber-500/70 group-hover:text-amber-400 transition-colors">
                  {best.citation || `Decision #${decision_id}`}
                </span>
                {best.date && (
                  <span className="font-mono text-[10px] text-slate-600 ml-auto flex-shrink-0">
                    {best.date}
                  </span>
                )}
              </div>
              <p className="text-xs font-medium text-slate-300 group-hover:text-slate-100 transition-colors mb-2 leading-snug">
                {best.title}
              </p>
              <p className="text-xs text-slate-500 group-hover:text-slate-400 transition-colors leading-relaxed line-clamp-3">
                {best.text}
              </p>
              <div className="flex items-center gap-3 mt-2">
                {best.court && (
                  <span className="font-mono text-[9px] text-slate-700 uppercase tracking-wider">
                    {best.court}
                  </span>
                )}
                <span className="font-mono text-[9px] text-slate-700 ml-auto">
                  chunk {best.chunk_num}
                </span>
              </div>
            </button>

            {/* Expand toggle for additional chunks */}
            {extra.length > 0 && (
              <div className="border-t border-ink-600/50">
                <button
                  onClick={() => toggleExpand(decision_id)}
                  className="w-full px-4 py-2 text-left font-mono text-[10px] text-slate-600 hover:text-violet-400 transition-colors flex items-center gap-2"
                >
                  <span>{isExpanded ? '▾' : '▸'}</span>
                  <span>
                    {isExpanded ? 'Hide' : 'Show'} {extra.length} more excerpt{extra.length > 1 ? 's' : ''}
                  </span>
                </button>
                {isExpanded && (
                  <div className="px-4 pb-3 space-y-2">
                    {extra.map(chunk => (
                      <button
                        key={chunk.chunk_id}
                        onClick={() => onSelectDecision(chunk.decision_id)}
                        className="w-full text-left border border-ink-600/50 rounded p-3 hover:border-violet-500/20 hover:bg-ink-700 transition-colors group"
                      >
                        <div className="flex items-center gap-2 mb-1.5">
                          <ScoreBadge score={chunk.score} />
                          <span className="font-mono text-[9px] text-slate-700">chunk {chunk.chunk_num}</span>
                        </div>
                        <p className="text-xs text-slate-500 group-hover:text-slate-400 transition-colors leading-relaxed line-clamp-3">
                          {chunk.text}
                        </p>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
