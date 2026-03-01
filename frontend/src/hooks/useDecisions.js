import { useState, useEffect } from 'react'

export function useDecisions({ mode, query, filters, page, perPage = 20 }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const { court, dateFrom, dateTo, source } = filters

  useEffect(() => {
    if (mode === 'detail') return

    const controller = new AbortController()
    setLoading(true)

    const params = new URLSearchParams()
    if (mode === 'search' && query) params.set('q', query)
    if (source) params.set('source', source)
    if (court) params.set('court', court)
    if (dateFrom) params.set('date_from', dateFrom)
    if (dateTo) params.set('date_to', dateTo)
    params.set('page', String(page))
    params.set('per_page', String(perPage))

    const endpoint = mode === 'search' ? '/api/decisions/search' : '/api/decisions'

    fetch(`${endpoint}?${params}`, { signal: controller.signal })
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(d => {
        setData(d)
        setLoading(false)
        setError(null)
      })
      .catch(err => {
        if (err.name === 'AbortError') return
        setError(err.message)
        setLoading(false)
      })

    return () => controller.abort()
  }, [mode, query, source, court, dateFrom, dateTo, page, perPage])

  return { data, loading, error }
}
