import { AnimatePresence, motion } from 'framer-motion'
import { useSearchStore } from '@/store'
import CaseCard from '@/components/cases/CaseCard'
import ResultsSkeleton from '@/components/ui/ResultsSkeleton'
import { SearchX, Sparkles } from 'lucide-react'

export default function ResultsList() {
  const { results, loading, searched, error, expandedQueries } = useSearchStore()

  if (loading) return <ResultsSkeleton />

  if (error) return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
      className="text-center py-16 text-red-500 dark:text-red-400">
      <p className="text-sm">{error}</p>
    </motion.div>
  )

  if (searched && results.length === 0) return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
      className="text-center py-16 text-gray-400 dark:text-gray-600">
      <SearchX className="w-10 h-10 mx-auto mb-3 opacity-50" />
      <p className="text-sm">No matching cases found. Try rephrasing your scenario.</p>
    </motion.div>
  )

  if (!searched) return null

  return (
    <div className="mt-8">
      {/* Meta row */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="mb-4 space-y-2"
      >
        <p className="text-xs text-gray-400 dark:text-gray-600">
          {results.length} best matching case{results.length !== 1 ? 's' : ''} found
        </p>

        {/* Show expanded queries if more than 1 */}
        {expandedQueries && expandedQueries.length > 1 && (
          <div className="flex items-start gap-2 flex-wrap">
            <span className="inline-flex items-center gap-1 text-xs text-brand-500 dark:text-brand-400 mt-0.5">
              <Sparkles className="w-3 h-3" />
              Also searched:
            </span>
            {expandedQueries.slice(1).map((q, i) => (
              <span
                key={i}
                className="text-xs px-2 py-0.5 rounded-full
                           bg-brand-50 dark:bg-brand-950/30
                           text-brand-600 dark:text-brand-400
                           border border-brand-100 dark:border-brand-900"
              >
                {q}
              </span>
            ))}
          </div>
        )}
      </motion.div>

      <div className="flex flex-col gap-4">
        <AnimatePresence>
          {results.map((r, i) => (
            <CaseCard key={r.pdf_index} result={r} rank={i + 1} delay={i * 0.07} />
          ))}
        </AnimatePresence>
      </div>
    </div>
  )
}
