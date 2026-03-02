import ReactMarkdown from 'react-markdown'

export default function AskPanel({ question, result, loading, onSelectDecision }) {
  if (loading) {
    return (
      <div className="mt-6">
        <div className="border border-sky-500/20 rounded bg-ink-800/50 p-5">
          <div className="flex items-center gap-3 mb-4">
            <span className="font-mono text-[10px] text-sky-400/60 tracking-widest uppercase">Querying</span>
            <span className="flex gap-1">
              {[0, 1, 2].map(i => (
                <span
                  key={i}
                  className="inline-block w-1 h-1 rounded-full bg-sky-400/60 animate-pulse"
                  style={{ animationDelay: `${i * 200}ms` }}
                />
              ))}
            </span>
          </div>
          <p className="font-mono text-xs text-slate-600 italic">"{question}"</p>
        </div>
      </div>
    )
  }

  if (!result) return null

  return (
    <div className="mt-6 space-y-4">
      {/* Answer block */}
      <div className="border-l-2 border-sky-500/50 pl-4">
        <div className="flex items-center gap-2 mb-3">
          <span className="font-mono text-[10px] text-sky-400/70 tracking-widest uppercase">
            Analysis · {result.chunks_used} source chunks
          </span>
          {result.memory_updated && (
            <span className="font-mono text-[10px] text-emerald-500/50 tracking-widest">
              · R2 ✓
            </span>
          )}
        </div>
        <p className="font-mono text-[10px] text-slate-500 mb-3 italic">"{question}"</p>
        <div className="prose-answer text-sm text-slate-300 leading-relaxed">
          <ReactMarkdown
            components={{
              h1: ({children}) => <h1 className="text-base font-bold text-slate-100 mt-4 mb-2 first:mt-0">{children}</h1>,
              h2: ({children}) => <h2 className="text-sm font-semibold text-slate-200 mt-4 mb-1.5 first:mt-0">{children}</h2>,
              h3: ({children}) => <h3 className="text-sm font-medium text-slate-300 mt-3 mb-1 first:mt-0">{children}</h3>,
              p: ({children}) => <p className="mb-3 last:mb-0">{children}</p>,
              strong: ({children}) => <strong className="font-semibold text-slate-100">{children}</strong>,
              em: ({children}) => <em className="italic text-slate-400">{children}</em>,
              ul: ({children}) => <ul className="mb-3 space-y-1 pl-4 list-disc list-outside">{children}</ul>,
              ol: ({children}) => <ol className="mb-3 space-y-1 pl-4 list-decimal list-outside">{children}</ol>,
              li: ({children}) => <li className="text-slate-300">{children}</li>,
              code: ({children}) => <code className="font-mono text-xs bg-ink-700 text-amber-400/80 px-1 py-0.5 rounded">{children}</code>,
              blockquote: ({children}) => <blockquote className="border-l border-slate-600 pl-3 my-2 text-slate-500 italic">{children}</blockquote>,
            }}
          >
            {result.answer}
          </ReactMarkdown>
        </div>
      </div>

      {/* Sources */}
      {result.sources.length > 0 && (
        <div>
          <p className="font-mono text-[10px] text-slate-600 tracking-widest uppercase mb-2">
            Cited Sources
          </p>
          <div className="space-y-2">
            {result.sources.map(src => (
              <button
                key={src.decision_id}
                onClick={() => onSelectDecision(src.decision_id)}
                className="w-full text-left flex items-start gap-3 border border-ink-600 hover:border-amber-500/30 rounded px-3 py-2.5 bg-ink-800 hover:bg-ink-700 transition-colors group"
              >
                <span className="font-mono text-[10px] text-amber-500/70 group-hover:text-amber-400 transition-colors mt-0.5 flex-shrink-0">
                  [{src.citation}]
                </span>
                <span className="text-xs text-slate-400 group-hover:text-slate-200 transition-colors leading-snug">
                  {src.title}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {result.sources.length === 0 && (
        <p className="font-mono text-[10px] text-slate-700 italic">No directly cited sources extracted.</p>
      )}
    </div>
  )
}
