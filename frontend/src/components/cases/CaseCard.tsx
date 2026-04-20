import { motion } from 'framer-motion'
import { FileText, Download, MessageSquare, ChevronDown, ChevronUp, AlertCircle, Layers } from 'lucide-react'
import { useState } from 'react'
import clsx from 'clsx'
import type { CaseSummary } from '@/lib/api'
import { getDownloadUrl } from '@/lib/api'
import { useActiveCaseStore } from '@/store'

interface Props {
  result:  CaseSummary
  rank:    number
  delay?:  number
}

function ConfidenceBadge({ confidence }: { confidence: string }) {
  const styles: Record<string, string> = {
    High:   'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    Medium: 'bg-gold-100 text-gold-700 dark:bg-gold-900/30 dark:text-gold-400',
    Low:    'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400',
  }
  return (
    <span className={clsx('score-badge', styles[confidence] ?? styles.Low)}>
      {confidence} match
    </span>
  )
}

export default function CaseCard({ result, rank, delay = 0 }: Props) {
  const [expanded, setExpanded] = useState(false)
  const { setActiveCase }       = useActiveCaseStore()
  const caseName = result.pdf_index.replace(/\.pdf$/i, '')

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.35, ease: 'easeOut' }}
      className="card p-5 hover:shadow-md transition-shadow duration-200"
    >
      {/* Top row */}
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 w-7 h-7 rounded-lg bg-brand-50 dark:bg-brand-950/40
                        flex items-center justify-center text-brand-600 dark:text-brand-400
                        text-xs font-mono font-semibold mt-0.5">
          {rank}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-medium text-gray-900 dark:text-gray-100 text-sm font-mono truncate max-w-xs">
              {caseName}
            </h3>
            <ConfidenceBadge confidence={result.confidence} />

            {/* Chunk hits badge */}
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs
                             text-gray-400 dark:text-gray-600">
              <Layers className="w-3 h-3" />
              {result.chunk_hits} hits
            </span>

            {!result.available && (
              <span className="score-badge bg-red-50 text-red-500 dark:bg-red-950/30 dark:text-red-400 gap-1">
                <AlertCircle className="w-3 h-3" /> PDF unavailable
              </span>
            )}
          </div>
        </div>
      </div>

      {/* AI summary */}
      <p className="mt-3 text-sm text-gray-600 dark:text-gray-400 leading-relaxed pl-10">
        {result.summary}
      </p>

      {/* Expandable snippet */}
      {result.snippet && (
        <div className="mt-3 pl-10">
          <button
            onClick={() => setExpanded(v => !v)}
            className="flex items-center gap-1 text-xs text-gray-400 dark:text-gray-600
                       hover:text-gray-600 dark:hover:text-gray-400 transition-colors"
          >
            {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            {expanded ? 'Hide' : 'Show'} source excerpt
          </button>
          {expanded && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="mt-2 p-3 rounded-xl bg-gray-50 dark:bg-gray-800/50
                         border border-gray-200 dark:border-gray-700/50
                         text-xs text-gray-500 dark:text-gray-500 leading-relaxed font-mono
                         max-h-48 overflow-y-auto"
            >
              {result.snippet}
            </motion.div>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="mt-4 pl-10 flex items-center gap-2">
        <button
          onClick={() => setActiveCase(result)}
          className="btn-primary py-1.5 px-3 text-xs"
        >
          <MessageSquare className="w-3.5 h-3.5" />
          Chat with case
        </button>
        {result.available && (
          <a
            href={getDownloadUrl(result.pdf_index)}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-secondary py-1.5 px-3 text-xs"
          >
            <Download className="w-3.5 h-3.5" />
            Download PDF
          </a>
        )}
        <button onClick={() => setActiveCase(result)} className="btn-ghost text-xs">
          <FileText className="w-3.5 h-3.5" />
          Preview
        </button>
      </div>
    </motion.div>
  )
}
