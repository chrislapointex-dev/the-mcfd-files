import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'

const STATUS_STYLES = {
  ACTIVE:  { badge: 'text-amber-400 border-amber-500/40 bg-amber-900/20', dot: 'bg-amber-400' },
  FILED:   { badge: 'text-sky-400 border-sky-500/40 bg-sky-900/20',       dot: 'bg-sky-400' },
  CLOSED:  { badge: 'text-emerald-400 border-emerald-500/40 bg-emerald-900/20', dot: 'bg-emerald-400' },
  STALLED: { badge: 'text-red-400 border-red-500/40 bg-red-900/20',       dot: 'bg-red-400' },
  OPEN:    { badge: 'text-slate-400 border-slate-600 bg-slate-800/20',    dot: 'bg-slate-400' },
}

const STATUS_OPTIONS = ['ACTIVE', 'FILED', 'OPEN', 'STALLED', 'CLOSED']

function StatusBadge({ status }) {
  const s = STATUS_STYLES[status] || STATUS_STYLES.OPEN
  return (
    <span className={`inline-flex items-center gap-1.5 text-[10px] font-mono px-2 py-0.5 rounded border ${s.badge}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
      {status}
    </span>
  )
}

function NotesCell({ id, initial, onSaved }) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(initial || '')
  const inputRef = useRef(null)

  function startEdit() {
    setEditing(true)
    setTimeout(() => inputRef.current?.focus(), 0)
  }

  function save() {
    setEditing(false)
    fetch(`/api/complaints/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes: value || null }),
    })
      .then(r => r.json())
      .then(onSaved)
      .catch(() => {})
  }

  if (editing) {
    return (
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={e => setValue(e.target.value)}
        onBlur={save}
        onKeyDown={e => e.key === 'Enter' && save()}
        className="w-full bg-ink-800 border border-slate-600 rounded px-2 py-1 text-xs font-mono text-slate-200 focus:outline-none focus:border-slate-400"
      />
    )
  }

  return (
    <button
      onClick={startEdit}
      className="text-left text-xs font-mono text-slate-400 hover:text-slate-200 transition-colors w-full"
      title="Click to edit"
    >
      {value || <span className="text-slate-700 italic">add notes…</span>}
    </button>
  )
}

function StatusSelect({ id, current, onSaved }) {
  const [open, setOpen] = useState(false)

  function choose(status) {
    setOpen(false)
    fetch(`/api/complaints/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    })
      .then(r => r.json())
      .then(onSaved)
      .catch(() => {})
  }

  return (
    <div className="relative">
      <button onClick={() => setOpen(o => !o)}>
        <StatusBadge status={current} />
      </button>
      {open && (
        <div className="absolute left-0 top-full mt-1 z-10 bg-ink-800 border border-slate-700 rounded shadow-xl">
          {STATUS_OPTIONS.map(s => (
            <button
              key={s}
              onClick={() => choose(s)}
              className="block w-full text-left px-3 py-1.5 hover:bg-slate-700/50 transition-colors"
            >
              <StatusBadge status={s} />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function copySummary(complaints) {
  const lines = [
    'COMPLAINTS SUMMARY — The MCFD Files',
    `Generated: ${new Date().toISOString().slice(0, 10)}`,
    '',
    ...complaints.map(c =>
      `[${c.status}] ${c.body}${c.file_ref ? ` (${c.file_ref})` : ''} — Filed: ${c.filed_date || 'unknown'}${c.notes ? `\n  Notes: ${c.notes}` : ''}`
    ),
  ]
  navigator.clipboard.writeText(lines.join('\n')).catch(() => {})
}

export default function ComplaintsTracker() {
  const [complaints, setComplaints] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    fetch('/api/complaints')
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then(setComplaints)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  function handleUpdate(updated) {
    setComplaints(prev => prev.map(c => c.id === updated.id ? updated : c))
  }

  function handleCopy() {
    copySummary(complaints)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="min-h-screen bg-ink-900 font-sans text-slate-200">
      <div className="h-px bg-gradient-to-r from-transparent via-red-500/60 to-transparent" />

      <header className="sticky top-0 z-20 border-b border-ink-600 bg-ink-900/90 backdrop-blur-sm">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
          <div>
            <h1 className="font-display text-3xl tracking-[0.12em] text-white leading-none">
              THE MCFD FILES
            </h1>
            <p className="font-mono text-[10px] text-slate-600 tracking-widest mt-1 uppercase">
              Complaints &amp; Oversight Tracker
            </p>
          </div>
          <nav className="flex items-center gap-2 flex-wrap justify-end">
            <Link to="/trial" className="text-[10px] font-mono text-slate-500 border border-slate-700 px-2 py-1 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors hidden sm:block">TRIAL</Link>
            <Link to="/complaints" className="text-[10px] font-mono text-red-400 border border-red-500/40 px-2 py-1 rounded tracking-widest hidden sm:block">COMPLAINTS</Link>
            <span className="text-[10px] font-mono text-amber-500/60 border border-amber-500/25 px-2 py-1 rounded tracking-widest hidden sm:block">UNREDACTED</span>
          </nav>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <span className="font-mono text-[11px] text-slate-500 tracking-widest">
              {complaints.length} OVERSIGHT BODIES
            </span>
            <span className="font-mono text-[11px] text-amber-400">
              {complaints.filter(c => c.status === 'ACTIVE').length} ACTIVE
            </span>
          </div>
          <button
            onClick={handleCopy}
            className="text-[10px] font-mono border border-slate-700 px-3 py-1.5 rounded text-slate-400 hover:text-slate-200 hover:border-slate-500 transition-colors"
          >
            {copied ? 'COPIED ✓' : 'COPY SUMMARY'}
          </button>
        </div>

        {loading && (
          <p className="text-center text-slate-500 font-mono text-sm py-12">Loading…</p>
        )}
        {error && (
          <p className="text-center text-red-400 font-mono text-sm py-12">Error: {error}</p>
        )}

        {!loading && !error && (
          <div className="overflow-x-auto rounded border border-slate-700/60">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700/60 bg-ink-800/40">
                  <th className="text-left px-4 py-3 font-mono text-[10px] text-slate-500 tracking-widest">BODY</th>
                  <th className="text-left px-4 py-3 font-mono text-[10px] text-slate-500 tracking-widest">FILE REF</th>
                  <th className="text-left px-4 py-3 font-mono text-[10px] text-slate-500 tracking-widest">FILED</th>
                  <th className="text-left px-4 py-3 font-mono text-[10px] text-slate-500 tracking-widest">STATUS</th>
                  <th className="text-left px-4 py-3 font-mono text-[10px] text-slate-500 tracking-widest">LAST UPDATE</th>
                  <th className="text-left px-4 py-3 font-mono text-[10px] text-slate-500 tracking-widest">NOTES</th>
                </tr>
              </thead>
              <tbody>
                {complaints.map((c, i) => (
                  <tr
                    key={c.id}
                    className={`border-b border-slate-800/60 ${i % 2 === 0 ? '' : 'bg-slate-800/10'} hover:bg-slate-800/20 transition-colors`}
                  >
                    <td className="px-4 py-3 font-medium text-slate-200 whitespace-nowrap">{c.body}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-400 whitespace-nowrap">
                      {c.file_ref || <span className="text-slate-700">—</span>}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-400 whitespace-nowrap">
                      {c.filed_date || <span className="text-slate-700">—</span>}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <StatusSelect id={c.id} current={c.status} onSaved={handleUpdate} />
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-500 whitespace-nowrap">
                      {c.last_update || <span className="text-slate-700">—</span>}
                    </td>
                    <td className="px-4 py-3 min-w-[200px]">
                      <NotesCell id={c.id} initial={c.notes} onSaved={handleUpdate} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  )
}
