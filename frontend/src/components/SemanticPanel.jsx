export default function SemanticPanel({ query, results, loading, onSelectDecision }) {
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
          Vector · {results.total} chunks
        </span>
        <span className="font-mono text-[10px] text-slate-600 italic">"{query}"</span>
      </div>

      {results.results.length === 0 && (
        <p className="font-mono text-xs text-slate-600 py-12 text-center">
          No similar chunks found. Try a lower threshold or different phrasing.
        </p>
      )}

      {results.results.map(chunk => (
        <button
          key={chunk.chunk_id}
          onClick={() => onSelectDecision(chunk.decision_id)}
          className="w-full text-left border border-ink-600 hover:border-violet-500/30 rounded bg-ink-800 hover:bg-ink-700 transition-colors group p-4"
        >
          {/* Top row: score + citation + date */}
          <div className="flex items-center gap-3 mb-2">
            <ScoreBadge score={chunk.score} />
            <span className="font-mono text-[10px] text-amber-500/70 group-hover:text-amber-400 transition-colors">
              {chunk.citation || `Decision #${chunk.decision_id}`}
            </span>
            {chunk.date && (
              <span className="font-mono text-[10px] text-slate-600 ml-auto flex-shrink-0">
                {chunk.date}
              </span>
            )}
          </div>

          {/* Title */}
          <p className="text-xs font-medium text-slate-300 group-hover:text-slate-100 transition-colors mb-2 leading-snug">
            {chunk.title}
          </p>

          {/* Chunk text excerpt */}
          <p className="text-xs text-slate-500 group-hover:text-slate-400 transition-colors leading-relaxed line-clamp-3">
            {chunk.text}
          </p>

          {/* Footer: court + chunk num */}
          <div className="flex items-center gap-3 mt-2">
            {chunk.court && (
              <span className="font-mono text-[9px] text-slate-700 uppercase tracking-wider">
                {chunk.court}
              </span>
            )}
            <span className="font-mono text-[9px] text-slate-700 ml-auto">
              chunk {chunk.chunk_num}
            </span>
          </div>
        </button>
      ))}
    </div>
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
