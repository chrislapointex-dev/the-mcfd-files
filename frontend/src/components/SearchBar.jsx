export default function SearchBar({ value, onChange, onSubmit, onClear, isSearch, mode = 'search' }) {
  const isAsk = mode === 'ask'
  const placeholder = isAsk
    ? 'Ask a question about BC court decisions…'
    : 'Search decisions, citations, parties…'
  const focusBorder = isAsk ? 'focus-within:border-sky-500/50' : 'focus-within:border-amber-500/50'
  const promptColor = isAsk ? 'text-sky-400/50' : 'text-amber-500/50'

  return (
    <form onSubmit={onSubmit}>
      <div className={`flex items-center gap-3 bg-ink-700 border border-ink-500 hover:border-ink-400 ${focusBorder} rounded px-4 py-3 transition-colors`}>

        {/* Terminal prompt glyph */}
        <span className={`font-mono ${promptColor} text-sm select-none flex-shrink-0`}>›</span>

        <input
          type="text"
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          className="flex-1 bg-transparent text-slate-200 placeholder:text-slate-600 outline-none font-mono text-sm min-w-0"
        />

        {isSearch && !value && !isAsk && (
          <span className="hidden sm:inline text-xs font-mono text-amber-500/40 border border-amber-500/20 px-2 py-0.5 rounded flex-shrink-0">
            RESULTS ACTIVE
          </span>
        )}

        {value && (
          <button
            type="button"
            onClick={onClear}
            className="text-slate-600 hover:text-slate-300 font-mono text-lg leading-none transition-colors flex-shrink-0"
            aria-label="Clear"
          >
            ×
          </button>
        )}

        <button
          type="submit"
          className={`flex-shrink-0 text-black text-xs font-bold uppercase tracking-widest px-4 py-1.5 rounded transition-colors font-mono ${
            isAsk
              ? 'bg-sky-400 hover:bg-sky-300 active:bg-sky-500'
              : 'bg-amber-500 hover:bg-amber-400 active:bg-amber-600'
          }`}
        >
          {isAsk ? 'ASK' : 'SEARCH'}
        </button>
      </div>
    </form>
  )
}
