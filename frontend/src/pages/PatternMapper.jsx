import { useState, useEffect, useRef, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import * as d3 from 'd3'

const TYPE_COLORS = {
  judge:        '#3b82f6',
  social_worker:'#ef4444',
  lawyer:       '#22c55e',
  office:       '#f97316',
  statute:      '#a855f7',
  outcome:      '#eab308',
}

const ENTITY_TYPES = ['judge', 'social_worker', 'lawyer', 'office', 'statute', 'outcome']

// ── Timeline strip ─────────────────────────────────────────────────────────────

function TimelineStrip({ entries }) {
  const dated = entries.filter(e => e.date)
  if (!dated.length) return null

  const times  = dated.map(e => new Date(e.date).getTime())
  const minT   = Math.min(...times)
  const maxT   = Math.max(...times)
  const range  = maxT - minT || 1

  return (
    <div className="relative h-5 bg-ink-700 rounded overflow-hidden border border-ink-600">
      {dated.map(e => {
        const pct = ((new Date(e.date).getTime() - minT) / range) * 96 + 2
        return (
          <div
            key={e.decision_id}
            className="absolute top-1 bottom-1 w-px bg-amber-500/60 hover:bg-amber-400 transition-colors"
            style={{ left: `${pct}%` }}
            title={`${e.date} — ${(e.title || '').slice(0, 50)}`}
          />
        )
      })}
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function PatternMapper() {
  const svgRef  = useRef(null)
  const simRef  = useRef(null)
  const navigate = useNavigate()

  const [typeA,      setTypeA]      = useState('judge')
  const [typeB,      setTypeB]      = useState('outcome')
  const [minCount,   setMinCount]   = useState(3)
  const [nameFilter, setNameFilter] = useState('')

  const [pairs,   setPairs]   = useState([])
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)

  const [selectedNode,  setSelectedNode]  = useState(null)
  const [nodeDetail,    setNodeDetail]    = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [timelineData,  setTimelineData]  = useState(null)

  // ── Data fetching ────────────────────────────────────────────────────────────

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(
        `/api/patterns/co-occurrence?entity_type_a=${typeA}&entity_type_b=${typeB}&min_count=${minCount}`
      )
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setPairs(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [typeA, typeB, minCount])

  useEffect(() => { fetchData() }, [fetchData])

  const fetchNodeDetail = useCallback(async (entityValue) => {
    setDetailLoading(true)
    setNodeDetail(null)
    setTimelineData(null)
    try {
      const [detailRes, timelineRes] = await Promise.all([
        fetch(`/api/patterns/entities/${encodeURIComponent(entityValue)}`),
        fetch(`/api/patterns/timeline?entity_value=${encodeURIComponent(entityValue)}`),
      ])
      if (detailRes.ok)    setNodeDetail(await detailRes.json())
      if (timelineRes.ok)  setTimelineData(await timelineRes.json())
    } catch (_) { /* ignore */ } finally {
      setDetailLoading(false)
    }
  }, [])

  // ── D3 graph ─────────────────────────────────────────────────────────────────

  useEffect(() => {
    if (!svgRef.current || loading) return

    const svgEl = svgRef.current

    // Apply name filter
    const filtered = nameFilter
      ? pairs.filter(p =>
          p.entity_a.toLowerCase().includes(nameFilter.toLowerCase()) ||
          p.entity_b.toLowerCase().includes(nameFilter.toLowerCase())
        )
      : pairs

    // Clear previous render + stop simulation
    d3.select(svgEl).selectAll('*').remove()
    if (simRef.current) { simRef.current.stop(); simRef.current = null }

    if (!filtered.length) return

    // Build nodes and links from pairs
    const nodeMap = new Map()
    filtered.forEach(p => {
      if (!nodeMap.has(p.entity_a)) nodeMap.set(p.entity_a, { id: p.entity_a, type: typeA, decSet: new Set() })
      if (!nodeMap.has(p.entity_b)) nodeMap.set(p.entity_b, { id: p.entity_b, type: typeB, decSet: new Set() })
      p.decision_ids.forEach(id => {
        nodeMap.get(p.entity_a).decSet.add(id)
        nodeMap.get(p.entity_b).decSet.add(id)
      })
    })
    const nodes = Array.from(nodeMap.values()).map(n => ({ ...n, count: n.decSet.size }))
    const links = filtered.map(p => ({ source: p.entity_a, target: p.entity_b, value: p.co_occurrence_count }))
    const maxCount = Math.max(...nodes.map(n => n.count), 1)

    const nodeR = d => 4 + Math.sqrt(d.count / maxCount) * 18

    const width  = svgEl.clientWidth  || 700
    const height = svgEl.clientHeight || 500

    const svg = d3.select(svgEl)
    const g   = svg.append('g')

    // Zoom
    svg.call(
      d3.zoom()
        .scaleExtent([0.1, 8])
        .on('zoom', e => g.attr('transform', e.transform))
    )

    // Links
    const link = g.append('g').selectAll('line')
      .data(links).join('line')
      .attr('stroke', '#1e293b')
      .attr('stroke-width', d => Math.max(1, Math.log(d.value + 1) * 2))
      .attr('stroke-opacity', 0.6)

    // Nodes
    const node = g.append('g').selectAll('circle')
      .data(nodes).join('circle')
      .attr('r', nodeR)
      .attr('fill', d => TYPE_COLORS[d.type] || '#64748b')
      .attr('fill-opacity', 0.8)
      .attr('stroke', '#07070f')
      .attr('stroke-width', 1.5)
      .attr('cursor', 'pointer')
      .on('click', (event, d) => {
        event.stopPropagation()
        setSelectedNode(d)
        fetchNodeDetail(d.id)
      })
      .on('mouseover', (_, d) => {
        link.attr('stroke-opacity', l =>
          l.source.id === d.id || l.target.id === d.id ? 1 : 0.05
        )
        node.attr('fill-opacity', n => n.id === d.id ? 1 : 0.25)
      })
      .on('mouseout', () => {
        link.attr('stroke-opacity', 0.6)
        node.attr('fill-opacity', 0.8)
      })
      .call(
        d3.drag()
          .on('start', (event, d) => {
            if (!event.active) sim.alphaTarget(0.3).restart()
            d.fx = d.x; d.fy = d.y
          })
          .on('drag',  (event, d) => { d.fx = event.x; d.fy = event.y })
          .on('end',   (event, d) => {
            if (!event.active) sim.alphaTarget(0)
            d.fx = null; d.fy = null
          })
      )

    // Labels for prominent nodes
    const labelThreshold = maxCount * 0.12
    const label = g.append('g').selectAll('text')
      .data(nodes.filter(d => d.count >= labelThreshold))
      .join('text')
      .attr('font-size', '8px')
      .attr('font-family', 'IBM Plex Mono, monospace')
      .attr('fill', '#94a3b8')
      .attr('text-anchor', 'middle')
      .attr('pointer-events', 'none')
      .text(d => d.id.length > 24 ? d.id.slice(0, 22) + '…' : d.id)

    const sim = d3.forceSimulation(nodes)
      .force('link',      d3.forceLink(links).id(d => d.id).distance(90).strength(0.4))
      .force('charge',    d3.forceManyBody().strength(-200))
      .force('center',    d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(d => nodeR(d) + 5))
      .on('tick', () => {
        link
          .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
          .attr('x2', d => d.target.x).attr('y2', d => d.target.y)
        node.attr('cx', d => d.x).attr('cy', d => d.y)
        label.attr('x', d => d.x).attr('y', d => d.y - nodeR(d) - 3)
      })

    simRef.current = sim

    return () => sim.stop()
  }, [pairs, nameFilter, typeA, typeB, loading, fetchNodeDetail])

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <div className="h-screen bg-ink-900 font-sans text-slate-200 flex flex-col overflow-hidden">

      {/* Top accent */}
      <div className="h-px bg-gradient-to-r from-transparent via-emerald-500/60 to-transparent flex-shrink-0" />

      {/* Header */}
      <header className="border-b border-ink-600 bg-ink-900/95 backdrop-blur-sm flex-shrink-0">
        <div className="px-4 py-3 flex items-center justify-between">
          <Link to="/" className="font-display text-lg tracking-[0.12em] text-white hover:text-amber-400 transition-colors">
            THE MCFD FILES
          </Link>
          <nav className="flex items-center gap-2">
            <Link to="/"
              className="text-[10px] font-mono text-slate-500 border border-slate-700 px-2 py-1 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors">
              SEARCH
            </Link>
            <span className="text-[10px] font-mono text-emerald-400 border border-emerald-500/40 px-2 py-1 rounded tracking-widest">
              PATTERNS
            </span>
            <Link to="/about"
              className="text-[10px] font-mono text-slate-500 border border-slate-700 px-2 py-1 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors">
              ABOUT
            </Link>
          </nav>
        </div>
      </header>

      {/* Filter bar */}
      <div className="border-b border-ink-600 bg-ink-800/60 px-4 py-2 flex items-center gap-3 flex-wrap flex-shrink-0">
        <label className="flex items-center gap-1.5">
          <span className="font-mono text-[9px] text-slate-600 tracking-widest">TYPE A</span>
          <select value={typeA} onChange={e => setTypeA(e.target.value)}
            className="font-mono text-[10px] bg-ink-700 border border-ink-500 text-slate-300 px-2 py-1 rounded">
            {ENTITY_TYPES.map(t => <option key={t} value={t}>{t.replace('_', ' ').toUpperCase()}</option>)}
          </select>
        </label>

        <span className="font-mono text-[10px] text-slate-600">×</span>

        <label className="flex items-center gap-1.5">
          <span className="font-mono text-[9px] text-slate-600 tracking-widest">TYPE B</span>
          <select value={typeB} onChange={e => setTypeB(e.target.value)}
            className="font-mono text-[10px] bg-ink-700 border border-ink-500 text-slate-300 px-2 py-1 rounded">
            {ENTITY_TYPES.map(t => <option key={t} value={t}>{t.replace('_', ' ').toUpperCase()}</option>)}
          </select>
        </label>

        <label className="flex items-center gap-1.5">
          <span className="font-mono text-[9px] text-slate-600 tracking-widest">MIN</span>
          <input type="number" value={minCount} min={1}
            onChange={e => setMinCount(Math.max(1, parseInt(e.target.value) || 1))}
            className="font-mono text-[10px] bg-ink-700 border border-ink-500 text-slate-300 w-14 px-2 py-1 rounded" />
        </label>

        <input type="text" value={nameFilter} onChange={e => setNameFilter(e.target.value)}
          placeholder="Filter by name…"
          className="font-mono text-[10px] bg-ink-700 border border-ink-500 text-slate-300 placeholder-slate-700 px-2 py-1 rounded w-36" />

        <button onClick={fetchData} disabled={loading}
          className="font-mono text-[10px] tracking-widest border border-emerald-500/30 text-emerald-400/70 hover:text-emerald-400 hover:border-emerald-500/60 px-2 py-1 rounded transition-colors disabled:opacity-40">
          {loading ? '···' : 'REFRESH'}
        </button>

        {!loading && pairs.length > 0 && (
          <span className="font-mono text-[9px] text-slate-600">{pairs.length} pairs</span>
        )}

        {/* Legend */}
        <div className="flex items-center gap-2.5 ml-auto">
          {Object.entries(TYPE_COLORS).map(([type, color]) => (
            <div key={type} className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color, opacity: 0.8 }} />
              <span className="font-mono text-[9px] text-slate-600">{type.replace('_', ' ')}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Main area: graph + sidebar */}
      <div className="flex flex-1 overflow-hidden" style={{ minHeight: 0 }}>

        {/* Graph */}
        <div className="flex-1 relative bg-ink-900" onClick={() => setSelectedNode(null)}>
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
              <span className="font-mono text-xs text-slate-600 tracking-widest animate-pulse">LOADING…</span>
            </div>
          )}
          {error && (
            <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
              <span className="font-mono text-xs text-red-500">{error}</span>
            </div>
          )}
          {!loading && !error && pairs.length === 0 && (
            <div className="absolute inset-0 flex flex-col items-center justify-center z-10 pointer-events-none gap-2">
              <span className="font-mono text-xs text-slate-600 tracking-widest">NO PAIRS FOUND</span>
              <span className="font-mono text-[10px] text-slate-700">Lower the minimum count or change types</span>
            </div>
          )}
          <svg ref={svgRef} className="w-full h-full" style={{ display: 'block' }} />
        </div>

        {/* Sidebar */}
        {selectedNode && (
          <div className="w-72 border-l border-ink-600 bg-ink-800/90 flex flex-col flex-shrink-0 overflow-hidden">

            {/* Header */}
            <div className="p-4 border-b border-ink-600 flex items-start gap-2 flex-shrink-0">
              <div className="flex-1 min-w-0">
                <p className="text-xs text-slate-200 font-medium leading-snug break-words">
                  {selectedNode.id}
                </p>
                <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                  <span className="font-mono text-[9px] px-1.5 py-0.5 rounded"
                    style={{ backgroundColor: (TYPE_COLORS[selectedNode.type] || '#64748b') + '22',
                             color: TYPE_COLORS[selectedNode.type] || '#64748b' }}>
                    {selectedNode.type.replace('_', ' ').toUpperCase()}
                  </span>
                  <span className="font-mono text-[9px] text-slate-600">
                    {selectedNode.count} decisions
                  </span>
                </div>
              </div>
              <button onClick={() => { setSelectedNode(null); setNodeDetail(null); setTimelineData(null) }}
                className="text-slate-600 hover:text-slate-400 font-mono text-xs flex-shrink-0 mt-0.5">
                ✕
              </button>
            </div>

            {/* Action buttons */}
            <div className="px-4 py-2.5 border-b border-ink-600/50 flex gap-2 flex-shrink-0">
              <button
                onClick={() => navigate(`/?q=${encodeURIComponent(selectedNode.id)}`)}
                className="flex-1 font-mono text-[9px] tracking-widest border border-amber-500/25 text-amber-500/70 hover:text-amber-400 hover:border-amber-500/50 px-2 py-1.5 rounded transition-colors text-center"
              >
                SEARCH DECISIONS
              </button>
              <button
                onClick={() => navigate(`/?ask=${encodeURIComponent(selectedNode.id)}`)}
                className="flex-1 font-mono text-[9px] tracking-widest border border-sky-500/25 text-sky-400/70 hover:text-sky-400 hover:border-sky-500/50 px-2 py-1.5 rounded transition-colors text-center"
              >
                ASK AI
              </button>
            </div>

            {detailLoading && (
              <div className="p-4 font-mono text-[10px] text-slate-600 tracking-widest animate-pulse">
                LOADING…
              </div>
            )}

            {nodeDetail && !detailLoading && (
              <div className="flex-1 overflow-y-auto">

                {/* Timeline */}
                {timelineData && timelineData.length > 0 && (
                  <div className="p-4 border-b border-ink-600/50">
                    <p className="font-mono text-[9px] text-slate-600 tracking-widest uppercase mb-2">
                      Timeline · {timelineData.filter(e => e.date).length} dates
                    </p>
                    <TimelineStrip entries={timelineData} />
                    {timelineData.filter(e => e.date).length > 1 && (
                      <div className="flex justify-between mt-1">
                        <span className="font-mono text-[9px] text-slate-700">
                          {timelineData.find(e => e.date)?.date}
                        </span>
                        <span className="font-mono text-[9px] text-slate-700">
                          {[...timelineData].reverse().find(e => e.date)?.date}
                        </span>
                      </div>
                    )}
                  </div>
                )}

                {/* Decisions */}
                <div className="p-4 border-b border-ink-600/50">
                  <p className="font-mono text-[9px] text-slate-600 tracking-widest uppercase mb-2">
                    Decisions ({nodeDetail.appearances.length})
                  </p>
                  <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
                    {nodeDetail.appearances.slice(0, 40).map(a => (
                      <a key={a.decision_id} href={a.url} target="_blank" rel="noopener noreferrer"
                        className="block group">
                        <span className="font-mono text-[9px] text-amber-500/60 group-hover:text-amber-400 transition-colors">
                          {a.citation || `#${a.decision_id}`}
                        </span>
                        <span className="block text-[10px] text-slate-500 group-hover:text-slate-300 transition-colors leading-snug truncate">
                          {a.title}
                        </span>
                        {a.date && (
                          <span className="font-mono text-[9px] text-slate-700">{a.date}</span>
                        )}
                      </a>
                    ))}
                    {nodeDetail.appearances.length > 40 && (
                      <p className="font-mono text-[9px] text-slate-700 italic">
                        +{nodeDetail.appearances.length - 40} more
                      </p>
                    )}
                  </div>
                </div>

                {/* Co-occurring entities */}
                {nodeDetail.appearances.length > 0 && (
                  <div className="p-4">
                    <p className="font-mono text-[9px] text-slate-600 tracking-widest uppercase mb-2">
                      Co-occurring
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {[...new Set(nodeDetail.appearances.flatMap(a => a.co_entities || []))].slice(0, 25).map(e => (
                        <span key={e}
                          className="font-mono text-[9px] bg-ink-700 text-slate-500 px-1.5 py-0.5 rounded border border-ink-600 truncate max-w-full">
                          {e.length > 28 ? e.slice(0, 26) + '…' : e}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
