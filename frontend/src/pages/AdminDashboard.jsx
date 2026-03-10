import { useState, useEffect } from 'react'

function SeverityBadge({ severity }) {
  const colors = {
    DIRECT: 'bg-red-900/60 text-red-300 border border-red-700/50',
    PARTIAL: 'bg-amber-900/60 text-amber-300 border border-amber-700/50',
    NONE: 'bg-slate-800 text-slate-400 border border-slate-700/50',
  }
  return (
    <span className={`font-mono text-[9px] px-1.5 py-0.5 rounded tracking-widest ${colors[severity] || colors.NONE}`}>
      {severity}
    </span>
  )
}

function SeverityDot({ severity }) {
  const colors = {
    DIRECT: 'bg-red-500',
    PARTIAL: 'bg-amber-500',
    NONE: 'bg-slate-600',
  }
  return <span className={`inline-block w-1.5 h-1.5 rounded-full shrink-0 mt-[5px] ${colors[severity] || colors.NONE}`} />
}

function StatusBadge({ ok, label }) {
  return (
    <span className={`font-mono text-[9px] px-1.5 py-0.5 rounded tracking-widest border ${
      ok ? 'bg-green-900/40 text-green-300 border-green-700/50' : 'bg-red-900/40 text-red-300 border-red-700/50'
    }`}>
      {label}
    </span>
  )
}

function SectionHeader({ children }) {
  return (
    <h2 className="text-[11px] tracking-[0.25em] text-slate-400 uppercase mb-4 border-b border-slate-800 pb-2">
      {children}
    </h2>
  )
}

export default function AdminDashboard() {
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('mcfd_api_key') || '')
  const [deployCheck, setDeployCheck] = useState(null)
  const [contradictions, setContradictions] = useState([])
  const [costs, setCosts] = useState(null)
  const [timeline, setTimeline] = useState([])
  const [witnesses, setWitnesses] = useState([])
  const [shareViews, setShareViews] = useState(null)
  const [loading, setLoading] = useState(true)
  const [errors, setErrors] = useState({})

  const headers = apiKey ? { 'X-API-Key': apiKey } : {}

  function handleApiKeyChange(e) {
    const val = e.target.value
    setApiKey(val)
    localStorage.setItem('mcfd_api_key', val)
  }

  async function fetchDeployCheck() {
    try {
      const res = await fetch('/api/deploy-check')
      const data = await res.json()
      setDeployCheck(data)
    } catch (e) {
      setErrors(prev => ({ ...prev, deployCheck: e.message }))
    }
  }

  async function fetchAll() {
    setLoading(true)
    const h = apiKey ? { 'X-API-Key': apiKey } : {}

    await Promise.all([
      fetchDeployCheck(),
      fetch('/api/contradictions', { headers: h })
        .then(r => r.json())
        .then(data => {
          const list = Array.isArray(data) ? data : (data.contradictions || [])
          list.sort((a, b) => {
            const order = { DIRECT: 0, PARTIAL: 1, NONE: 2 }
            return (order[a.severity] ?? 3) - (order[b.severity] ?? 3)
          })
          setContradictions(list)
        })
        .catch(e => setErrors(prev => ({ ...prev, contradictions: e.message }))),

      fetch('/api/costs')
        .then(r => r.json())
        .then(data => setCosts(data))
        .catch(e => setErrors(prev => ({ ...prev, costs: e.message }))),

      fetch('/api/timeline/events', { headers: h })
        .then(r => r.json())
        .then(data => setTimeline(Array.isArray(data) ? data : (data.events || [])))
        .catch(e => setErrors(prev => ({ ...prev, timeline: e.message }))),

      fetch('/api/witnesses', { headers: h })
        .then(r => r.json())
        .then(data => setWitnesses(Array.isArray(data) ? data : (data.witnesses || [])))
        .catch(e => setErrors(prev => ({ ...prev, witnesses: e.message }))),

      fetch('/api/share/views')
        .then(r => r.json())
        .then(data => setShareViews(data))
        .catch(e => setErrors(prev => ({ ...prev, shareViews: e.message }))),
    ])

    setLoading(false)
  }

  useEffect(() => { fetchAll() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const devMode = deployCheck?.checks?.auth?.mode && deployCheck.checks.auth.mode.includes('no key')
  const dbReady = deployCheck?.checks?.database

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-mono">
      {/* Header */}
      <header className="py-8 px-4 border-b border-slate-800">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row sm:items-center gap-4 justify-between">
          <div>
            <h1 className="text-xl font-bold text-white tracking-[0.08em]">ADMIN — THE MCFD FILES</h1>
            <div className="text-[10px] text-slate-500 tracking-[0.2em] mt-1">
              Private — not for public distribution
            </div>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-[10px] text-slate-500 shrink-0">API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={handleApiKeyChange}
              placeholder="mcfd_..."
              className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-200 w-48 focus:outline-none focus:border-slate-500"
            />
          </div>
        </div>
      </header>

      {devMode && (
        <div className="bg-amber-900/30 border-b border-amber-700/50 px-4 py-2 text-center">
          <span className="text-[11px] text-amber-300 tracking-widest">⚠ DEV MODE — no API key configured on server</span>
        </div>
      )}

      <main className="max-w-5xl mx-auto px-4 py-8 space-y-10">

        {/* Section 1 — Platform Status */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <SectionHeader>Platform Status</SectionHeader>
            <button
              onClick={fetchDeployCheck}
              className="text-[10px] text-slate-500 border border-slate-700 rounded px-2 py-1 hover:text-slate-300 hover:border-slate-500 transition-colors -mt-2"
            >
              Refresh
            </button>
          </div>
          {deployCheck ? (
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2 items-center">
                <StatusBadge ok={deployCheck.ready} label={deployCheck.ready ? 'READY' : 'NOT READY'} />
                <StatusBadge ok={deployCheck.checks?.auth?.mode !== 'no key set'} label={`Auth: ${deployCheck.checks?.auth?.mode || '—'}`} />
                <StatusBadge ok={deployCheck.checks?.vault?.ok} label={`Vault: ${deployCheck.checks?.vault?.ok ? 'OK' : 'MISSING'}`} />
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                {[
                  { label: 'Contradictions', value: dbReady?.contradictions ?? '—' },
                  { label: 'Cost entries', value: dbReady?.cost_entries ?? '—' },
                  { label: 'Timeline events', value: dbReady?.timeline_events ?? '—' },
                  { label: 'Witnesses', value: dbReady?.witnesses ?? '—' },
                  { label: 'Share views', value: shareViews?.total_views ?? '—' },
                ].map(({ label, value }) => (
                  <div key={label} className="bg-slate-900/60 border border-slate-800 rounded p-3">
                    <div className="text-[18px] font-bold text-slate-100">{value}</div>
                    <div className="text-[10px] text-slate-500 mt-0.5">{label}</div>
                  </div>
                ))}
              </div>
              {deployCheck.warnings?.length > 0 && (
                <div className="text-[11px] text-amber-400 space-y-1">
                  {deployCheck.warnings.map((w, i) => <div key={i}>⚠ {w}</div>)}
                </div>
              )}
            </div>
          ) : (
            <div className="text-[12px] text-slate-600">{loading ? 'Loading…' : (errors.deployCheck || 'No data')}</div>
          )}
        </section>

        {/* Section 2 — Contradictions */}
        <section>
          <SectionHeader>
            Contradictions {contradictions.length > 0 && `— ${contradictions.length} total`}
          </SectionHeader>
          {contradictions.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-[11px]">
                <thead>
                  <tr className="text-slate-500 text-left border-b border-slate-800">
                    <th className="pr-3 pb-2 font-normal w-8">#</th>
                    <th className="pr-3 pb-2 font-normal w-20">Severity</th>
                    <th className="pr-3 pb-2 font-normal">Claim</th>
                    <th className="pb-2 font-normal w-32">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {contradictions.map((c, i) => (
                    <tr key={c.id} className={`border-b border-slate-800/50 ${i % 2 === 0 ? '' : 'bg-slate-900/40'}`}>
                      <td className="pr-3 py-2 text-slate-600">{c.id}</td>
                      <td className="pr-3 py-2"><SeverityBadge severity={c.severity} /></td>
                      <td className="pr-3 py-2 text-slate-300 leading-relaxed">
                        {c.claim?.length > 80 ? c.claim.slice(0, 80) + '…' : c.claim}
                      </td>
                      <td className="py-2 text-slate-500 truncate max-w-[128px]">{c.source_doc}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-[12px] text-slate-600">{loading ? 'Loading…' : (errors.contradictions || 'No data')}</div>
          )}
        </section>

        {/* Section 3 — Costs Summary */}
        <section>
          <SectionHeader>Costs Summary</SectionHeader>
          {costs ? (
            <div className="space-y-3">
              <div className="flex items-baseline gap-3">
                <span className="text-2xl font-bold text-slate-100">
                  ${costs.grand_total?.toLocaleString('en-CA', { minimumFractionDigits: 2 })}
                </span>
                <span className="text-[11px] text-slate-500">total documented cost</span>
              </div>
              {costs.by_category && (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {Object.entries(costs.by_category).map(([cat, total]) => (
                    <div key={cat} className="bg-slate-900/60 border border-slate-800 rounded p-3">
                      <div className="text-[13px] font-bold text-slate-200">
                        ${Number(total).toLocaleString('en-CA', { minimumFractionDigits: 2 })}
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5 capitalize">{cat.replace(/_/g, ' ')}</div>
                    </div>
                  ))}
                </div>
              )}
              <a href="/costs" className="text-[10px] text-slate-500 hover:text-slate-300 transition-colors">
                Full breakdown → /costs
              </a>
            </div>
          ) : (
            <div className="text-[12px] text-slate-600">{loading ? 'Loading…' : (errors.costs || 'No data')}</div>
          )}
        </section>

        {/* Section 4 — Timeline */}
        <section>
          <SectionHeader>Timeline</SectionHeader>
          {timeline.length > 0 ? (
            <div className="space-y-1">
              {timeline.map((ev, i) => (
                <div key={i} className="flex gap-3 items-start py-1.5 border-b border-slate-800/40 text-[11px]">
                  <span className="text-slate-600 shrink-0 w-24">{ev.date}</span>
                  <SeverityDot severity={ev.severity} />
                  <span className="text-slate-300 leading-snug">
                    {ev.title?.length > 70 ? ev.title.slice(0, 70) + '…' : ev.title}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-[12px] text-slate-600">{loading ? 'Loading…' : (errors.timeline || 'No data')}</div>
          )}
        </section>

        {/* Section 5 — Witnesses */}
        <section>
          <SectionHeader>Witness Profiles</SectionHeader>
          {witnesses.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-[11px]">
                <thead>
                  <tr className="text-slate-500 text-left border-b border-slate-800">
                    <th className="pr-4 pb-2 font-normal">Name</th>
                    <th className="pr-4 pb-2 font-normal">Role</th>
                    <th className="pb-2 font-normal">Chunks</th>
                  </tr>
                </thead>
                <tbody>
                  {witnesses.map((w, i) => (
                    <tr key={i} className={`border-b border-slate-800/50 ${i % 2 === 0 ? '' : 'bg-slate-900/40'}`}>
                      <td className="pr-4 py-2 text-slate-200">{w.name}</td>
                      <td className="pr-4 py-2 text-slate-400">{w.role}</td>
                      <td className="py-2 text-slate-500">{w.chunk_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-[12px] text-slate-600">{loading ? 'Loading…' : (errors.witnesses || 'No data')}</div>
          )}
        </section>

        {/* Section 6 — Share Analytics */}
        <section>
          <SectionHeader>Share Analytics</SectionHeader>
          {shareViews ? (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: 'Total views', value: shareViews.total_views ?? '—' },
                { label: 'Views today', value: shareViews.views_today ?? '—' },
                { label: 'First view', value: shareViews.first_view ? new Date(shareViews.first_view).toLocaleDateString('en-CA') : '—' },
                { label: 'Latest view', value: shareViews.latest_view ? new Date(shareViews.latest_view).toLocaleDateString('en-CA') : '—' },
              ].map(({ label, value }) => (
                <div key={label} className="bg-slate-900/60 border border-slate-800 rounded p-3">
                  <div className="text-[18px] font-bold text-slate-100">{value}</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">{label}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-[12px] text-slate-600">{loading ? 'Loading…' : (errors.shareViews || 'No data')}</div>
          )}
        </section>

        {/* Section 7 — Quick Actions */}
        <section>
          <SectionHeader>Quick Actions</SectionHeader>
          <div className="flex flex-wrap gap-3">
            {[
              { label: 'Caryma Brief PDF', href: '/api/export/caryma-brief.pdf', download: true },
              { label: 'Media Package JSON', href: '/api/export/media-package', download: false },
              { label: 'Trial Report PDF', href: '/api/export/trial-report.pdf', download: true },
            ].map(({ label, href, download }) => (
              <a
                key={label}
                href={href}
                {...(download ? { download: true } : { target: '_blank', rel: 'noopener noreferrer' })}
                className="text-[10px] font-mono text-slate-400 border border-slate-700 rounded px-3 py-2 hover:text-slate-200 hover:border-slate-500 transition-colors"
              >
                {label}
              </a>
            ))}
            <button
              onClick={fetchDeployCheck}
              className="text-[10px] font-mono text-slate-400 border border-slate-700 rounded px-3 py-2 hover:text-slate-200 hover:border-slate-500 transition-colors"
            >
              Deploy Check
            </button>
          </div>
        </section>

      </main>
    </div>
  )
}
