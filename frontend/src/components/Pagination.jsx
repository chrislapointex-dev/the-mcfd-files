function getRange(current, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  if (current <= 4) return [1, 2, 3, 4, 5, '…', total]
  if (current >= total - 3) return [1, '…', total - 4, total - 3, total - 2, total - 1, total]
  return [1, '…', current - 1, current, current + 1, '…', total]
}

export default function Pagination({ page, pages, onPageChange }) {
  if (pages <= 1) return null

  const range = getRange(page, pages)
  const btn = 'w-8 h-8 flex items-center justify-center font-mono text-xs rounded transition-colors'

  return (
    <div className="flex items-center justify-center gap-1">

      <button
        onClick={() => onPageChange(page - 1)}
        disabled={page === 1}
        className={`${btn} text-slate-500 hover:text-slate-200 hover:bg-ink-700 disabled:opacity-25 disabled:cursor-not-allowed`}
        aria-label="Previous page"
      >
        ←
      </button>

      {range.map((p, i) =>
        p === '…' ? (
          <span
            key={`ellipsis-${i}`}
            className="w-8 h-8 flex items-center justify-center text-slate-700 font-mono text-xs"
          >
            …
          </span>
        ) : (
          <button
            key={p}
            onClick={() => onPageChange(p)}
            className={`${btn} ${
              p === page
                ? 'bg-amber-500 text-black font-bold'
                : 'text-slate-500 hover:text-slate-200 hover:bg-ink-700'
            }`}
            aria-current={p === page ? 'page' : undefined}
          >
            {p}
          </button>
        )
      )}

      <button
        onClick={() => onPageChange(page + 1)}
        disabled={page === pages}
        className={`${btn} text-slate-500 hover:text-slate-200 hover:bg-ink-700 disabled:opacity-25 disabled:cursor-not-allowed`}
        aria-label="Next page"
      >
        →
      </button>
    </div>
  )
}
