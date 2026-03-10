import { Link } from 'react-router-dom'

const KEY_FACTS = [
  ['Case', 'PC 19700 — BC Provincial Court, Kamloops'],
  ['Trial date', 'May 19–21, 2026'],
  ['Days in care', '214 (as of March 9, 2026)'],
  ['Taxpayer cost', '$175,041.32 (documented)'],
  ['Contradictions', '23 sworn statement conflicts'],
  ['FOI gap', '906 of 1,792 pages disclosed'],
  ['OIPC complaint', 'INV-F-26-00220 (active)'],
  ['Judicial review', 'SC 064851 (MCFD defaulted)'],
]

const DOWNLOADS = [
  {
    title: 'Media Package',
    desc: 'Full structured data — contradictions, costs, timeline, legal basis (JSON)',
    href: '/api/export/media-package',
    download: false,
  },
  {
    title: 'Caryma Brief',
    desc: '8-section case brief — evidence inventory, statutory violations, SHA-256 verified (PDF)',
    href: '/api/export/caryma-brief.pdf',
    download: true,
  },
  {
    title: 'Cost Report',
    desc: 'Itemized taxpayer cost breakdown with BC government source citations (JSON)',
    href: '/api/costs',
    download: false,
  },
  {
    title: 'OG Image',
    desc: '1200×630 stats image for social sharing (PNG)',
    href: '/og-image.png',
    download: true,
  },
]

const STATUTES = [
  'CFCSA s.30 — removal without observing child',
  'FOIPPA s.33-39 — unauthorized disclosure of personal information',
  'Charter s.7 — life, liberty, security of person',
  'Charter s.2(b) — freedom of expression',
  'Mental Health Act s.96 — wellness check procedures',
]

export default function PressKit() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-mono">
      {/* Top gradient bar */}
      <div className="h-1 bg-gradient-to-r from-red-900 via-red-500 to-red-900" />

      {/* Header */}
      <header className="py-10 px-4 text-center border-b border-slate-800">
        <div className="max-w-3xl mx-auto">
          <div className="text-[10px] text-red-400 tracking-[0.3em] uppercase mb-3">
            For Journalists &amp; Legal Researchers
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-white tracking-[0.08em] mb-2">
            PRESS KIT
          </h1>
          <div className="text-[11px] text-slate-500 tracking-[0.2em]">
            The MCFD Files — PC 19700 · British Columbia, Canada
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-10 space-y-12">

        {/* Key Facts */}
        <section>
          <h2 className="text-[11px] tracking-[0.25em] text-slate-400 uppercase mb-4 border-b border-slate-800 pb-2">
            Key Facts
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-2">
            {KEY_FACTS.map(([label, value]) => (
              <div key={label} className="flex gap-3 text-[12px]">
                <span className="text-slate-500 shrink-0 min-w-[120px]">{label}</span>
                <span className="text-slate-200">{value}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Downloads */}
        <section>
          <h2 className="text-[11px] tracking-[0.25em] text-slate-400 uppercase mb-4 border-b border-slate-800 pb-2">
            Downloads
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {DOWNLOADS.map(({ title, desc, href, download }) => (
              <div key={title} className="flex flex-col gap-3 bg-slate-900/60 border border-slate-700 rounded p-4">
                <div className="text-[13px] text-slate-200">{title}</div>
                <div className="text-[11px] text-slate-500 leading-relaxed flex-1">{desc}</div>
                <a
                  href={href}
                  {...(download ? { download: true } : { target: '_blank', rel: 'noopener noreferrer' })}
                  className="self-start text-[10px] font-mono text-red-400 border border-red-700/50 rounded px-2 py-1 hover:bg-red-900/20 transition-colors"
                >
                  Download
                </a>
              </div>
            ))}
          </div>
        </section>

        {/* Statutory Framework */}
        <section>
          <h2 className="text-[11px] tracking-[0.25em] text-slate-400 uppercase mb-4 border-b border-slate-800 pb-2">
            Statutory Framework
          </h2>
          <ul className="space-y-2">
            {STATUTES.map((s) => (
              <li key={s} className="flex gap-2 text-[13px] text-slate-400">
                <span className="text-red-500 shrink-0">·</span>
                <span>{s}</span>
              </li>
            ))}
          </ul>
        </section>

        {/* Platform Notes */}
        <section>
          <h2 className="text-[11px] tracking-[0.25em] text-slate-400 uppercase mb-4 border-b border-slate-800 pb-2">
            Platform Notes
          </h2>
          <div className="space-y-2 text-[13px] text-slate-400">
            <p>Built by: Christopher LaPointe (self-represented litigant)</p>
            <p>Data sources: BC FOI, BC government published rates, court records</p>
            <p>All figures cited to public record</p>
          </div>
        </section>

        {/* Contact */}
        <section>
          <h2 className="text-[11px] tracking-[0.25em] text-slate-400 uppercase mb-4 border-b border-slate-800 pb-2">
            Contact
          </h2>
          <p className="text-[13px] text-slate-400">
            Media inquiries: via /share · OIPC on file: INV-F-26-00220 · Kamloops, BC
          </p>
        </section>

        {/* Footer */}
        <footer className="border-t border-slate-800 pt-8 pb-4 space-y-3">
          <div className="flex items-center gap-4 flex-wrap">
            <Link
              to="/share"
              className="text-[10px] text-slate-600 hover:text-slate-400 transition-colors"
            >
              ← Back to Public Record
            </Link>
            <Link
              to="/methodology"
              className="text-[10px] text-slate-600 hover:text-slate-400 transition-colors"
            >
              Methodology →
            </Link>
          </div>
          <p className="text-[10px] text-slate-700">
            This platform contains publicly verifiable information only. Not legal advice.
          </p>
        </footer>

      </main>
    </div>
  )
}
