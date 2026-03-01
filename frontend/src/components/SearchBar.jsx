export default function SearchBar({ value, onChange, onSubmit, onClear, isSearch }) {
  return (
    <form onSubmit={onSubmit}>
      <div className="flex items-center gap-3 bg-ink-700 border border-ink-500 hover:border-ink-400 focus-within:border-amber-500/50 rounded px-4 py-3 transition-colors">

        {/* Terminal prompt glyph */}
        <span className="font-mono text-amber-500/50 text-sm select-none flex-shrink-0">›</span>

        <input
          type="text"
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder="Search decisions, citations, parties…"
          className="flex-1 bg-transparent text-slate-200 placeholder:text-slate-600 outline-none font-mono text-sm min-w-0"
        />

        {isSearch && !value && (
          <span className="hidden sm:inline text-xs font-mono text-amber-500/40 border border-amber-500/20 px-2 py-0.5 rounded flex-shrink-0">
            RESULTS ACTIVE
          </span>
        )}

        {value && (
          <button
            type="button"
            onClick={onClear}
            className="text-slate-600 hover:text-slate-300 font-mono text-lg leading-none transition-colors flex-shrink-0"
            aria-label="Clear search"
          >
            ×
          </button>
        )}

        <button
          type="submit"
          className="flex-shrink-0 bg-amber-500 hover:bg-amber-400 active:bg-amber-600 text-black text-xs font-bold uppercase tracking-widest px-4 py-1.5 rounded transition-colors font-mono"
        >
          SEARCH
        </button>
      </div>
    </form>
  )
}
