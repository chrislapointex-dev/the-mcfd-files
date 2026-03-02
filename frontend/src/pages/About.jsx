import { Link } from 'react-router-dom'

const STATS = [
  { value: '40%', label: 'MCFD failure rate — their own audits' },
  { value: '2,516', label: 'critical injuries and deaths in a single year' },
  { value: '51 yrs', label: 'of systemic negligence covered by class action' },
  { value: '1,299+', label: 'decisions indexed and searchable' },
]

const TECH = [
  { name: 'FastAPI', desc: 'Async Python backend' },
  { name: 'React 18', desc: 'Frontend + Vite' },
  { name: 'PostgreSQL + pgvector', desc: 'Full-text + vector search' },
  { name: 'Claude AI', desc: 'Synthesized answers with citations' },
  { name: 'R2-D2 Memory', desc: 'Persistent research context across sessions' },
  { name: 'sentence-transformers', desc: 'Local embedding model (all-MiniLM-L6-v2)' },
]

export default function About() {
  return (
    <div className="min-h-screen bg-ink-900 font-sans text-slate-200">

      {/* Top accent line */}
      <div className="h-px bg-gradient-to-r from-transparent via-amber-500/60 to-transparent" />

      {/* Header */}
      <header className="border-b border-ink-600 bg-ink-900/90 backdrop-blur-sm">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="font-display text-xl tracking-[0.12em] text-white hover:text-amber-400 transition-colors">
            THE MCFD FILES
          </Link>
          <nav className="flex items-center gap-2">
            <Link
              to="/"
              className="text-[10px] font-mono text-slate-500 border border-slate-700 px-2 py-1 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors"
            >
              SEARCH
            </Link>
            <span className="text-[10px] font-mono text-amber-500/70 border border-amber-500/30 px-2 py-1 rounded tracking-widest">
              ABOUT
            </span>
          </nav>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-16">

        {/* Title block */}
        <div className="mb-16">
          <h1 className="font-display text-4xl md:text-5xl tracking-[0.08em] text-white leading-tight mb-4">
            THE MCFD FILES
          </h1>
          <p className="text-lg text-slate-400 leading-relaxed max-w-2xl">
            An open-source AI accountability platform for BC child protection.
            Every public court decision, RCY report, news article, and piece of
            legislation involving the Ministry of Children and Family Development
            — searchable, citable, and in one place.
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-ink-600 border border-ink-600 rounded-lg overflow-hidden mb-16">
          {STATS.map(({ value, label }) => (
            <div key={value} className="bg-ink-800 p-5">
              <p className="font-display text-2xl text-amber-400 tracking-wider mb-1">{value}</p>
              <p className="font-mono text-[10px] text-slate-500 leading-snug uppercase tracking-wide">{label}</p>
            </div>
          ))}
        </div>

        {/* Why it exists */}
        <section className="mb-14">
          <h2 className="font-mono text-[10px] text-amber-500/70 tracking-widest uppercase mb-4">
            Why It Exists
          </h2>
          <div className="space-y-4 text-slate-300 leading-relaxed border-l-2 border-amber-500/20 pl-5">
            <p>
              MCFD's own internal audits document a <strong className="text-white">40% failure rate</strong> in
              following their own child protection policies. In one reported year,
              <strong className="text-white"> 2,516 children in their care suffered critical injuries or died</strong>.
              A class action lawsuit spans <strong className="text-white">51 years of systemic negligence</strong>.
            </p>
            <p>
              This information exists — in court filings, oversight reports, legislative records,
              and news archives. But it is scattered across hundreds of disconnected sources,
              written in legal language, and practically inaccessible to the families who need it most.
            </p>
            <p>
              This platform puts it all in one searchable place, with AI that can synthesize
              answers and cite the exact decisions behind them.
            </p>
          </div>
        </section>

        {/* Who it's for */}
        <section className="mb-14">
          <h2 className="font-mono text-[10px] text-amber-500/70 tracking-widest uppercase mb-4">
            Who It's For
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {['Families', 'Lawyers', 'Journalists', 'Oversight Bodies'].map(who => (
              <div key={who} className="border border-ink-600 rounded px-4 py-3 bg-ink-800">
                <p className="font-mono text-xs text-slate-300">{who}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Built by */}
        <section className="mb-14">
          <h2 className="font-mono text-[10px] text-amber-500/70 tracking-widest uppercase mb-4">
            Built By
          </h2>
          <div className="border border-ink-600 rounded bg-ink-800 p-5 text-slate-300 leading-relaxed">
            <p>
              A Canadian Armed Forces veteran building the tool he wished existed when MCFD
              removed his daughter on a provably false affidavit. Built in the margins of
              caregiving, legal proceedings, and everything else that comes with fighting a
              government ministry alone.
            </p>
            <p className="mt-3 font-mono text-xs text-slate-500">
              🍁 Pro Patria
            </p>
          </div>
        </section>

        {/* How it works */}
        <section className="mb-14">
          <h2 className="font-mono text-[10px] text-amber-500/70 tracking-widest uppercase mb-4">
            How to Use It
          </h2>
          <div className="space-y-3">
            {[
              { mode: 'FTS', color: 'text-amber-400 border-amber-500/30', desc: 'Full-text keyword search across all indexed documents. Best for finding specific cases, citations, or names.' },
              { mode: 'VECTOR', color: 'text-violet-400 border-violet-500/30', desc: 'Semantic similarity search. Describe what you\'re looking for in plain language — finds conceptually related content even when the exact words differ.' },
              { mode: 'ASK', color: 'text-sky-400 border-sky-500/30', desc: 'Ask a question in plain English. Claude reads the most relevant documents and synthesizes a cited answer backed by actual court decisions and reports.' },
            ].map(({ mode, color, desc }) => (
              <div key={mode} className="flex gap-4 items-start border border-ink-600 rounded bg-ink-800 p-4">
                <span className={`font-mono text-[10px] border px-2 py-1 rounded flex-shrink-0 mt-0.5 ${color}`}>
                  {mode}
                </span>
                <p className="text-sm text-slate-400 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Open source */}
        <section className="mb-14">
          <h2 className="font-mono text-[10px] text-amber-500/70 tracking-widest uppercase mb-4">
            Open Source
          </h2>
          <div className="border border-ink-600 rounded bg-ink-800 p-5 flex items-center justify-between gap-4">
            <div>
              <p className="text-sm text-slate-300 mb-1">MIT License — free to use, fork, and build on.</p>
              <p className="font-mono text-[10px] text-slate-600">github.com/chrislapointex-dev/the-mcfd-files</p>
            </div>
            <a
              href="https://github.com/chrislapointex-dev/the-mcfd-files"
              target="_blank"
              rel="noopener noreferrer"
              className="flex-shrink-0 font-mono text-[10px] tracking-widest border border-slate-600 text-slate-400 hover:text-white hover:border-slate-400 px-3 py-2 rounded transition-colors"
            >
              GITHUB ↗
            </a>
          </div>
        </section>

        {/* Tech stack */}
        <section className="mb-16">
          <h2 className="font-mono text-[10px] text-amber-500/70 tracking-widest uppercase mb-4">
            Built With
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {TECH.map(({ name, desc }) => (
              <div key={name} className="border border-ink-600 rounded bg-ink-800 px-3 py-2.5">
                <p className="font-mono text-xs text-slate-200 mb-0.5">{name}</p>
                <p className="font-mono text-[10px] text-slate-600">{desc}</p>
              </div>
            ))}
          </div>
        </section>

      </main>

      {/* Footer */}
      <footer className="border-t border-ink-600 py-10">
        <div className="max-w-3xl mx-auto px-6 text-center space-y-2">
          <p className="font-mono text-sm text-slate-500 italic">
            "Because sunlight is the best disinfectant."
          </p>
          <p className="font-mono text-[10px] text-slate-700 tracking-widest uppercase">
            🍁 Pro Patria · The MCFD Files · MIT License
          </p>
        </div>
      </footer>

    </div>
  )
}
