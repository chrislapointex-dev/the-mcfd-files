export default function SearchBar({ value, onChange, onSubmit, onClear, isSearch, mode = 'search' }) {
  const placeholders = {
    search:   'Search decisions, citations, parties…',
    semantic: 'Describe what you\'re looking for…',
    ask:      'Ask a question about BC court decisions…',
  }
  const focusBorders = {
    search:   'focus-within:border-amber-500/50',
    semantic: 'focus-within:border-violet-500/50',
    ask:      'focus-within:border-sky-500/50',
  }
  const promptColors = {
    search:   'text-amber-500/50',
    semantic: 'text-violet-400/50',
    ask:      'text-sky-400/50',
  }
  const submitStyles = {
    search:   'bg-amber-500 hover:bg-amber-400 active:bg-amber-600',
    semantic: 'bg-violet-500 hover:bg-violet-400 active:bg-violet-600',
    ask:      'bg-sky-400 hover:bg-sky-300 active:bg-sky-500',
  }
  const submitLabels = { search: 'SEARCH', semantic: 'VECTOR', ask: 'ASK' }

  return (
    <form onSubmit={onSubmit}>
      <div className={`flex items-center gap-3 bg-ink-700 border border-ink-500 hover:border-ink-400 ${focusBorders[mode]} rounded px-4 py-3 transition-colors`}>

        <span className={`font-mono ${promptColors[mode]} text-sm select-none flex-shrink-0`}>›</span>

        <input
          type="text"
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholders[mode]}
          className="flex-1 bg-transparent text-slate-200 placeholder:text-slate-600 outline-none font-mono text-sm min-w-0"
        />

        {isSearch && !value && mode === 'search' && (
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
          className={`flex-shrink-0 text-black text-xs font-bold uppercase tracking-widest px-4 py-1.5 rounded transition-colors font-mono ${submitStyles[mode]}`}
        >
          {submitLabels[mode]}
        </button>
      </div>
    </form>
  )
}
