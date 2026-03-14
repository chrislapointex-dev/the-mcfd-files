import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'

const STATUS_COLORS = {
  IDLE: 'text-slate-500 border-slate-700',
  RUNNING: 'text-cyan-400 border-cyan-500/40 animate-pulse',
  COMPLETED: 'text-emerald-400 border-emerald-500/40',
  ERROR: 'text-red-400 border-red-500/40',
  SCHEDULED: 'text-amber-400 border-amber-500/40',
}

function StatusBadge({ status }) {
  return (
    <span className={`font-mono text-[10px] border px-2 py-0.5 rounded tracking-widest ${STATUS_COLORS[status] || STATUS_COLORS.IDLE}`}>
      {status}
    </span>
  )
}

function AgentCard({ agent }) {
  return (
    <div className="bg-ink-800 border border-ink-600 rounded-lg p-4 space-y-2">
      <div className="flex items-center justify-between">
        <span className="font-mono text-xs text-white tracking-widest uppercase">{agent.name}</span>
        <StatusBadge status={agent.status} />
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1">
        <span className="font-mono text-[10px] text-slate-600">FOUND</span>
        <span className="font-mono text-[10px] text-slate-400">{agent.records_found}</span>
        <span className="font-mono text-[10px] text-slate-600">ADDED</span>
        <span className="font-mono text-[10px] text-emerald-400">{agent.records_added}</span>
        <span className="font-mono text-[10px] text-slate-600">ERRORS</span>
        <span className="font-mono text-[10px] text-red-400">{agent.errors?.length ?? 0}</span>
        <span className="font-mono text-[10px] text-slate-600">LAST RUN</span>
        <span className="font-mono text-[10px] text-slate-500">
          {agent.last_run ? new Date(agent.last_run).toLocaleString() : '—'}
        </span>
      </div>
      {agent.errors?.length > 0 && (
        <div className="mt-2 border-t border-ink-600 pt-2 space-y-1">
          {agent.errors.slice(-3).map((e, i) => (
            <p key={i} className="font-mono text-[9px] text-red-400/70 truncate">{e}</p>
          ))}
        </div>
      )}
    </div>
  )
}

export default function AgentDashboard() {
  const [agents, setAgents] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [embedLoading, setEmbedLoading] = useState(false)
  const [embedResult, setEmbedResult] = useState(null)
  const [scrapeMsg, setScrapeMsg] = useState('')

  // Page sliders
  const [canliiPages, setCanliiPages] = useState(5)
  const [hansardPages, setHansardPages] = useState(5)

  const fetchStatus = useCallback(async () => {
    try {
      const [statusRes, statsRes] = await Promise.all([
        fetch('/api/agents/status'),
        fetch('/api/agents/scraped/stats'),
      ])
      if (statusRes.ok) {
        const data = await statusRes.json()
        setAgents(data.agents || [])
      }
      if (statsRes.ok) {
        setStats(await statsRes.json())
      }
    } catch (_) {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStatus()
  }, [fetchStatus])

  // Auto-refresh every 10s when any agent is RUNNING
  useEffect(() => {
    const anyRunning = agents.some(a => a.status === 'RUNNING')
    if (!anyRunning) return
    const id = setInterval(fetchStatus, 10000)
    return () => clearInterval(id)
  }, [agents, fetchStatus])

  const triggerScraper = async (endpoint, label) => {
    setScrapeMsg(`Starting ${label}...`)
    try {
      const res = await fetch(endpoint, { method: 'POST' })
      if (res.ok) {
        setScrapeMsg(`${label} started`)
        setTimeout(fetchStatus, 1000)
      } else {
        setScrapeMsg(`Error starting ${label}: HTTP ${res.status}`)
      }
    } catch (e) {
      setScrapeMsg(`Error: ${e.message}`)
    }
  }

  const triggerAll = async () => {
    setScrapeMsg('Starting all scrapers...')
    await Promise.all([
      fetch(`/api/agents/scrape/canlii?pages=${canliiPages}`, { method: 'POST' }),
      fetch('/api/agents/scrape/rcy', { method: 'POST' }),
      fetch(`/api/agents/scrape/hansard?pages=${hansardPages}`, { method: 'POST' }),
    ])
    setScrapeMsg('All scrapers started')
    setTimeout(fetchStatus, 1000)
  }

  const triggerEmbed = async () => {
    setEmbedLoading(true)
    setEmbedResult(null)
    try {
      const res = await fetch('/api/agents/embed-scraped?limit=50', { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        setEmbedResult(`Embedded ${data.embedded} decisions`)
        fetchStatus()
      } else {
        setEmbedResult(`Error: HTTP ${res.status}`)
      }
    } catch (e) {
      setEmbedResult(`Error: ${e.message}`)
    } finally {
      setEmbedLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-ink-900 font-sans text-slate-200">
      <div className="h-px bg-gradient-to-r from-transparent via-cyan-500/60 to-transparent" />

      <header className="sticky top-0 z-20 border-b border-ink-600 bg-ink-900/90 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="font-display text-2xl tracking-[0.12em] text-white leading-none">
              AGENT DASHBOARD
            </h1>
            <p className="font-mono text-[10px] text-slate-600 tracking-widest mt-1">
              MCFD HISTORICAL DATA SCRAPER · PUBLIC SOURCES
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to="/"
              className="text-[10px] font-mono text-slate-500 border border-slate-700 px-2 py-1 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors"
            >
              ← HOME
            </Link>
            <button
              onClick={fetchStatus}
              className="text-[10px] font-mono text-cyan-400/70 border border-cyan-500/25 px-2 py-1 rounded tracking-widest hover:text-cyan-400 hover:border-cyan-500/50 transition-colors"
            >
              REFRESH
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-8">

        {/* ── Status Grid ───────────────────────────────── */}
        <section>
          <h2 className="font-mono text-[10px] text-slate-500 tracking-widest mb-3 uppercase">
            Agent Status
          </h2>
          {loading ? (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-32 bg-ink-800 border border-ink-600 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {agents.length === 0 ? (
                <p className="font-mono text-xs text-slate-600 col-span-3">No agents registered yet. Trigger a scraper to start.</p>
              ) : (
                agents.map(a => <AgentCard key={a.name} agent={a} />)
              )}
            </div>
          )}
        </section>

        {/* ── Scraper Controls ──────────────────────────── */}
        <section className="bg-ink-800 border border-ink-600 rounded-lg p-5 space-y-5">
          <h2 className="font-mono text-[10px] text-slate-500 tracking-widest uppercase">
            Scraper Controls
          </h2>

          {scrapeMsg && (
            <p className="font-mono text-[10px] text-cyan-400/80 border border-cyan-500/20 bg-cyan-900/10 px-3 py-2 rounded tracking-widest">
              {scrapeMsg}
            </p>
          )}

          {/* CanLII */}
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-[10px] text-slate-400 tracking-widest">CANLII</span>
                <span className="font-mono text-[10px] text-slate-500">{canliiPages} pages</span>
              </div>
              <input
                type="range" min={1} max={20} value={canliiPages}
                onChange={e => setCanliiPages(Number(e.target.value))}
                className="w-full accent-cyan-500"
              />
            </div>
            <button
              onClick={() => triggerScraper(`/api/agents/scrape/canlii?pages=${canliiPages}`, 'CanLII')}
              className="font-mono text-[10px] text-cyan-400 border border-cyan-500/40 px-3 py-2 rounded tracking-widest hover:bg-cyan-900/20 transition-colors whitespace-nowrap"
            >
              SCRAPE CANLII
            </button>
          </div>

          {/* RCY */}
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <span className="font-mono text-[10px] text-slate-400 tracking-widest">RCY REPORTS</span>
              <p className="font-mono text-[9px] text-slate-600 mt-0.5">Representative for Children and Youth BC</p>
            </div>
            <button
              onClick={() => triggerScraper('/api/agents/scrape/rcy', 'RCY')}
              className="font-mono text-[10px] text-cyan-400 border border-cyan-500/40 px-3 py-2 rounded tracking-widest hover:bg-cyan-900/20 transition-colors whitespace-nowrap"
            >
              SCRAPE RCY
            </button>
          </div>

          {/* Hansard */}
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-[10px] text-slate-400 tracking-widest">HANSARD</span>
                <span className="font-mono text-[10px] text-slate-500">{hansardPages} pages</span>
              </div>
              <input
                type="range" min={1} max={20} value={hansardPages}
                onChange={e => setHansardPages(Number(e.target.value))}
                className="w-full accent-cyan-500"
              />
            </div>
            <button
              onClick={() => triggerScraper(`/api/agents/scrape/hansard?pages=${hansardPages}`, 'Hansard')}
              className="font-mono text-[10px] text-cyan-400 border border-cyan-500/40 px-3 py-2 rounded tracking-widest hover:bg-cyan-900/20 transition-colors whitespace-nowrap"
            >
              SCRAPE HANSARD
            </button>
          </div>

          {/* Scrape All */}
          <div className="border-t border-ink-600 pt-4">
            <button
              onClick={triggerAll}
              className="w-full font-mono text-[10px] text-white bg-cyan-700 hover:bg-cyan-600 px-4 py-2.5 rounded tracking-widest transition-colors"
            >
              ⚡ SCRAPE ALL (CanLII + RCY + Hansard)
            </button>
          </div>
        </section>

        {/* ── Data Pipeline Stats + Embed ───────────────── */}
        <section className="bg-ink-800 border border-ink-600 rounded-lg p-5 space-y-4">
          <h2 className="font-mono text-[10px] text-slate-500 tracking-widest uppercase">
            Pipeline Stats
          </h2>

          {stats ? (
            <div className="grid grid-cols-3 gap-4">
              {[
                { label: 'CANLII DECISIONS', data: stats.scraped_decisions },
                { label: 'RCY REPORTS', data: stats.scraped_reports },
                { label: 'HANSARD EXCERPTS', data: stats.scraped_hansard },
              ].map(({ label, data }) => (
                <div key={label} className="text-center">
                  <p className="font-mono text-[9px] text-slate-600 tracking-widest">{label}</p>
                  <p className="font-mono text-lg text-white mt-1">{data?.total ?? 0}</p>
                  <p className="font-mono text-[9px] text-amber-400">{data?.unembedded ?? 0} unembedded</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="h-16 animate-pulse bg-ink-700 rounded" />
          )}

          <div className="border-t border-ink-600 pt-4 space-y-2">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-mono text-[10px] text-slate-400 tracking-widest">EMBED INTO VECTOR DB</p>
                <p className="font-mono text-[9px] text-slate-600 mt-0.5">
                  Processes up to 50 unembedded CanLII decisions → Decision + Chunk rows
                </p>
              </div>
              <button
                onClick={triggerEmbed}
                disabled={embedLoading}
                className="font-mono text-[10px] text-emerald-400 border border-emerald-500/40 px-3 py-2 rounded tracking-widest hover:bg-emerald-900/20 transition-colors disabled:opacity-50 whitespace-nowrap"
              >
                {embedLoading ? 'EMBEDDING...' : 'EMBED NOW'}
              </button>
            </div>
            {embedResult && (
              <p className="font-mono text-[10px] text-emerald-400/80 border border-emerald-500/20 bg-emerald-900/10 px-3 py-2 rounded tracking-widest">
                {embedResult}
              </p>
            )}
          </div>
        </section>

      </main>
    </div>
  )
}
