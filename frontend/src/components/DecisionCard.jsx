function courtAbbr(court) {
  if (court === 'BC Court of Appeal') return 'BCCA'
  if (court === 'BC Supreme Court') return 'BCSC'
  if (court === 'BC Provincial Court') return 'BCPC'
  return court?.split(' ').map(w => w[0]).join('') ?? '—'
}

export default function DecisionCard({ decision, onClick, index }) {
  return (
    <div
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && onClick()}
      className="group flex cursor-pointer animate-fade-up focus:outline-none"
      style={{ animationDelay: `${Math.min(index * 35, 350)}ms` }}
    >
      {/* Accent bar */}
      <div className="w-[3px] flex-shrink-0 rounded-l bg-ink-500 group-hover:bg-amber-500 group-focus:bg-amber-500 transition-colors" />

      {/* Body */}
      <div className="flex-1 bg-ink-800 group-hover:bg-ink-700 group-focus:bg-ink-700 border border-l-0 border-ink-600 group-hover:border-ink-500 rounded-r-lg px-5 py-4 transition-all">

        {/* Top: citation + court badge + date */}
        <div className="flex items-start justify-between gap-4 mb-2">
          <span className="font-mono text-[11px] text-amber-500/80 tracking-wider leading-none mt-0.5">
            {decision.citation ?? '—'}
          </span>
          <div className="flex items-center gap-2.5 flex-shrink-0">
            <span className="font-mono text-[10px] text-slate-600 border border-ink-500 px-1.5 py-0.5 rounded tracking-widest uppercase">
              {courtAbbr(decision.court)}
            </span>
            <span className="font-mono text-[11px] text-slate-500">
              {decision.date ?? '—'}
            </span>
          </div>
        </div>

        {/* Title */}
        <h3 className="text-slate-100 font-medium text-[15px] leading-snug mb-2 group-hover:text-white transition-colors">
          {decision.title}
        </h3>

        {/* Snippet with highlighted marks */}
        {decision.snippet ? (
          <p
            className="text-slate-500 text-sm leading-relaxed line-clamp-2"
            dangerouslySetInnerHTML={{ __html: decision.snippet }}
          />
        ) : (
          <p className="text-slate-700 text-sm italic">No excerpt available.</p>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-ink-600">
          <span className="font-mono text-[10px] text-slate-700 uppercase tracking-widest">
            {decision.source}
          </span>
          <span className="font-mono text-[11px] text-amber-500 tracking-widest opacity-0 group-hover:opacity-100 group-focus:opacity-100 transition-opacity">
            VIEW FILE →
          </span>
        </div>
      </div>
    </div>
  )
}
