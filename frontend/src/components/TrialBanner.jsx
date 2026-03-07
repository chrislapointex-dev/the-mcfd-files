import { useState, useEffect } from 'react'

export default function TrialBanner() {
  const [days, setDays] = useState(null)

  useEffect(() => {
    fetch('/api/trialprep/summary')
      .then(r => r.ok ? r.json() : null)
      .then(d => d && setDays(d.days_remaining))
      .catch(() => {})
  }, [])

  if (days === null || days >= 30) return null

  return (
    <div className="bg-red-900/30 border border-red-500/50 rounded px-4 py-2 text-center">
      <p className="font-mono text-xs text-red-400 tracking-widest font-bold">
        TRIAL IN {days} DAYS — MAY 19–21, 2026
      </p>
    </div>
  )
}
