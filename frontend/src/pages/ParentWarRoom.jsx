import { useState, useEffect } from 'react'

const TABS = [
  { id: 'foi', label: 'FOI REQUEST' },
  { id: 'complaint', label: 'COMPLAINT ENGINE' },
  { id: 'rights', label: 'RIGHTS CHECKER' },
  { id: 'patterns', label: 'PATTERN DATABASE' },
  { id: 'toolkit', label: 'SELF-REP TOOLKIT' },
  { id: 'evidence', label: 'EVIDENCE STRATEGY' },
]

const DISCLAIMER = (
  <div className="mt-6 border border-emerald-900/40 bg-emerald-950/20 rounded p-3 text-[10px] font-mono text-emerald-700 tracking-wide leading-relaxed">
    NOT LEGAL ADVICE. This tool uses public records, court decisions, and BC legislation for informational purposes only.
    Consult a lawyer or legal aid clinic before taking legal action. Use initials only when entering personal information.
    All data stays in your browser session.
  </div>
)

// ── FOI Tab ────────────────────────────────────────────────────────────────────

function FOITab() {
  const [form, setForm] = useState({
    name: '', address: '', email: '',
    date_range_start: '', date_range_end: '',
    file_numbers: '', specific_records: '',
  })
  const [letter, setLetter] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setLetter('')
    try {
      const res = await fetch('/api/warroom/foi-generator', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (!res.ok) throw new Error(`Server error ${res.status}`)
      const data = await res.json()
      setLetter(data.letter)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <p className="font-mono text-[11px] text-emerald-600 mb-4 tracking-wide">
        Generate a FOIPPA request letter for your MCFD file. Cites s.4, s.5, s.7, s.75(5).
      </p>
      <form onSubmit={submit} className="space-y-3">
        {[
          ['name', 'Your Name (initials OK)'],
          ['address', 'Your Mailing Address'],
          ['email', 'Your Email'],
          ['date_range_start', 'Date Range Start (YYYY-MM-DD)'],
          ['date_range_end', 'Date Range End (YYYY-MM-DD)'],
          ['file_numbers', 'File Numbers (optional)'],
        ].map(([k, label]) => (
          <div key={k}>
            <label className="block font-mono text-[10px] text-emerald-700 tracking-widest mb-1">{label}</label>
            <input
              value={form[k]}
              onChange={set(k)}
              className="w-full bg-[#0d1220] border border-emerald-900/50 rounded px-3 py-2 font-mono text-xs text-slate-200 focus:outline-none focus:border-emerald-600"
            />
          </div>
        ))}
        <div>
          <label className="block font-mono text-[10px] text-emerald-700 tracking-widest mb-1">Specific Records Requested</label>
          <textarea
            value={form.specific_records}
            onChange={set('specific_records')}
            rows={3}
            placeholder="e.g., all case notes, worker logs, supervision records, risk assessments, emails between workers..."
            className="w-full bg-[#0d1220] border border-emerald-900/50 rounded px-3 py-2 font-mono text-xs text-slate-200 focus:outline-none focus:border-emerald-600 resize-none"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="font-mono text-[11px] tracking-widest bg-emerald-900/60 border border-emerald-600/40 text-emerald-400 px-4 py-2 rounded hover:bg-emerald-800/60 transition-colors disabled:opacity-50"
        >
          {loading ? 'GENERATING…' : 'GENERATE LETTER'}
        </button>
      </form>
      {error && <p className="mt-4 font-mono text-xs text-red-400">{error}</p>}
      {letter && (
        <div className="mt-6">
          <div className="flex gap-2 mb-2">
            <button
              onClick={() => navigator.clipboard.writeText(letter)}
              className="font-mono text-[10px] tracking-widest border border-emerald-800/50 text-emerald-600 px-3 py-1 rounded hover:border-emerald-600 transition-colors"
            >
              COPY
            </button>
            <button
              onClick={() => window.print()}
              className="font-mono text-[10px] tracking-widest border border-emerald-800/50 text-emerald-600 px-3 py-1 rounded hover:border-emerald-600 transition-colors"
            >
              PRINT
            </button>
          </div>
          <pre className="bg-[#0d1220] border border-emerald-900/40 rounded p-4 font-mono text-xs text-slate-300 whitespace-pre-wrap leading-relaxed">
            {letter}
          </pre>
        </div>
      )}
      {DISCLAIMER}
    </div>
  )
}

// ── Complaint Tab ──────────────────────────────────────────────────────────────

const COMPLAINT_TYPES = [
  { value: 'rcy', label: 'Representative for Children & Youth (RCY)' },
  { value: 'oipc', label: 'OIPC — Privacy Commissioner' },
  { value: 'ombudsperson', label: 'BC Ombudsperson' },
  { value: 'human_rights', label: 'BC Human Rights Tribunal' },
]

function ComplaintTab() {
  const [form, setForm] = useState({ type: 'rcy', details: '', date_of_incident: '', file_numbers: '' })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await fetch('/api/warroom/complaint-generator', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (!res.ok) throw new Error(`Server error ${res.status}`)
      setResult(await res.json())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <p className="font-mono text-[11px] text-emerald-600 mb-4 tracking-wide">
        Generate a formal complaint letter to the appropriate oversight body.
      </p>
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className="block font-mono text-[10px] text-emerald-700 tracking-widest mb-1">COMPLAINT BODY</label>
          <select
            value={form.type}
            onChange={set('type')}
            className="w-full bg-[#0d1220] border border-emerald-900/50 rounded px-3 py-2 font-mono text-xs text-slate-200 focus:outline-none focus:border-emerald-600"
          >
            {COMPLAINT_TYPES.map(t => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>
        {[
          ['date_of_incident', 'Date of Incident (YYYY-MM-DD)'],
          ['file_numbers', 'File Numbers (optional)'],
        ].map(([k, label]) => (
          <div key={k}>
            <label className="block font-mono text-[10px] text-emerald-700 tracking-widest mb-1">{label}</label>
            <input
              value={form[k]}
              onChange={set(k)}
              className="w-full bg-[#0d1220] border border-emerald-900/50 rounded px-3 py-2 font-mono text-xs text-slate-200 focus:outline-none focus:border-emerald-600"
            />
          </div>
        ))}
        <div>
          <label className="block font-mono text-[10px] text-emerald-700 tracking-widest mb-1">What Happened</label>
          <textarea
            value={form.details}
            onChange={set('details')}
            rows={5}
            placeholder="Describe what happened in your own words..."
            className="w-full bg-[#0d1220] border border-emerald-900/50 rounded px-3 py-2 font-mono text-xs text-slate-200 focus:outline-none focus:border-emerald-600 resize-none"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="font-mono text-[11px] tracking-widest bg-emerald-900/60 border border-emerald-600/40 text-emerald-400 px-4 py-2 rounded hover:bg-emerald-800/60 transition-colors disabled:opacity-50"
        >
          {loading ? 'GENERATING…' : 'GENERATE COMPLAINT'}
        </button>
      </form>
      {error && <p className="mt-4 font-mono text-xs text-red-400">{error}</p>}
      {result && (
        <div className="mt-6 space-y-4">
          <div className="bg-[#0d1220] border border-emerald-900/40 rounded p-3 font-mono text-[10px] text-emerald-700 leading-relaxed">
            <span className="text-emerald-500 tracking-widest">SEND TO:</span><br />
            <span className="text-slate-400 whitespace-pre-line">{result.office_address}</span>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => navigator.clipboard.writeText(result.letter)}
              className="font-mono text-[10px] tracking-widest border border-emerald-800/50 text-emerald-600 px-3 py-1 rounded hover:border-emerald-600 transition-colors"
            >
              COPY
            </button>
            <button
              onClick={() => window.print()}
              className="font-mono text-[10px] tracking-widest border border-emerald-800/50 text-emerald-600 px-3 py-1 rounded hover:border-emerald-600 transition-colors"
            >
              PRINT
            </button>
          </div>
          <pre className="bg-[#0d1220] border border-emerald-900/40 rounded p-4 font-mono text-xs text-slate-300 whitespace-pre-wrap leading-relaxed">
            {result.letter}
          </pre>
        </div>
      )}
      {DISCLAIMER}
    </div>
  )
}

// ── Rights Checker Tab ─────────────────────────────────────────────────────────

function RightsTab() {
  const [text, setText] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    if (!text.trim()) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await fetch('/api/warroom/rights-check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ what_happened: text }),
      })
      if (!res.ok) throw new Error(`Server error ${res.status}`)
      setResult(await res.json())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <p className="font-mono text-[11px] text-emerald-600 mb-4 tracking-wide">
        Describe what happened in plain language. R2 will identify potential rights violations using BC court decisions.
      </p>
      <form onSubmit={submit} className="space-y-3">
        <textarea
          value={text}
          onChange={e => setText(e.target.value)}
          rows={6}
          placeholder="e.g., MCFD removed my child without warning and did not provide me with the removal documents. The worker refused to tell me where my child was placed..."
          className="w-full bg-[#0d1220] border border-emerald-900/50 rounded px-3 py-2 font-mono text-xs text-slate-200 focus:outline-none focus:border-emerald-600 resize-none"
        />
        <button
          type="submit"
          disabled={loading}
          className="font-mono text-[11px] tracking-widest bg-emerald-900/60 border border-emerald-600/40 text-emerald-400 px-4 py-2 rounded hover:bg-emerald-800/60 transition-colors disabled:opacity-50"
        >
          {loading ? 'ANALYZING…' : 'CHECK MY RIGHTS'}
        </button>
      </form>
      {error && <p className="mt-4 font-mono text-xs text-red-400">{error}</p>}
      {result && (
        <div className="mt-6 space-y-4">
          {result.violations?.length === 0 && (
            <p className="font-mono text-xs text-slate-500">No clear violations identified. Consult a lawyer for a full assessment.</p>
          )}
          {result.violations?.map((v, i) => (
            <div key={i} className="border border-emerald-900/40 rounded p-4 bg-[#0d1220]">
              <div className="flex items-center gap-2 mb-2">
                <span className="font-mono text-[10px] bg-emerald-900/40 text-emerald-400 px-2 py-0.5 rounded tracking-widest">{v.section}</span>
                <span className="font-mono text-xs text-slate-200 font-medium">{v.title}</span>
              </div>
              <p className="font-mono text-[11px] text-slate-400 leading-relaxed mb-2">{v.explanation}</p>
              <div className="border-l-2 border-emerald-700/40 pl-3">
                <span className="font-mono text-[10px] text-emerald-600 tracking-widest">WHAT TO DO: </span>
                <span className="font-mono text-[11px] text-slate-300">{v.what_to_do}</span>
              </div>
            </div>
          ))}
          {result.patterns_matched?.length > 0 && (
            <div className="border border-emerald-900/30 rounded p-3 bg-emerald-950/10">
              <p className="font-mono text-[10px] text-emerald-600 tracking-widest mb-2">PATTERNS MATCHED IN COURT DECISIONS:</p>
              <ul className="space-y-1">
                {result.patterns_matched.map((p, i) => (
                  <li key={i} className="font-mono text-[11px] text-slate-400">· {p}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
      {DISCLAIMER}
    </div>
  )
}

// ── Pattern Database Tab ───────────────────────────────────────────────────────

function PatternsTab() {
  const [patterns, setPatterns] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/warroom/patterns-summary')
      .then(r => r.json())
      .then(setPatterns)
      .catch(() => setPatterns([]))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <p className="font-mono text-[11px] text-emerald-600 mb-1 tracking-wide">
        Top entities found across <span className="text-emerald-400">1,352 court decisions</span> involving MCFD.
      </p>
      <p className="font-mono text-[10px] text-slate-600 mb-4">Frequency = number of decisions mentioning this entity.</p>
      {loading && <p className="font-mono text-xs text-slate-600">LOADING PATTERNS…</p>}
      {patterns && patterns.length === 0 && (
        <p className="font-mono text-xs text-slate-600">No pattern data available yet.</p>
      )}
      {patterns && patterns.length > 0 && (
        <div className="space-y-2">
          {patterns.map((p, i) => (
            <div key={i} className="flex items-center gap-3 border border-emerald-900/30 rounded px-3 py-2 bg-[#0d1220]">
              <span className="font-mono text-[10px] text-emerald-700 w-6 text-right">{i + 1}</span>
              <div className="flex-1">
                <span className="font-mono text-xs text-slate-200">{p.name}</span>
                <span className="ml-2 font-mono text-[10px] text-slate-600">{p.type}</span>
              </div>
              <span className="font-mono text-[11px] text-emerald-500">{p.frequency.toLocaleString()}×</span>
            </div>
          ))}
        </div>
      )}
      {DISCLAIMER}
    </div>
  )
}

// ── Self-Rep Toolkit Tab ───────────────────────────────────────────────────────

function ToolkitTab() {
  const [guide, setGuide] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/warroom/self-rep-guide')
      .then(r => r.json())
      .then(setGuide)
      .catch(() => setGuide(null))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="font-mono text-xs text-slate-600">LOADING GUIDE…</p>
  if (!guide) return <p className="font-mono text-xs text-red-400">Failed to load guide.</p>

  return (
    <div className="space-y-8">
      {/* Filing Deadlines */}
      <section>
        <h3 className="font-mono text-[11px] text-emerald-500 tracking-widest mb-3 uppercase">Key Deadlines</h3>
        <div className="space-y-2">
          {guide.filing_deadlines.map((d, i) => (
            <div key={i} className="flex gap-4 border border-emerald-900/30 rounded px-3 py-2 bg-[#0d1220]">
              <span className="font-mono text-[11px] text-slate-300 flex-1">{d.item}</span>
              <span className="font-mono text-[10px] text-emerald-600 text-right flex-shrink-0">{d.deadline}</span>
            </div>
          ))}
        </div>
      </section>

      {/* CFCSA Plain Language */}
      <section>
        <h3 className="font-mono text-[11px] text-emerald-500 tracking-widest mb-3 uppercase">CFCSA Plain Language</h3>
        <div className="space-y-2">
          {guide.cfcsa_plain_language.map((s, i) => (
            <div key={i} className="border border-emerald-900/30 rounded px-3 py-2 bg-[#0d1220]">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-mono text-[10px] bg-emerald-900/40 text-emerald-400 px-2 py-0.5 rounded">{s.section}</span>
                <span className="font-mono text-xs text-slate-200">{s.title}</span>
              </div>
              <p className="font-mono text-[11px] text-slate-400 leading-relaxed">{s.plain}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Legal Aid */}
      <section>
        <h3 className="font-mono text-[11px] text-emerald-500 tracking-widest mb-3 uppercase">Legal Aid &amp; Support</h3>
        <div className="space-y-2">
          {guide.legal_aid_links.map((l, i) => (
            <div key={i} className="border border-emerald-900/30 rounded px-3 py-2 bg-[#0d1220]">
              <span className="font-mono text-xs text-emerald-400">{l.name}</span>
              <span className="font-mono text-[10px] text-slate-500 ml-2">— {l.note}</span>
              <div className="font-mono text-[10px] text-slate-600 mt-0.5">{l.url}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Evidence Checklist */}
      <section>
        <h3 className="font-mono text-[11px] text-emerald-500 tracking-widest mb-3 uppercase">Evidence Checklist</h3>
        <ul className="space-y-1">
          {guide.evidence_checklist.map((item, i) => (
            <li key={i} className="font-mono text-[11px] text-slate-400 flex gap-2">
              <span className="text-emerald-700">·</span>{item}
            </li>
          ))}
        </ul>
      </section>

      {/* Pharmacogenomics */}
      <section>
        <h3 className="font-mono text-[11px] text-emerald-500 tracking-widest mb-3 uppercase">{guide.pharmacogenomics.title}</h3>
        <div className="border border-emerald-900/40 rounded p-4 bg-[#0d1220]">
          <p className="font-mono text-[11px] text-slate-300 leading-relaxed mb-3">{guide.pharmacogenomics.summary}</p>
          <p className="font-mono text-[10px] text-emerald-700 tracking-widest mb-1">PROVIDERS:</p>
          <ul className="space-y-1 mb-3">
            {guide.pharmacogenomics.providers.map((p, i) => (
              <li key={i} className="font-mono text-[11px] text-slate-400">· {p}</li>
            ))}
          </ul>
          <p className="font-mono text-[10px] text-slate-500 leading-relaxed">{guide.pharmacogenomics.how_to_use}</p>
        </div>
      </section>

      {DISCLAIMER}
    </div>
  )
}

// ── Evidence Strategy Tab ──────────────────────────────────────────────────────

function EvidenceTab() {
  const strategies = [
    {
      title: 'BC One-Party Consent Recording',
      content: 'In BC, you can legally record any conversation you are a party to without the other person\'s consent (Criminal Code s.184(2)(a)). This includes phone calls, home visits, and meetings. Use your phone\'s voice memo app. Always record every interaction with MCFD workers. Label recordings with date, worker name, and purpose.',
    },
    {
      title: 'FOI Organization System',
      content: 'When your FOI records arrive, organize them chronologically by date. Create a spreadsheet: Date | Worker | Document Type | Key Content | Contradicts. Flag every date discrepancy, missing entry, or event mentioned in court that does not appear in the file. Gaps in records are themselves evidence.',
    },
    {
      title: 'Contradiction Spotting',
      content: 'Compare affidavits against case notes. Compare case notes against emails. Compare what workers said in court against what they wrote. Note exact dates, times, and word choices. In BC courts, established credibility issues with one worker can be used to challenge other evidence from the same ministry.',
    },
    {
      title: 'Pharmacogenomic Testing as Evidence',
      content: 'If medication non-compliance or adverse reactions have been raised as concerns, request pharmacogenomic testing through your GP. A poor metabolizer result explains biological — not behavioural — causes. Submit the lab report as medical evidence with an expert letter. Cites CFCSA s.4(1)(b).',
    },
    {
      title: 'Get Everything in Writing',
      content: 'After every verbal interaction, send a follow-up email: "As per our conversation today [date], you said X. Please confirm or correct." This creates a contemporaneous written record. If the worker does not respond, the email stands as your record. Courts give weight to contemporaneous notes.',
    },
    {
      title: 'Support Network Documentation',
      content: 'Collect letters from everyone who can speak to your parenting: teachers, doctors, family members, neighbours, coaches, religious leaders. Letters should be specific — not "C is a good parent" but "I observed C attending every appointment, managing meltdowns calmly, advocating for N\'s medical needs." File all support letters in the court record early.',
    },
  ]

  return (
    <div className="space-y-4">
      {strategies.map((s, i) => (
        <div key={i} className="border border-emerald-900/40 rounded p-4 bg-[#0d1220]">
          <h3 className="font-mono text-xs text-emerald-400 tracking-widest mb-2">{s.title}</h3>
          <p className="font-mono text-[11px] text-slate-400 leading-relaxed">{s.content}</p>
        </div>
      ))}
      {DISCLAIMER}
    </div>
  )
}

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function ParentWarRoom() {
  const [activeTab, setActiveTab] = useState('foi')

  return (
    <div className="min-h-screen bg-[#0a0e1a] text-slate-200 font-sans">
      {/* Top accent */}
      <div className="h-px bg-gradient-to-r from-transparent via-emerald-500/60 to-transparent" />

      {/* Header */}
      <header className="border-b border-emerald-900/40 bg-[#0a0e1a]/90 backdrop-blur-sm sticky top-0 z-20">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="font-mono text-xl tracking-[0.2em] text-emerald-400 leading-none">
              PARENT WAR ROOM
            </h1>
            <p className="font-mono text-[10px] text-slate-600 tracking-widest mt-1">
              Facts · Public Records · Your Rights
            </p>
          </div>
          <span className="font-mono text-[10px] tracking-widest bg-red-900/30 border border-red-700/40 text-red-400 px-3 py-1 rounded">
            CLASSIFIED
          </span>
        </div>
      </header>

      {/* Tabs */}
      <div className="border-b border-emerald-900/30 bg-[#0a0e1a] sticky top-[61px] z-10">
        <div className="max-w-5xl mx-auto px-4">
          <div className="flex gap-0 overflow-x-auto">
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`font-mono text-[10px] tracking-widest px-4 py-3 flex-shrink-0 border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-emerald-500 text-emerald-400'
                    : 'border-transparent text-slate-600 hover:text-slate-400'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <main className="max-w-5xl mx-auto px-4 py-8">
        {activeTab === 'foi' && <FOITab />}
        {activeTab === 'complaint' && <ComplaintTab />}
        {activeTab === 'rights' && <RightsTab />}
        {activeTab === 'patterns' && <PatternsTab />}
        {activeTab === 'toolkit' && <ToolkitTab />}
        {activeTab === 'evidence' && <EvidenceTab />}
      </main>
    </div>
  )
}
