import { useState, useEffect, useRef, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import * as d3 from 'd3'
import * as THREE from 'three'

const TYPE_COLORS = {
  social_worker: '#ef4444',
  judge: '#a855f7',
  lawyer: '#3b82f6',
  statute: '#eab308',
  outcome: '#6b7280',
  office: '#f97316',
}

function nodeColor(type) {
  return TYPE_COLORS[type] || '#6b7280'
}

function nodeSize(mention_count) {
  return Math.max(0.2, Math.min(2.0, Math.sqrt(mention_count) * 0.3))
}

function GraphNode({ node, isHighlighted, onClick, onHover }) {
  const [hovered, setHovered] = useState(false)
  const color = nodeColor(node.type)

  return (
    <mesh
      position={[node.x, node.y, node.z]}
      onClick={(e) => { e.stopPropagation(); onClick(node) }}
      onPointerOver={(e) => { e.stopPropagation(); setHovered(true); onHover(node) }}
      onPointerOut={() => { setHovered(false); onHover(null) }}
    >
      <sphereGeometry args={[nodeSize(node.mention_count), 12, 12]} />
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={hovered || isHighlighted ? 0.6 : 0.1}
        roughness={0.4}
        metalness={0.2}
      />
    </mesh>
  )
}

function GraphLinks({ nodes, links }) {
  const geo = useMemo(() => {
    const nodeMap = {}
    nodes.forEach(n => { nodeMap[n.id] = n })

    const positions = []
    links.forEach(link => {
      const src = nodeMap[typeof link.source === 'object' ? link.source.id : link.source]
      const tgt = nodeMap[typeof link.target === 'object' ? link.target.id : link.target]
      if (src && tgt) {
        positions.push(src.x, src.y, src.z, tgt.x, tgt.y, tgt.z)
      }
    })

    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
    return geometry
  }, [nodes, links])

  return (
    <lineSegments geometry={geo}>
      <lineBasicMaterial color="#334155" opacity={0.35} transparent />
    </lineSegments>
  )
}

function Scene({ graphData, highlightIds, onNodeClick, onNodeHover }) {
  return (
    <>
      <ambientLight intensity={0.5} />
      <pointLight position={[100, 100, 100]} intensity={1} />
      <pointLight position={[-100, -100, -50]} intensity={0.3} />
      <GraphLinks nodes={graphData.nodes} links={graphData.links} />
      {graphData.nodes.map(node => (
        <GraphNode
          key={node.id}
          node={node}
          isHighlighted={highlightIds.has(node.id)}
          onClick={onNodeClick}
          onHover={onNodeHover}
        />
      ))}
      <OrbitControls enableDamping dampingFactor={0.1} />
    </>
  )
}

function EntityDetail({ name }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    setData(null)
    fetch(`/api/graph/entity/${encodeURIComponent(name)}`)
      .then(r => r.json())
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [name])

  if (loading) {
    return <p className="font-mono text-[9px] text-slate-600 tracking-widest animate-pulse">LOADING...</p>
  }
  if (!data) return null

  return (
    <div>
      {data.co_occurring?.length > 0 && (
        <div className="mb-3">
          <p className="font-mono text-[9px] text-slate-600 tracking-widest mb-1.5">CO-OCCURRING</p>
          <div className="flex flex-wrap gap-1">
            {data.co_occurring.map(co => (
              <span key={co} className="font-mono text-[8px] text-emerald-400/70 border border-emerald-500/20 px-1.5 py-0.5 rounded">
                {co}
              </span>
            ))}
          </div>
        </div>
      )}
      {data.chunks?.length > 0 && (
        <div>
          <p className="font-mono text-[9px] text-slate-600 tracking-widest mb-1.5">APPEARANCES</p>
          <div className="space-y-2">
            {data.chunks.slice(0, 5).map((chunk, i) => (
              <div key={i} className="border border-ink-600 rounded p-2">
                <p className="font-mono text-[8px] text-slate-400 line-clamp-3 leading-relaxed">{chunk.text}</p>
                {chunk.citation && (
                  <p className="font-mono text-[8px] text-slate-600 mt-1">{chunk.citation}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function buildGraph(rawData) {
  const nodes = rawData.nodes.map(n => ({
    ...n,
    z: (Math.random() - 0.5) * 80,
  }))
  const links = rawData.links.map(l => ({ ...l }))

  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(20).strength(0.4))
    .force('charge', d3.forceManyBody().strength(-40))
    .force('center', d3.forceCenter(0, 0))
    .stop()

  for (let i = 0; i < 300; i++) simulation.tick()

  // Scale x/y to spread nodes nicely in 3D space
  nodes.forEach(n => {
    n.x = (n.x || 0) * 0.6
    n.y = (n.y || 0) * 0.6
  })

  return { nodes, links }
}

export default function EntityWeb() {
  const [graphData, setGraphData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState(null)
  const [hovered, setHovered] = useState(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    fetch('/api/graph/entities')
      .then(r => r.json())
      .then(data => {
        setGraphData(buildGraph(data))
        setLoading(false)
      })
      .catch(() => {
        setError('Failed to load entity graph')
        setLoading(false)
      })
  }, [])

  const highlightIds = useMemo(() => {
    if (!search.trim() || !graphData) return new Set()
    const q = search.toLowerCase()
    return new Set(graphData.nodes.filter(n => n.name.toLowerCase().includes(q)).map(n => n.id))
  }, [search, graphData])

  return (
    <div className="h-screen bg-ink-900 font-sans text-slate-200 flex flex-col overflow-hidden">
      <div className="h-px bg-gradient-to-r from-transparent via-emerald-500/60 to-transparent flex-shrink-0" />

      {/* Header */}
      <header className="flex-shrink-0 border-b border-ink-600 bg-ink-900/90 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-4">
          <div>
            <h1 className="font-display text-xl tracking-[0.12em] text-white leading-none">
              ENTITY WEB
            </h1>
            <p className="font-mono text-[10px] text-slate-600 tracking-widest mt-0.5 uppercase">
              3D co-occurrence graph · lawyers · judges · social workers · statutes
            </p>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="SEARCH..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="font-mono text-[10px] bg-ink-800 border border-ink-600 text-slate-300 px-2 py-1 rounded tracking-widest placeholder-slate-600 focus:outline-none focus:border-emerald-500/40 w-32"
            />
            <Link
              to="/trial"
              className="text-[10px] font-mono text-slate-500 border border-slate-700 px-2 py-1 rounded tracking-widest hover:text-slate-300 hover:border-slate-500 transition-colors"
            >
              ← BACK
            </Link>
          </div>
        </div>
      </header>

      {/* Canvas area */}
      <div className="flex-1 relative">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center z-10">
            <span className="font-mono text-[10px] text-slate-500 tracking-widest animate-pulse">
              BUILDING GRAPH...
            </span>
          </div>
        )}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center z-10">
            <span className="font-mono text-[10px] text-red-500 tracking-widest">{error}</span>
          </div>
        )}
        {graphData && (
          <Canvas
            camera={{ position: [0, 0, 150], fov: 60 }}
            style={{ width: '100%', height: '100%' }}
            gl={{ antialias: true }}
          >
            <Scene
              graphData={graphData}
              highlightIds={highlightIds}
              onNodeClick={setSelected}
              onNodeHover={setHovered}
            />
          </Canvas>
        )}

        {/* Hover tooltip */}
        {hovered && (
          <div className="absolute bottom-4 left-4 pointer-events-none bg-ink-900/90 border border-ink-600 rounded px-3 py-2">
            <p className="font-mono text-[10px] text-slate-300 tracking-widest">{hovered.name}</p>
            <p className="font-mono text-[9px] text-slate-500 tracking-widest mt-0.5">
              {hovered.type} · {hovered.mention_count} mentions
            </p>
          </div>
        )}

        {/* Search hint */}
        {search && highlightIds.size > 0 && (
          <div className="absolute top-3 left-4 pointer-events-none">
            <span className="font-mono text-[9px] text-emerald-400/70 tracking-widest">
              {highlightIds.size} match{highlightIds.size !== 1 ? 'es' : ''}
            </span>
          </div>
        )}

        {/* Selected node panel */}
        {selected && (
          <div className="absolute top-3 right-3 w-72 bg-ink-900/95 border border-ink-600 rounded shadow-xl overflow-y-auto max-h-[calc(100vh-100px)]">
            <div className="p-4">
              <div className="flex items-start justify-between gap-2 mb-3">
                <div>
                  <p className="font-mono text-[11px] text-white tracking-widest font-bold leading-snug">{selected.name}</p>
                  <p className="font-mono text-[9px] text-slate-500 tracking-widest mt-1">
                    {selected.type} · {selected.mention_count} mentions
                  </p>
                </div>
                <button
                  onClick={() => setSelected(null)}
                  className="font-mono text-[10px] text-slate-600 hover:text-slate-400 transition-colors flex-shrink-0 mt-0.5"
                >
                  ✕
                </button>
              </div>
              <EntityDetail name={selected.name} />
            </div>
          </div>
        )}

        {/* Legend */}
        <div className="absolute bottom-4 right-4 bg-ink-900/90 border border-ink-600 rounded px-3 py-2">
          {Object.entries(TYPE_COLORS).map(([type, color]) => (
            <div key={type} className="flex items-center gap-2 mb-1 last:mb-0">
              <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
              <span className="font-mono text-[9px] text-slate-500 tracking-widest">{type.replace('_', ' ')}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
