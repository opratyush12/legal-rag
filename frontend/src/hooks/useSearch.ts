import { useCallback } from 'react'
import toast from 'react-hot-toast'
import { searchCases } from '@/lib/api'
import { useSearchStore } from '@/store'

export function useSearch() {
  const { query, setQuery, setResults, setLoading, setError, loading } = useSearchStore()

  const submit = useCallback(
    async (q?: string) => {
      const text = (q ?? query).trim()
      if (!text || text.length < 10) {
        toast.error('Please describe your scenario in at least 10 characters.')
        return
      }
      setLoading(true)
      setError(null)
      try {
        const data = await searchCases(text, 5)
        setResults(data.results, data.expanded_queries ?? [text])
        if (data.results.length === 0) toast('No matching cases found.', { icon: '🔍' })
      } catch (err: unknown) {
        const msg = (err as { response?: { data?: { detail?: string } } })
          ?.response?.data?.detail ?? 'Search failed. Is the backend running?'
        setError(msg)
        toast.error(msg)
      } finally {
        setLoading(false)
      }
    },
    [query, setLoading, setError, setResults],
  )

  return { query, setQuery, submit, loading }
}
