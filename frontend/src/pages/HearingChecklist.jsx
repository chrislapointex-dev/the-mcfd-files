import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'

const CATEGORY_STYLES = {
  EVIDENCE:  { bar: 'bg-amber-500',  label: 'text-amber-400',  border: 'border-amber-500/30',  bg: 'bg-amber-900/10' },
  FILINGS:   { bar: 'bg-violet-500', label: 'text-violet-400', border: 'border-violet-500/30', bg: 'bg-violet-900/10' },
  WITNESSES: { bar: 'bg-sky-500',    label: 'text-sky-400',    border: 'border-sky-500/30',    bg: 'bg-sky-900/10' },
  LOGISTICS: { bar: 'bg-slate-400',  label: 'text-slate-400',  border: 'border-slate-600',     bg: 'bg-slate-800/20' },
}

const CATEGORY_ORDER = ['EVIDENCE', 'FILINGS', 'WITNESSES', 'LOGISTICS']

function NotesField({ itemId, initial, onSaved }) {
  const [value, setValue] = useState(initial || '')
  const timerRef = useRef(null)

  function handleChange(e) {
    setValue(e.target.value)
  }

  function handleBlur() {
    clearTimeout(timerRef.current)
    save(value)
  }

  function save(notes) {
    fetch(`/api/checklist/${itemId}/notes`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes: notes || null }),
    })
      .then(r => r.json())
      .then(onSaved)
      .catch(() => {})
  }

  return (
    <input
      type="text"
      value={value}
      onChange={handleChange}
      onBlur={handleBlur}
      placeholder="add notes…"
      className="mt-1 w-full bg-transparent border-b border-slate-700 text-[11px] font-mono text-slate-500 placeholder-slate-700 focus:outline-none focus:border-slate-500 focus:text-slate-300 transition-colors"
    />
  )
}

function ChecklistRow({ item, onToggle, onNotesSaved }) {
  const [toggling, setToggling] = useState(false)

  function handleToggle() {
    if (toggling) return
    setToggling(true)
    fetch(`/api/checklist/${item.id}/toggle`, { method: 'PATCH' })
      .then(r => r.json())
      .then(updated => { onToggle(updated); setToggling(false) })
      .catch(() => setToggling(false))
  }

  return (
    <div className={`flex flex-col gap-1 px-3 py-2 border-b border-slate-800/60 ${item.done ? 'opacity-50' : ''}`}>
      <div className="flex items-start gap-3">
        <button
          onClick={handleToggle}
          disabled={toggling}
          className={`mt-0.5 w-4 h-4 shrink-0 rounded border ${item.done ? 'bg-emerald-500 border-emerald-500' : 'border-slate-600 bg-transparent hover:border-slate-400'} flex items-center justify-center transition-colors`}
          aria-label="Toggle"
        >
          {item.done && (
            <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 12 12">
              <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          )}
        </button>
        <span className={`text-sm leading-snug ${item.done ? 'line-through text-slate-600' : 'text-slate-200'}`}>
          {item.item}
        </span>
      </div>
      <div className="pl-7">
        <NotesField itemId={item.id} initial={item.notes} onSaved={onNotesSaved} />
      </div>
    </div>
  )
}

function CategoryBlock({ category, items, onToggle, onNotesSaved }) {
  const style = CATEGORY_STYLES[category] || CATEGORY_STYLES.LOGISTICS
  const done = items.filter(i => i.done).length
  const total = items.length
  const pct = total > 0 ? Math.round((done / total) * 100) : 0

  return (
    <div className={`rounded border ${style.border} ${style.bg} overflow-hidden`}>
      <div className="px-3 py-2 flex items-center justify-between gap-4">
        <span className={`text-[11px] font-mono tracking-widest font-semibold ${style.label}`}>
          {category}
        </span>
        <div className="flex items-center gap-2 flex-1">
          <div className="flex-1 h-1 bg-slate-800 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-300 ${style.bar}`}
              style={{ width: `${pct}%` }}
            />
          </div>
          <span className="text-[10px] font-mono text-slate-500 shrink-0">{done}/{total}</span>
        </div>
      </div>
      <div>
        {items.map(item => (
          <ChecklistRow
            key={item.id}
            item={item}
            onToggle={onToggle}
            onNotesSaved={onNotesSaved}
          />
        ))}
      </div>
    </div>
  )
}

export default function HearingChecklist() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/api/checklist')
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then(setItems)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  function handleToggle(updated) {
    setItems(prev => prev.map(i => i.id === updated.id ? updated : i))
  }

  function handleNotesSaved(updated) {
    setItems(prev => prev.map(i => i.id === updated.id ? updated : i))
  }

  const totalDone = items.filter(i => i.done).length
  const totalAll = items.length

  const grouped = CATEGORY_ORDER.reduce((acc, cat) => {
    acc[cat] = items.filter(i => i.category === cat)
    return acc
  }, {})

  return (
    <div className="min-h-screen bg-ink-900 font-sans text-slate-200">
      <div className="h-px bg-gradient-to-r from-transparent via-red-500/60 to-transparent" />

      <header className="sticky top-0 z-20 border-b border-ink-600 bg-ink-900/90 backdrop-blur-sm">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
          <div>
            <h1 className="font-display text-3xl tracking-[0.12em] text-white leading-none">
              THE MCFD FILES
            </h1>
            <p className="font-mono text-[10px] text-slate-600 tracking-widest mt-1 uppercase">
              Hearing Prep Checklist · May 19–21, 2026
            </p>
          </div>
          <nav className="flex items-center gap-2 flex-wrap justify-end">
            <Link to="/trial" className="text-[10px] font-mono text-slate-500 border border-slate-700 px-2 py-1 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors hidden sm:block">TRIAL</Link>
            <Link to="/checklist" className="text-[10px] font-mono text-red-400 border border-red-500/40 px-2 py-1 rounded tracking-widest hidden sm:block">CHECKLIST</Link>
            <span className="text-[10px] font-mono text-amber-500/60 border border-amber-500/25 px-2 py-1 rounded tracking-widest hidden sm:block">UNREDACTED</span>
          </nav>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6 space-y-4">
        {/* Overall progress */}
        <div className="flex items-center gap-4 px-3 py-3 rounded border border-slate-700 bg-slate-800/20">
          <span className="font-mono text-[11px] text-slate-400 tracking-widest">OVERALL PROGRESS</span>
          <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-emerald-500 rounded-full transition-all duration-300"
              style={{ width: totalAll > 0 ? `${Math.round((totalDone / totalAll) * 100)}%` : '0%' }}
            />
          </div>
          <span className="font-mono text-sm text-emerald-400 shrink-0">{totalDone} of {totalAll}</span>
        </div>

        {loading && (
          <p className="text-center text-slate-500 font-mono text-sm py-12">Loading checklist…</p>
        )}
        {error && (
          <p className="text-center text-red-400 font-mono text-sm py-12">Error: {error}</p>
        )}

        {!loading && !error && CATEGORY_ORDER.map(cat => (
          grouped[cat]?.length > 0 && (
            <CategoryBlock
              key={cat}
              category={cat}
              items={grouped[cat]}
              onToggle={handleToggle}
              onNotesSaved={handleNotesSaved}
            />
          )
        ))}
      </main>
    </div>
  )
}
