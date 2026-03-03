import { useState } from 'react'

export default function DiagnosticsPanel({ budget, diagnostics }) {
  const [open, setOpen] = useState(false)

  if (!budget && !diagnostics) return null

  const chunks = diagnostics?.chunks_after_budget ?? 0
  const memories = diagnostics?.memory_total_items ?? 0
  const utilization = budget?.utilization_pct ?? diagnostics?.budget_utilization_pct ?? 0

  return (
    <div className="mt-3">
      {/* Collapsed chip */}
      <button
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-1.5 font-mono text-[10px] text-slate-700 hover:text-slate-500 tracking-widest transition-colors"
      >
        <span>{open ? '▾' : '▸'}</span>
        R2 used {chunks} chunks · {memories} memories · {utilization}% context
      </button>

      {/* Expanded panel */}
      {open && (
        <div className="mt-2 border border-ink-600 rounded bg-ink-800/40 p-4 space-y-4 text-[11px]">

          {/* Memory Regions */}
          {diagnostics?.memory_regions_loaded && Object.keys(diagnostics.memory_regions_loaded).length > 0 && (
            <section>
              <p className="font-mono text-[10px] text-slate-600 tracking-widest uppercase mb-2">Memory Regions</p>
              <div className="space-y-1">
                {Object.entries(diagnostics.memory_regions_loaded).map(([region, count]) => (
                  <div key={region} className="flex items-center gap-3">
                    <span className="font-mono text-[10px] text-sky-400/60 w-28">{region}</span>
                    <span className="font-mono text-[10px] text-slate-400">{count} item{count !== 1 ? 's' : ''}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Chunk Sources */}
          {diagnostics?.top_chunk_sources?.length > 0 && (
            <section>
              <p className="font-mono text-[10px] text-slate-600 tracking-widest uppercase mb-2">Chunk Sources</p>
              <div className="flex flex-wrap gap-1">
                {diagnostics.top_chunk_sources.map(src => (
                  <span
                    key={src}
                    className="font-mono text-[10px] bg-ink-700 text-slate-400 px-2 py-0.5 rounded border border-ink-600"
                  >
                    {src}
                  </span>
                ))}
              </div>
            </section>
          )}

          {/* Retrieval Stats */}
          {diagnostics && (
            <section>
              <p className="font-mono text-[10px] text-slate-600 tracking-widest uppercase mb-2">Retrieval</p>
              <div className="space-y-1">
                {[
                  ['FTS hits',       diagnostics.chunks_retrieved_fts],
                  ['Semantic hits',  diagnostics.chunks_retrieved_semantic],
                  ['After merge',    diagnostics.chunks_after_merge],
                  ['After budget',   diagnostics.chunks_after_budget],
                  ['Search type',    diagnostics.search_type],
                ].map(([label, val]) => (
                  <div key={label} className="flex items-center gap-3">
                    <span className="font-mono text-[10px] text-slate-600 w-28">{label}</span>
                    <span className="font-mono text-[10px] text-slate-300">{val}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Budget */}
          {budget && (
            <section>
              <p className="font-mono text-[10px] text-slate-600 tracking-widest uppercase mb-2">Budget</p>
              <div className="space-y-1">
                {[
                  ['System prompt',  `${budget.system_prompt_tokens} tokens`],
                  ['Output reserve', `${budget.output_reserve} tokens`],
                  ['Safety margin',  `${budget.safety_margin} tokens`],
                  ['Chunk budget',   `${budget.chunk_budget} tokens`],
                  ['Utilization',    `${budget.utilization_pct}%`],
                ].map(([label, val]) => (
                  <div key={label} className="flex items-center gap-3">
                    <span className="font-mono text-[10px] text-slate-600 w-28">{label}</span>
                    <span className="font-mono text-[10px] text-slate-300">{val}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Model */}
          {diagnostics?.model && (
            <div className="pt-2 border-t border-ink-600/50">
              <span className="font-mono text-[10px] text-slate-700">Model: {diagnostics.model}</span>
            </div>
          )}

        </div>
      )}
    </div>
  )
}
