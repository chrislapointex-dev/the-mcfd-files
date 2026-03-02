import { useState, useEffect, useCallback } from 'react'
import SearchBar from './components/SearchBar'
import FilterBar from './components/FilterBar'
import DecisionCard from './components/DecisionCard'
import DecisionDetail from './components/DecisionDetail'
import Pagination from './components/Pagination'
import MemoryPanel from './components/MemoryPanel'
import AskPanel from './components/AskPanel'
import { useDecisions } from './hooks/useDecisions'

const EMPTY_FILTERS = { source: '', court: '', dateFrom: '', dateTo: '' }

export default function App() {
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

  // Ask mode
  const [inputMode, setInputMode] = useState('search') // 'search' | 'ask'
  const [askResult, setAskResult] = useState(null)
  const [askLoading, setAskLoading] = useState(false)
  const [askQuestion, setAskQuestion] = useState('')

  // Filter options from API
  const [filterOptions, setFilterOptions] = useState({ sources: [], courts: [], year_min: null, year_max: null })

  const isSearch = submittedQuery.length > 0
  const mode = selectedId !== null ? 'detail' : isSearch ? 'search' : 'browse'

  // Load filter options once
  useEffect(() => {
    fetch('/api/decisions/filters')
      .then(r => r.json())
      .then(setFilterOptions)
      .catch(console.error)
  }, [])

  const { data, loading, error } = useDecisions({
    mode,
    query: submittedQuery,
    filters,
    page,
  })

  const handleSearch = useCallback(
    async e => {
      e.preventDefault()
      const q = query.trim()
      if (!q) return

      if (inputMode === 'ask') {
        setAskQuestion(q)
        setAskResult(null)
        setAskLoading(true)
        setSelectedId(null)
        try {
          const res = await fetch('/api/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: q }),
          })
          const data = await res.json()
          setAskResult(data)
        } catch {
          setAskResult({ answer: 'Request failed. Is the backend running?', sources: [], chunks_used: 0, memory_updated: false })
        } finally {
          setAskLoading(false)
        }
        return
      }

      setSubmittedQuery(q)
      setPage(1)
      setSelectedId(null)
    },
    [query, inputMode]
  )

  const handleClear = useCallback(() => {
    setQuery('')
    setSubmittedQuery('')
    setAskResult(null)
    setAskQuestion('')
    setPage(1)
    setSelectedId(null)
  }, [])

  const handleModeToggle = useCallback(() => {
    setInputMode(m => m === 'search' ? 'ask' : 'search')
    setQuery('')
    setSubmittedQuery('')
    setAskResult(null)
    setAskQuestion('')
    setSelectedId(null)
    setPage(1)
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
              <button
                onClick={() => setMemoryOpen(true)}
                className="text-[10px] font-mono text-sky-400/70 border border-sky-500/25 px-2 py-1 rounded tracking-widest hover:text-sky-400 hover:border-sky-500/50 transition-colors hidden sm:block"
              >
                R2 MEMORY
              </button>
              <span className="text-[10px] font-mono text-amber-500/60 border border-amber-500/25 px-2 py-1 rounded tracking-widest hidden sm:block">
                UNREDACTED
              </span>
            </div>
          </div>

          {/* Mode toggle + search bar */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleModeToggle}
              title={inputMode === 'search' ? 'Switch to Ask mode (AI Q&A)' : 'Switch to Search mode'}
              className={`flex-shrink-0 font-mono text-[10px] tracking-widest px-2 py-1.5 rounded border transition-colors ${
                inputMode === 'ask'
                  ? 'bg-sky-500/15 border-sky-500/40 text-sky-400 hover:bg-sky-500/25'
                  : 'bg-ink-700 border-ink-500 text-slate-600 hover:text-slate-400 hover:border-ink-400'
              }`}
            >
              {inputMode === 'ask' ? 'ASK' : 'FTS'}
            </button>
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
        ) : inputMode === 'ask' ? (
          askLoading || askResult ? (
            <AskPanel
              question={askQuestion}
              result={askResult}
              loading={askLoading}
              onSelectDecision={handleSelect}
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
