import DOMPurify from 'dompurify'

function courtAbbr(court) {
  if (court === 'BC Court of Appeal') return 'BCCA'
  if (court === 'BC Supreme Court') return 'BCSC'
  if (court === 'BC Provincial Court') return 'BCPC'
  return court?.split(' ').map(w => w[0]).join('') ?? null
}

const PERSONAL_SOURCES = new Set(['foi', 'personal'])

export default function DecisionCard({ decision, onClick, index }) {
  const isRcy = decision.source === 'rcy'
  const isPersonal = PERSONAL_SOURCES.has(decision.source)
  const abbr = isRcy ? 'RCY' : isPersonal ? decision.source.toUpperCase() : courtAbbr(decision.court)

  const accentBar = isPersonal
    ? 'bg-violet-700 group-hover:bg-violet-400 group-focus:bg-violet-400'
    : isRcy
      ? 'bg-teal-700 group-hover:bg-teal-400 group-focus:bg-teal-400'
      : 'bg-ink-500 group-hover:bg-amber-500 group-focus:bg-amber-500'

  const citationColor = isPersonal ? 'text-violet-400/80' : isRcy ? 'text-teal-500/80' : 'text-amber-500/80'
  const badgeColor = isPersonal ? 'text-violet-500 border-violet-900' : isRcy ? 'text-teal-600 border-teal-900' : 'text-slate-600 border-ink-500'
  const viewColor = isPersonal ? 'text-violet-400' : isRcy ? 'text-teal-400' : 'text-amber-500'

  return (
    <div
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && onClick()}
      className="group flex cursor-pointer animate-fade-up focus:outline-none"
      style={{ animationDelay: `${Math.min(index * 35, 350)}ms` }}
    >
      {/* Accent bar — violet for personal, teal for RCY, amber for court decisions */}
      <div className={`w-[3px] flex-shrink-0 rounded-l transition-colors ${accentBar}`} />

      {/* Body */}
      <div className="flex-1 bg-ink-800 group-hover:bg-ink-700 group-focus:bg-ink-700 border border-l-0 border-ink-600 group-hover:border-ink-500 rounded-r-lg px-5 py-4 transition-all">

        {/* Top: citation/source tag + badge + date */}
        <div className="flex items-start justify-between gap-4 mb-2">
          <span className={`font-mono text-[11px] tracking-wider leading-none mt-0.5 ${citationColor}`}>
            {isPersonal ? 'MY FILE' : isRcy ? 'RCY REPORT' : (decision.citation ?? '—')}
          </span>
          <div className="flex items-center gap-2.5 flex-shrink-0">
            {abbr && (
              <span className={`font-mono text-[10px] border px-1.5 py-0.5 rounded tracking-widest uppercase ${badgeColor}`}>
                {abbr}
              </span>
            )}
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
            dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(decision.snippet) }}
          />
        ) : (
          <p className="text-slate-700 text-sm italic">No excerpt available.</p>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-ink-600">
          <span className="font-mono text-[10px] text-slate-700 uppercase tracking-widest">
            {decision.source}
          </span>
          <span className={`font-mono text-[11px] tracking-widest opacity-0 group-hover:opacity-100 group-focus:opacity-100 transition-opacity ${viewColor}`}>
            VIEW FILE →
          </span>
        </div>
      </div>
    </div>
  )
}
