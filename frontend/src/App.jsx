import { useState, useEffect, useCallback, useRef } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import SearchBar from './components/SearchBar'
import FilterBar from './components/FilterBar'
import DecisionCard from './components/DecisionCard'
import DecisionDetail from './components/DecisionDetail'
import Pagination from './components/Pagination'
import MemoryPanel from './components/MemoryPanel'
import AskPanel from './components/AskPanel'
import SemanticPanel from './components/SemanticPanel'
import { useDecisions } from './hooks/useDecisions'

const EMPTY_FILTERS = { source: '', court: '', dateFrom: '', dateTo: '' }
const EMPTY_ASK_RESULT = { answer: '', sources: [], chunks_used: 0, memory_updated: false, budget: null, diagnostics: null }

export default function App() {
  const [searchParams] = useSearchParams()

  // Search state
  const [query, setQuery] = useState('')
  const [submittedQuery, setSubmittedQuery] = useState('')

  // Navigation
  const [selectedId, setSelectedId] = useState(null)

  // Filters + pagination
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [page, setPage] = useState(1)

  // Memory panel
  const [memoryOpen, setMemoryOpen] = useState(false)

  // Mobile nav menu
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  // Input mode: 'search' | 'semantic' | 'ask'
  const [inputMode, setInputMode] = useState('search')

  // Ask mode: array of { question, result } messages
  const [askMessages, setAskMessages] = useState([])
  const [askLoading, setAskLoading] = useState(false)

  // Semantic mode state
  const [semanticResults, setSemanticResults] = useState(null)
  const [semanticLoading, setSemanticLoading] = useState(false)
  const [semanticQuery, setSemanticQuery] = useState('')

  // Filter options from API
  const [filterOptions, setFilterOptions] = useState({ sources: [], courts: [], year_min: null, year_max: null })

  // Abort controller for in-flight semantic/ask requests
  const abortRef = useRef(null)

  const isSearch = submittedQuery.length > 0
  const mode = selectedId !== null ? 'detail' : isSearch ? 'search' : 'browse'

  // Load filter options once
  useEffect(() => {
    fetch('/api/decisions/filters')
      .then(r => r.json())
      .then(setFilterOptions)
      .catch(() => setFilterOptions({ sources: [], courts: [], year_min: null, year_max: null }))
  }, [])

  const { data, loading, error } = useDecisions({
    mode,
    query: submittedQuery,
    filters,
    page,
  })

  // ── Ask streaming ────────────────────────────────────────────────────────────

  const triggerAsk = useCallback(async (q) => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setAskMessages(prev => [...prev, { question: q, result: { ...EMPTY_ASK_RESULT } }])
    setAskLoading(true)
    setSelectedId(null)

    try {
      const res = await fetch('/api/ask/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q }),
        signal: controller.signal,
      })
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const parts = buf.split('\n\n')
        buf = parts.pop()
        for (const part of parts) {
          const line = part.trim()
          if (!line.startsWith('data: ')) continue
          const data = JSON.parse(line.slice(6))
          if (data.type === 'token') {
            setAskMessages(prev => {
              const msgs = [...prev]
              const last = msgs[msgs.length - 1]
              msgs[msgs.length - 1] = { ...last, result: { ...last.result, answer: last.result.answer + data.text } }
              return msgs
            })
          } else if (data.type === 'done') {
            setAskMessages(prev => {
              const msgs = [...prev]
              const last = msgs[msgs.length - 1]
              msgs[msgs.length - 1] = {
                ...last,
                result: {
                  ...last.result,
                  sources: data.sources,
                  chunks_used: data.chunks_used,
                  memory_updated: data.memory_updated,
                  budget: data.budget ?? null,
                  diagnostics: data.diagnostics ?? null,
                },
              }
              return msgs
            })
          } else if (data.type === 'error') {
            setAskMessages(prev => {
              const msgs = [...prev]
              const last = msgs[msgs.length - 1]
              msgs[msgs.length - 1] = { ...last, result: { ...last.result, answer: data.message } }
              return msgs
            })
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        setAskMessages(prev => {
          const msgs = [...prev]
          const last = msgs[msgs.length - 1]
          msgs[msgs.length - 1] = { ...last, result: { ...last.result, answer: 'Request failed. Is the backend running?' } }
          return msgs
        })
      }
    } finally {
      setAskLoading(false)
    }
  }, [])

  // ── URL param auto-submit (#3: crosslink from PatternMapper) ─────────────────

  useEffect(() => {
    const q = searchParams.get('q')
    const ask = searchParams.get('ask')
    if (q) {
      setInputMode('search')
      setQuery(q)
      setSubmittedQuery(q)
      setPage(1)
    } else if (ask) {
      setInputMode('ask')
      setQuery(ask)
      triggerAsk(ask)
    }
    // Only run once on mount — intentionally no deps on searchParams
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── Handlers ─────────────────────────────────────────────────────────────────

  const handleSearch = useCallback(
    async e => {
      e.preventDefault()
      const q = query.trim()
      if (!q) return

      if (inputMode === 'semantic') {
        abortRef.current?.abort()
        const controller = new AbortController()
        abortRef.current = controller
        setSemanticQuery(q)
        setSemanticResults(null)
        setSemanticLoading(true)
        setSelectedId(null)
        try {
          const res = await fetch(`/api/search/semantic?q=${encodeURIComponent(q)}&k=20`, { signal: controller.signal })
          const data = await res.json()
          setSemanticResults(data)
        } catch (err) {
          if (err.name !== 'AbortError') setSemanticResults({ query: q, total: 0, results: [] })
        } finally {
          setSemanticLoading(false)
        }
        return
      }

      if (inputMode === 'ask') {
        triggerAsk(q)
        return
      }

      setSubmittedQuery(q)
      setPage(1)
      setSelectedId(null)
    },
    [query, inputMode, triggerAsk]
  )

  const handleClear = useCallback(() => {
    setQuery('')
    setSubmittedQuery('')
    setAskMessages([])
    setSemanticResults(null)
    setSemanticQuery('')
    setPage(1)
    setSelectedId(null)
  }, [])

  const handleSetMode = useCallback((newMode) => {
    abortRef.current?.abort()
    setInputMode(newMode)
    setQuery('')
    setSubmittedQuery('')
    setAskMessages([])
    setSemanticResults(null)
    setSemanticQuery('')
    setSelectedId(null)
    setPage(1)
  }, [])

  const handleNewConversation = useCallback(() => {
    abortRef.current?.abort()
    setAskMessages([])
    setAskLoading(false)
    setQuery('')
  }, [])

  const handleFilterChange = useCallback(newFilters => {
    setFilters(newFilters)
    setPage(1)
  }, [])

  const handleSelect = useCallback(id => {
    setSelectedId(id)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

  const handleBack = useCallback(() => {
    setSelectedId(null)
  }, [])

  const handlePageChange = useCallback(p => {
    setPage(p)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

  return (
    <div className="min-h-screen bg-ink-900 font-sans text-slate-200">
      {memoryOpen && <MemoryPanel onClose={() => setMemoryOpen(false)} />}

      {/* Top amber accent line */}
      <div className="h-px bg-gradient-to-r from-transparent via-amber-500/60 to-transparent" />

      {/* ── Header ──────────────────────────────────── */}
      <header className="sticky top-0 z-20 border-b border-ink-600 bg-ink-900/90 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-4 py-4">

          {/* Logo row */}
          <div className="flex items-start justify-between gap-4 mb-4">
            <div>
              <h1 className="font-display text-3xl tracking-[0.12em] text-white leading-none">
                THE MCFD FILES
              </h1>
              <p className="font-mono text-[10px] text-slate-600 tracking-widest mt-1 uppercase">
                BC Court Decisions · Ministry of Children &amp; Family Development
              </p>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              {/* Desktop nav */}
              <button
                onClick={() => setMemoryOpen(true)}
                className="text-[10px] font-mono text-sky-400/70 border border-sky-500/25 px-2 py-1 rounded tracking-widest hover:text-sky-400 hover:border-sky-500/50 transition-colors hidden sm:block"
              >
                R2 MEMORY
              </button>
              <Link
                to="/patterns"
                className="text-[10px] font-mono text-slate-500 border border-slate-700 px-2 py-1 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors hidden sm:block"
              >
                PATTERNS
              </Link>
              <Link
                to="/about"
                className="text-[10px] font-mono text-slate-500 border border-slate-700 px-2 py-1 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors hidden sm:block"
              >
                ABOUT
              </Link>
              <span className="text-[10px] font-mono text-amber-500/60 border border-amber-500/25 px-2 py-1 rounded tracking-widest hidden sm:block">
                UNREDACTED
              </span>

              {/* Mobile hamburger */}
              <div className="relative sm:hidden">
                <button
                  onClick={() => setMobileMenuOpen(v => !v)}
                  className="text-[10px] font-mono text-slate-500 border border-slate-700 px-2 py-1 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors"
                  aria-label="Open menu"
                >
                  ☰
                </button>
                {mobileMenuOpen && (
                  <div className="absolute right-0 top-full mt-1 z-50 bg-ink-800 border border-ink-600 rounded shadow-lg flex flex-col min-w-[130px]">
                    <button
                      onClick={() => { setMemoryOpen(true); setMobileMenuOpen(false) }}
                      className="text-[10px] font-mono text-sky-400/70 px-3 py-2.5 text-left hover:bg-ink-700 hover:text-sky-400 transition-colors tracking-widest"
                    >
                      R2 MEMORY
                    </button>
                    <Link
                      to="/patterns"
                      onClick={() => setMobileMenuOpen(false)}
                      className="text-[10px] font-mono text-slate-500 px-3 py-2.5 hover:bg-ink-700 hover:text-slate-300 transition-colors tracking-widest"
                    >
                      PATTERNS
                    </Link>
                    <Link
                      to="/about"
                      onClick={() => setMobileMenuOpen(false)}
                      className="text-[10px] font-mono text-slate-500 px-3 py-2.5 hover:bg-ink-700 hover:text-slate-300 transition-colors tracking-widest"
                    >
                      ABOUT
                    </Link>
                    <span className="text-[10px] font-mono text-amber-500/60 px-3 py-2.5 tracking-widest border-t border-ink-600">
                      UNREDACTED
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Mode toggle + search bar */}
          <div className="flex items-center gap-2">
            {/* Three-way mode toggle */}
            <div className="flex flex-shrink-0 rounded border border-ink-500 overflow-hidden">
              {[
                { id: 'search',   label: 'FTS',    active: 'bg-amber-500/15 border-r border-amber-500/30 text-amber-400' },
                { id: 'semantic', label: 'VECTOR', active: 'bg-violet-500/15 border-r border-violet-500/30 text-violet-400' },
                { id: 'ask',      label: 'ASK',    active: 'bg-sky-500/15 text-sky-400' },
              ].map(({ id, label, active }, i) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => handleSetMode(id)}
                  className={`font-mono text-[10px] tracking-widest px-2 py-1.5 transition-colors ${
                    i < 2 ? 'border-r border-ink-500' : ''
                  } ${
                    inputMode === id
                      ? active
                      : 'bg-ink-700 text-slate-600 hover:text-slate-400'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="flex-1">
              <SearchBar
                value={query}
                onChange={setQuery}
                onSubmit={handleSearch}
                onClear={handleClear}
                isSearch={isSearch}
                mode={inputMode}
              />
            </div>
          </div>
        </div>
      </header>

      {/* ── Main ────────────────────────────────────── */}
      <main className="max-w-4xl mx-auto px-4 py-6">

        {selectedId !== null ? (
          <DecisionDetail id={selectedId} onBack={handleBack} />
        ) : inputMode === 'semantic' ? (
          semanticLoading || semanticResults ? (
            <SemanticPanel
              query={semanticQuery}
              results={semanticResults}
              loading={semanticLoading}
              onSelectDecision={handleSelect}
            />
          ) : (
            <div className="py-24 text-center">
              <p className="font-mono text-xs text-slate-600 tracking-widest">VECTOR MODE ACTIVE</p>
              <p className="font-mono text-[10px] text-slate-700 mt-2">
                Semantic similarity search over embedded document chunks.
              </p>
            </div>
          )
        ) : inputMode === 'ask' ? (
          askLoading || askMessages.length > 0 ? (
            <AskPanel
              messages={askMessages}
              loading={askLoading}
              onSelectDecision={handleSelect}
              onNewConversation={handleNewConversation}
            />
          ) : (
            <div className="py-24 text-center">
              <p className="font-mono text-xs text-slate-600 tracking-widest">ASK MODE ACTIVE</p>
              <p className="font-mono text-[10px] text-slate-700 mt-2">
                Ask any question about BC court decisions involving MCFD.
              </p>
            </div>
          )
        ) : (
          <>
            {/* Filters */}
            <FilterBar
              filters={filters}
              onChange={handleFilterChange}
              sources={filterOptions.sources}
              courts={filterOptions.courts}
              yearMin={filterOptions.year_min}
              yearMax={filterOptions.year_max}
              total={data?.total ?? 0}
              isSearch={isSearch}
              query={submittedQuery}
              loading={loading}
            />

            {/* Error state */}
            {error && (
              <div className="font-mono text-sm text-red-400 py-12 text-center">
                Error: {error}
              </div>
            )}

            {/* Skeleton loader (first load only) */}
            {loading && !data && (
              <div className="space-y-3 mt-5">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div
                    key={i}
                    className="flex animate-pulse"
                    style={{ animationDelay: `${i * 80}ms` }}
                  >
                    <div className="w-[3px] flex-shrink-0 rounded-l bg-ink-600" />
                    <div className="flex-1 bg-ink-800 border border-l-0 border-ink-700 rounded-r-lg h-28" />
                  </div>
                ))}
              </div>
            )}

            {/* Results list */}
            {data && (
              <>
                <div className={`mt-5 space-y-3 transition-opacity duration-150 ${loading ? 'opacity-50' : 'opacity-100'}`}>
                  {data.items.length === 0 ? (
                    <div className="py-20 text-center">
                      <p className="font-mono text-sm text-slate-600">
                        {isSearch
                          ? `No decisions found for "${submittedQuery}".`
                          : 'No decisions found.'}
                      </p>
                      {isSearch && (
                        <button
                          onClick={handleClear}
                          className="mt-4 font-mono text-xs text-amber-500 hover:text-amber-400 transition-colors"
                        >
                          CLEAR SEARCH
                        </button>
                      )}
                    </div>
                  ) : (
                    data.items.map((decision, i) => (
                      <DecisionCard
                        key={decision.id}
                        decision={decision}
                        onClick={() => handleSelect(decision.id)}
                        index={i}
                      />
                    ))
                  )}
                </div>

                {data.pages > 1 && (
                  <div className="mt-10">
                    <Pagination
                      page={page}
                      pages={data.pages}
                      onPageChange={handlePageChange}
                    />
                    <p className="text-center font-mono text-[10px] text-slate-700 mt-3">
                      PAGE {page} OF {data.pages} · {data.total.toLocaleString()} TOTAL
                    </p>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </main>

      {/* ── Footer ──────────────────────────────────── */}
      <footer className="border-t border-ink-600 mt-20 py-8">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <p className="font-mono text-[10px] text-slate-700 uppercase tracking-widest">
            The MCFD Files · BC Court Decisions · Compiled for public interest research
          </p>
        </div>
      </footer>
    </div>
  )
}
