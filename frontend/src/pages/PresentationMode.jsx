import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'

// ── Slide components ──────────────────────────────────────────────────────────

function TitleSlide({ summary }) {
  const trialDate = 'APRIL 14, 2025'
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-16">
      <div className="font-mono text-[11px] tracking-[0.4em] text-cyan-400/70 mb-8 uppercase">
        PC 19700 — C.L.
      </div>
      <h1 style={{ fontSize: '72px', lineHeight: 1.1 }} className="font-mono font-bold text-white tracking-[0.15em] uppercase mb-12">
        THE MCFD FILES
      </h1>
      <div style={{ fontSize: '28px' }} className="font-mono text-slate-400 mb-6 tracking-widest">
        TRIAL DATE: {trialDate}
      </div>
      {summary?.days_remaining != null && (
        <div style={{ fontSize: '56px' }} className="font-mono font-bold text-amber-400 tracking-widest">
          {summary.days_remaining} DAYS
        </div>
      )}
      <div style={{ fontSize: '18px' }} className="font-mono text-slate-600 mt-4 tracking-widest">
        REMAINING
      </div>
    </div>
  )
}

function AnimatedNumber({ target, color }) {
  const [display, setDisplay] = useState(0)
  const rafRef = useRef(null)
  useEffect(() => {
    if (typeof target !== 'number' || isNaN(target)) return
    const duration = 1000
    const start = performance.now()
    function tick(now) {
      const elapsed = now - start
      const progress = Math.min(elapsed / duration, 1)
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3)
      setDisplay(Math.round(eased * target))
      if (progress < 1) rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(rafRef.current)
  }, [target])
  if (typeof target !== 'number' || isNaN(target)) {
    return <span className={`font-mono font-bold ${color}`} style={{ fontSize: '96px', lineHeight: 1 }}>—</span>
  }
  return <span className={`font-mono font-bold ${color}`} style={{ fontSize: '96px', lineHeight: 1 }}>{display}</span>
}

function StatsSlide({ summary }) {
  const stats = [
    { label: 'CONTRADICTIONS', value: Number(summary?.contradiction_count), color: 'text-red-400' },
    { label: 'PERSONAL CHUNKS', value: Number(summary?.personal_chunks), color: 'text-cyan-400' },
    { label: 'DAYS REMAINING', value: Number(summary?.days_remaining), color: 'text-amber-400' },
  ]
  return (
    <div className="flex flex-col items-center justify-center h-full px-16">
      <h2 style={{ fontSize: '32px' }} className="font-mono text-slate-500 tracking-[0.3em] uppercase mb-16">
        CASE STATISTICS
      </h2>
      <div className="flex gap-24 justify-center">
        {stats.map(s => (
          <div key={s.label} className="text-center">
            <AnimatedNumber target={s.value} color={s.color} />
            <div style={{ fontSize: '16px' }} className="font-mono text-slate-500 tracking-widest mt-4">
              {s.label}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

const SEVERITY_COLORS = {
  high: 'text-red-400 border-red-500/50 bg-red-900/20',
  medium: 'text-amber-400 border-amber-500/50 bg-amber-900/20',
  low: 'text-green-400 border-green-500/50 bg-green-900/20',
}

function ContradictionSlide({ item, index, total }) {
  const sev = (item.severity || 'medium').toLowerCase()
  const colorClass = SEVERITY_COLORS[sev] || SEVERITY_COLORS.medium
  return (
    <div className="flex flex-col justify-center h-full px-20">
      <div className="flex items-center gap-4 mb-10">
        <span style={{ fontSize: '13px' }} className="font-mono text-slate-600 tracking-widest">
          CONTRADICTION {index} / {total}
        </span>
        <span className={`font-mono text-[12px] tracking-widest px-3 py-1 border ${colorClass} uppercase`}>
          {item.severity || 'MEDIUM'}
        </span>
      </div>
      <p style={{ fontSize: '36px', lineHeight: 1.35 }} className="font-mono text-white mb-10 leading-snug">
        {item.claim}
      </p>
      <p style={{ fontSize: '24px', lineHeight: 1.5 }} className="font-mono text-slate-400 mb-8">
        {item.evidence}
      </p>
      {item.source_doc && (
        <div style={{ fontSize: '14px' }} className="font-mono text-slate-600 tracking-widest">
          SOURCE: {item.source_doc}{item.page_ref ? ` · P.${item.page_ref}` : ''}
        </div>
      )}
    </div>
  )
}

const CATEGORY_COLORS = {
  critical: 'text-red-400',
  high: 'text-orange-400',
  medium: 'text-amber-400',
  low: 'text-slate-400',
}

function TimelineSlide({ item, index, total }) {
  const colorClass = CATEGORY_COLORS[(item.severity || item.category || '').toLowerCase()] || 'text-amber-400'
  const dateStr = item.event_date ? new Date(item.event_date).toLocaleDateString('en-CA', { year: 'numeric', month: 'long', day: 'numeric' }).toUpperCase() : ''
  return (
    <div className="flex flex-col justify-center h-full px-20">
      <div style={{ fontSize: '13px' }} className="font-mono text-slate-600 tracking-widest mb-6">
        EVENT {index} / {total}
        {item.category && <span className="ml-4 text-slate-500">{item.category.toUpperCase()}</span>}
      </div>
      {dateStr && (
        <div style={{ fontSize: '40px' }} className={`font-mono font-bold ${colorClass} tracking-widest mb-6`}>
          {dateStr}
        </div>
      )}
      <h2 style={{ fontSize: '48px', lineHeight: 1.2 }} className="font-mono text-white mb-8">
        {item.title}
      </h2>
      {item.description && (
        <p style={{ fontSize: '24px', lineHeight: 1.5 }} className="font-mono text-slate-400">
          {item.description}
        </p>
      )}
      {item.source_ref && (
        <div style={{ fontSize: '14px' }} className="font-mono text-slate-600 tracking-widest mt-8">
          REF: {item.source_ref}
        </div>
      )}
    </div>
  )
}

function CostSlide({ costs }) {
  const total = costs?.grand_total ?? 0
  const formatted = new Intl.NumberFormat('en-CA', { style: 'currency', currency: 'CAD' }).format(total)
  const byCategory = costs?.by_category ?? {}
  return (
    <div className="flex flex-col justify-center h-full px-20">
      <div style={{ fontSize: '13px' }} className="font-mono text-slate-600 tracking-widest mb-8">
        COST SUMMARY{costs?.case_ref ? ` · ${costs.case_ref}` : ''}
      </div>
      <div style={{ fontSize: '80px', lineHeight: 1 }} className="font-mono font-bold text-red-400 mb-12">
        {formatted}
      </div>
      <div style={{ fontSize: '18px' }} className="font-mono text-slate-500 tracking-widest mb-8">
        TOTAL ESTIMATED COST
      </div>
      {Object.keys(byCategory).length > 0 && (
        <div className="grid grid-cols-2 gap-x-16 gap-y-3 mt-4">
          {Object.entries(byCategory).map(([cat, amt]) => (
            <div key={cat} className="flex justify-between gap-8">
              <span style={{ fontSize: '18px' }} className="font-mono text-slate-400 uppercase tracking-wide">{cat}</span>
              <span style={{ fontSize: '18px' }} className="font-mono text-white">
                {new Intl.NumberFormat('en-CA', { style: 'currency', currency: 'CAD' }).format(amt)}
              </span>
            </div>
          ))}
        </div>
      )}
      {costs?.days_in_care != null && (
        <div style={{ fontSize: '22px' }} className="font-mono text-amber-400 mt-10 tracking-widest">
          {costs.days_in_care} DAYS IN CARE
        </div>
      )}
    </div>
  )
}

// ── Slide builder ─────────────────────────────────────────────────────────────

const SLIDE_TYPES = ['TITLE', 'STATS', 'CONTRADICTIONS', 'TIMELINE', 'COST']

function buildSlides(selected, data) {
  const slides = []
  if (selected.TITLE) slides.push({ type: 'title' })
  if (selected.STATS) slides.push({ type: 'stats' })
  if (selected.CONTRADICTIONS && data.contradictions?.length) {
    data.contradictions.forEach((item, i) =>
      slides.push({ type: 'contradiction', item, index: i + 1, total: data.contradictions.length })
    )
  }
  if (selected.TIMELINE && data.events?.length) {
    data.events.forEach((item, i) =>
      slides.push({ type: 'timeline', item, index: i + 1, total: data.events.length })
    )
  }
  if (selected.COST) slides.push({ type: 'cost' })
  return slides
}

// ── Main component ────────────────────────────────────────────────────────────

export default function PresentationMode() {
  const [phase, setPhase] = useState('builder') // 'builder' | 'present'
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState({ summary: null, contradictions: [], events: [], costs: null })
  const [selected, setSelected] = useState({ TITLE: true, STATS: true, CONTRADICTIONS: true, TIMELINE: true, COST: true })
  const [liveMode, setLiveMode] = useState(false)
  const [aspect169, setAspect169] = useState(false)
  const [slideIndex, setSlideIndex] = useState(0)
  const [visible, setVisible] = useState(true)
  const fadeTimer = useRef(null)

  // Fetch all data on mount
  useEffect(() => {
    Promise.all([
      fetch('/api/trialprep/summary').then(r => r.ok ? r.json() : null).catch(() => null),
      fetch('/api/contradictions').then(r => r.ok ? r.json() : null).catch(() => null),
      fetch('/api/timeline/events').then(r => r.ok ? r.json() : null).catch(() => null),
      fetch('/api/costs').then(r => r.ok ? r.json() : null).catch(() => null),
    ]).then(([summary, contradictions, events, costs]) => {
      setData({
        summary,
        contradictions: Array.isArray(contradictions) ? contradictions : [],
        events: Array.isArray(events) ? events : [],
        costs,
      })
      setLoading(false)
    })
  }, [])

  // Keyboard handler — only active in presenter phase
  useEffect(() => {
    if (phase !== 'present') return
    const slides = buildSlides(selected, data)
    const handler = (e) => {
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        setSlideIndex(i => {
          const next = Math.min(i + 1, slides.length - 1)
          if (next !== i) goToSlide(next)
          return i
        })
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        setSlideIndex(i => {
          const next = Math.max(i - 1, 0)
          if (next !== i) goToSlide(next)
          return i
        })
      } else if (e.key === 'Escape') {
        setPhase('builder')
        setSlideIndex(0)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [phase, selected, data])

  const slides = buildSlides(selected, data)

  function goToSlide(next) {
    clearTimeout(fadeTimer.current)
    setVisible(false)
    fadeTimer.current = setTimeout(() => {
      setSlideIndex(next)
      setVisible(true)
    }, 180)
  }

  function startPresenter() {
    if (slides.length === 0) return
    setSlideIndex(0)
    setVisible(true)
    setPhase('present')
  }

  function advanceSlide() {
    setSlideIndex(i => {
      const next = Math.min(i + 1, slides.length - 1)
      if (next !== i) goToSlide(next)
      return i
    })
  }

  // ── Presenter phase ────────────────────────────────────────────────────────
  if (phase === 'present') {
    const slide = slides[slideIndex]
    const inner = (
      <div className="relative w-full h-full">
        {/* LIVE dot */}
        {liveMode && (
          <div className="absolute top-8 right-10 flex items-center gap-2 z-10">
            <div className="w-3 h-3 bg-red-500 animate-pulse" style={{ borderRadius: 0 }} />
            <span className="font-mono text-red-400 text-[13px] tracking-widest">LIVE</span>
          </div>
        )}
        {/* Slide counter */}
        <div className="absolute bottom-8 right-10 font-mono text-slate-600 text-[13px] tracking-widest z-10">
          {slideIndex + 1} / {slides.length}
        </div>
        {/* Slide content */}
        <div
          className="w-full h-full"
          onClick={advanceSlide}
          style={{ opacity: visible ? 1 : 0, transition: 'opacity 180ms ease' }}
        >
          {slide.type === 'title' && <TitleSlide summary={data.summary} />}
          {slide.type === 'stats' && <StatsSlide summary={data.summary} />}
          {slide.type === 'contradiction' && (
            <ContradictionSlide item={slide.item} index={slide.index} total={slide.total} />
          )}
          {slide.type === 'timeline' && (
            <TimelineSlide item={slide.item} index={slide.index} total={slide.total} />
          )}
          {slide.type === 'cost' && <CostSlide costs={data.costs} />}
        </div>
      </div>
    )

    return (
      <div
        style={{ position: 'fixed', inset: 0, background: '#0a0e1a', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
        className="z-50"
      >
        {aspect169 ? (
          <div style={{ aspectRatio: '16/9', maxHeight: '100vh', maxWidth: 'calc(100vh * (16 / 9))', width: '100%', position: 'relative' }}>
            {inner}
          </div>
        ) : (
          <div style={{ width: '100%', height: '100%', position: 'relative' }}>
            {inner}
          </div>
        )}
      </div>
    )
  }

  // ── Builder phase ──────────────────────────────────────────────────────────
  const counts = {
    TITLE: 1,
    STATS: 1,
    CONTRADICTIONS: data.contradictions.length,
    TIMELINE: data.events.length,
    COST: 1,
  }

  return (
    <div className="min-h-screen bg-[#0a0e1a] font-mono text-slate-300 flex flex-col">
      {/* Header */}
      <div className="h-px bg-gradient-to-r from-transparent via-cyan-500/40 to-transparent" />
      <header className="border-b border-slate-800/60 px-8 py-5 flex items-center justify-between">
        <div>
          <div className="text-[10px] tracking-[0.4em] text-slate-600 mb-1">THE MCFD FILES</div>
          <h1 className="text-2xl tracking-[0.2em] text-white font-bold">PRESENTATION MODE</h1>
        </div>
        <Link to="/trial" className="text-[10px] tracking-widest text-slate-500 border border-slate-700 px-3 py-1.5 hover:text-slate-300 hover:border-slate-500 transition-colors">
          ← BACK
        </Link>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center px-8 py-12">
        {loading ? (
          <div className="text-[11px] tracking-widest text-slate-600 animate-pulse">LOADING DATA…</div>
        ) : (
          <div className="w-full max-w-lg">
            <div className="text-[10px] tracking-[0.3em] text-slate-600 mb-6 uppercase">Select Slides</div>

            {/* Slide checkboxes */}
            <div className="space-y-2 mb-10">
              {SLIDE_TYPES.map(type => (
                <label key={type} className="flex items-center gap-4 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={selected[type]}
                    onChange={e => setSelected(s => ({ ...s, [type]: e.target.checked }))}
                    className="accent-cyan-500 w-4 h-4"
                  />
                  <span className="text-[13px] tracking-widest text-slate-300 group-hover:text-white transition-colors flex-1">
                    {type}
                  </span>
                  <span className="text-[11px] tracking-widest text-slate-600">
                    {counts[type] > 1 ? `${counts[type]} slides` : '1 slide'}
                  </span>
                </label>
              ))}
            </div>

            {/* Options */}
            <div className="flex gap-8 mb-12">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={liveMode}
                  onChange={e => setLiveMode(e.target.checked)}
                  className="accent-red-500 w-4 h-4"
                />
                <span className="text-[12px] tracking-widest text-red-400">LIVE</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={aspect169}
                  onChange={e => setAspect169(e.target.checked)}
                  className="accent-cyan-500 w-4 h-4"
                />
                <span className="text-[12px] tracking-widest text-slate-400">16:9</span>
              </label>
            </div>

            {/* Slide count info */}
            <div className="text-[11px] tracking-widest text-slate-600 mb-6">
              {slides.length} slide{slides.length !== 1 ? 's' : ''} total
            </div>

            {/* Present button */}
            <button
              onClick={startPresenter}
              disabled={slides.length === 0}
              className="w-full bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-800 disabled:text-slate-600 text-white text-[13px] tracking-[0.3em] py-4 transition-colors"
              style={{ borderRadius: 0 }}
            >
              ▶ PRESENT
            </button>

            <div className="text-[10px] tracking-widest text-slate-700 mt-4 text-center">
              Arrow keys to advance · ESC to exit
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
