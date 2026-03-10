import { Link } from 'react-router-dom'

export default function Methodology() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-mono">
      {/* Top gradient bar */}
      <div className="h-1 bg-gradient-to-r from-red-900 via-red-500 to-red-900" />

      {/* Header */}
      <header className="py-10 px-4 text-center border-b border-slate-800">
        <div className="max-w-3xl mx-auto">
          <div className="text-[10px] text-red-400 tracking-[0.3em] uppercase mb-3">
            Transparency &amp; Methods
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-white tracking-[0.08em] mb-2">
            METHODOLOGY
          </h1>
          <div className="text-[11px] text-slate-500 tracking-[0.2em]">
            How This Record Is Built · PC 19700
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-10 space-y-12">

        {/* Data Sources */}
        <section>
          <h2 className="text-[11px] tracking-[0.25em] text-slate-400 uppercase mb-4 border-b border-slate-800 pb-2">
            Data Sources
          </h2>
          <div className="space-y-3 text-[13px] text-slate-400 leading-relaxed">
            <p>
              All data in this record comes from one or more of the following official sources:
            </p>
            <ul className="space-y-2 pl-4">
              <li className="flex gap-2">
                <span className="text-red-500 shrink-0">·</span>
                <span><span className="text-slate-200">Sworn affidavits and court filings</span> — documents filed in BC Provincial Court under case PC 19700 and PC 19709. These are sworn statements subject to perjury penalties.</span>
              </li>
              <li className="flex gap-2">
                <span className="text-red-500 shrink-0">·</span>
                <span><span className="text-slate-200">FOI disclosures</span> — records obtained via Freedom of Information requests under the BC <em>Freedom of Information and Protection of Privacy Act</em>. The gap between disclosed pages (906) and MCFD's stated total (1,792) is documented in OIPC complaint INV-F-26-00220.</span>
              </li>
              <li className="flex gap-2">
                <span className="text-red-500 shrink-0">·</span>
                <span><span className="text-slate-200">BC government published rates</span> — all cost figures use rates published by the Government of British Columbia in official service plans, salary grids, and MCFD annual reports.</span>
              </li>
              <li className="flex gap-2">
                <span className="text-red-500 shrink-0">·</span>
                <span><span className="text-slate-200">Video and audio recordings</span> — lawfully recorded interactions preserved as evidence under s.7 and s.8 of the <em>Canadian Charter of Rights and Freedoms</em>.</span>
              </li>
              <li className="flex gap-2">
                <span className="text-red-500 shrink-0">·</span>
                <span><span className="text-slate-200">Medical and genetic records</span> — clinical reports from BC Children's Hospital and CEN4GEN (genetics). Phelan-McDermid syndrome ruled out May 2024.</span>
              </li>
            </ul>
          </div>
        </section>

        {/* Contradiction Detection */}
        <section>
          <h2 className="text-[11px] tracking-[0.25em] text-slate-400 uppercase mb-4 border-b border-slate-800 pb-2">
            Contradiction Detection
          </h2>
          <div className="space-y-3 text-[13px] text-slate-400 leading-relaxed">
            <p>
              Contradictions are identified by comparing sworn statements against each other and against
              documentary evidence (video recordings, FOI records, medical reports). Each contradiction
              is classified by severity:
            </p>
            <div className="border border-slate-800 rounded overflow-hidden mt-3">
              <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-800">
                <span className="font-mono text-[9px] px-1.5 py-0.5 rounded tracking-widest bg-red-900/60 text-red-300 border border-red-700/50 shrink-0">DIRECT</span>
                <span className="text-[12px] text-slate-300">A sworn statement directly contradicts verifiable evidence (video, document, or another sworn statement on the same specific fact).</span>
              </div>
              <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-800">
                <span className="font-mono text-[9px] px-1.5 py-0.5 rounded tracking-widest bg-amber-900/60 text-amber-300 border border-amber-700/50 shrink-0">PARTIAL</span>
                <span className="text-[12px] text-slate-300">A statement is inconsistent with or materially incomplete relative to the documented record, but not a direct factual inversion.</span>
              </div>
              <div className="flex items-center gap-3 px-4 py-3">
                <span className="font-mono text-[9px] px-1.5 py-0.5 rounded tracking-widest bg-slate-800 text-slate-400 border border-slate-700/50 shrink-0">NONE</span>
                <span className="text-[12px] text-slate-300">Flagged for review but no contradiction confirmed at this time.</span>
              </div>
            </div>
            <p className="text-[12px] text-slate-500 mt-2">
              All contradictions are reviewed and entered manually. AI tools are used for pattern
              analysis and cross-referencing, not for generating factual claims.
            </p>
          </div>
        </section>

        {/* Cost Methodology */}
        <section>
          <h2 className="text-[11px] tracking-[0.25em] text-slate-400 uppercase mb-4 border-b border-slate-800 pb-2">
            Cost Methodology
          </h2>
          <div className="space-y-3 text-[13px] text-slate-400 leading-relaxed">
            <p>
              Documented costs ($175,041.32) are calculated using publicly available BC government rates
              applied to the documented duration of state intervention (214 days, beginning July 2024).
            </p>
            <ul className="space-y-2 pl-4">
              <li className="flex gap-2">
                <span className="text-red-500 shrink-0">·</span>
                <span><span className="text-slate-200">Social worker salaries</span> — BC Public Service salary grids, Grid 27 classification, mid-step rate.</span>
              </li>
              <li className="flex gap-2">
                <span className="text-red-500 shrink-0">·</span>
                <span><span className="text-slate-200">Court time</span> — BC Provincial Court operations cost per day, derived from BC Court Services Annual Report.</span>
              </li>
              <li className="flex gap-2">
                <span className="text-red-500 shrink-0">·</span>
                <span><span className="text-slate-200">Legal Aid</span> — Legal Aid BC published hourly rates for child protection matters.</span>
              </li>
              <li className="flex gap-2">
                <span className="text-red-500 shrink-0">·</span>
                <span><span className="text-slate-200">Placement costs</span> — MCFD published foster care and residential service rates.</span>
              </li>
              <li className="flex gap-2">
                <span className="text-red-500 shrink-0">·</span>
                <span><span className="text-slate-200">Scale estimate</span> ($1.4B–$2.1B) — applied per-case rate to BC MCFD's 5,000 children-in-care figure from the 2024–25 Annual Service Plan. This is an illustrative projection, not a MCFD-published total.</span>
              </li>
            </ul>
          </div>
        </section>

        {/* What This Platform Is */}
        <section>
          <h2 className="text-[11px] tracking-[0.25em] text-slate-400 uppercase mb-4 border-b border-slate-800 pb-2">
            What This Platform Is
          </h2>
          <div className="space-y-3 text-[13px] text-slate-400 leading-relaxed">
            <p>
              The MCFD Files is a personal accountability platform built by a parent involved in a BC
              child protection proceeding (PC 19700). It is not a government resource, not a legal advice
              service, and not affiliated with MCFD or any court.
            </p>
            <p>
              Its purpose is to make the documented record of this case available in a clear, searchable,
              and verifiable format — for journalists, lawyers, researchers, and the public — before the
              scheduled trial date of May 19–21, 2026.
            </p>
            <p>
              Every factual claim on this platform is tied to a source document. No claim is generated
              from speculation. Where uncertainty exists, it is marked.
            </p>
          </div>
        </section>

        {/* Limitations */}
        <section>
          <h2 className="text-[11px] tracking-[0.25em] text-slate-400 uppercase mb-4 border-b border-slate-800 pb-2">
            Limitations
          </h2>
          <div className="space-y-3 text-[13px] text-slate-400 leading-relaxed">
            <ul className="space-y-2 pl-4">
              <li className="flex gap-2">
                <span className="text-red-500 shrink-0">·</span>
                <span>Cost figures are estimates based on published rates. Actual government expenditure may differ if internal rates or overhead factors are applied differently.</span>
              </li>
              <li className="flex gap-2">
                <span className="text-red-500 shrink-0">·</span>
                <span>The FOI page gap (906 vs 1,792) is documented in the OIPC complaint. MCFD has not publicly explained the discrepancy.</span>
              </li>
              <li className="flex gap-2">
                <span className="text-red-500 shrink-0">·</span>
                <span>This record reflects one party's perspective in an active legal proceeding. Court determinations have not yet been made.</span>
              </li>
              <li className="flex gap-2">
                <span className="text-red-500 shrink-0">·</span>
                <span>AI-assisted analysis (cross-referencing, pattern detection) is used as a research tool only. All conclusions are reviewed by the case participant before publication.</span>
              </li>
            </ul>
          </div>
        </section>

        {/* Footer */}
        <footer className="border-t border-slate-800 pt-8 pb-4 space-y-2">
          <p className="text-[10px] text-slate-600">
            OIPC Complaint INV-F-26-00220 · Trial: May 19–21, 2026, BC Provincial Court, Kamloops
          </p>
          <p className="text-[10px] text-slate-600 mt-3">
            <Link to="/share" className="text-slate-500 hover:text-slate-300 transition-colors">
              ← Back to Public Record
            </Link>
          </p>
        </footer>

      </main>
    </div>
  )
}
