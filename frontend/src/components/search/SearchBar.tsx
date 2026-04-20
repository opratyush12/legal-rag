import { useRef, KeyboardEvent, useCallback, useState } from 'react'
import { Search, Mic, MicOff, Loader2, Sparkles, Upload, FileText, X } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import clsx from 'clsx'
import toast from 'react-hot-toast'
import { useSearch } from '@/hooks/useSearch'
import { useVoice } from '@/hooks/useVoice'
import { useSearchStore } from '@/store'
import { searchFromPdf } from '@/lib/api'
import { cleanPastedText } from '@/lib/textUtils'

const EXAMPLES = [
  'Tenant evicted without notice after 5 years of occupation',
  'Employee dismissed without enquiry after 20 years of service',
  'Property dispute between brothers over ancestral land partition',
  'Bail denied to accused in financial fraud — grounds to challenge',
]

interface Props {
  compact?: boolean
}

export default function SearchBar({ compact = false }: Props) {
  const { query, setQuery, submit, loading } = useSearch()
  const { setLoading, setResults, setError } = useSearchStore()
  const { listening, startListening, stopListening } = useVoice()
  const textareaRef  = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [uploading,    setUploading]    = useState(false)

  // ── Paste handler — clean PDF artifacts ───────────────────────────────────
  const handlePaste = useCallback((e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const raw = e.clipboardData.getData('text')
    if (!raw) return
    const cleaned = cleanPastedText(raw)
    if (cleaned !== raw) {
      e.preventDefault()
      // Insert cleaned text at cursor position
      const el    = e.currentTarget
      const start = el.selectionStart ?? 0
      const end   = el.selectionEnd   ?? 0
      const next  = query.slice(0, start) + cleaned + query.slice(end)
      setQuery(next)
      toast.success('PDF text cleaned — escape characters removed', { duration: 2000 })
    }
    // If text is clean, let default paste happen
  }, [query, setQuery])

  // ── Keyboard submit ────────────────────────────────────────────────────────
  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      submit()
    }
  }

  // ── Voice ──────────────────────────────────────────────────────────────────
  const handleVoice = () => {
    if (listening) { stopListening(); return }
    startListening((transcript) => {
      setQuery(transcript)
      setTimeout(() => submit(transcript), 300)
    })
  }

  // ── PDF file upload ────────────────────────────────────────────────────────
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      toast.error('Only PDF files are supported.')
      return
    }
    if (file.size > 20 * 1024 * 1024) {
      toast.error('PDF too large. Max 20 MB.')
      return
    }
    setUploadedFile(file)
    await runPdfSearch(file)
    // Reset input so same file can be re-uploaded
    e.target.value = ''
  }

  const runPdfSearch = async (file: File) => {
    setUploading(true)
    setLoading(true)
    setError(null)
    try {
      toast.loading('Extracting text from PDF…', { id: 'pdf-upload' })
      const data = await searchFromPdf(file)
      toast.success(`Found ${data.results.length} matching cases`, { id: 'pdf-upload' })
      setResults(data.results, data.expanded_queries ?? [])
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? 'PDF search failed.'
      toast.error(msg, { id: 'pdf-upload' })
      setError(msg)
    } finally {
      setUploading(false)
      setLoading(false)
    }
  }

  const clearFile = () => {
    setUploadedFile(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const isLoading = loading || uploading

  return (
    <div className={clsx('w-full', !compact && 'max-w-3xl mx-auto')}>
      {/* Uploaded file pill */}
      <AnimatePresence>
        {uploadedFile && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="mb-2 inline-flex items-center gap-2 px-3 py-1.5 rounded-full
                       bg-brand-50 dark:bg-brand-950/40 border border-brand-200 dark:border-brand-800
                       text-brand-700 dark:text-brand-400 text-xs"
          >
            <FileText className="w-3.5 h-3.5" />
            {uploadedFile.name}
            <button onClick={clearFile} className="ml-1 hover:text-red-500 transition-colors">
              <X className="w-3 h-3" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main textarea */}
      <div className="relative group">
        <div className={clsx(
          'relative rounded-2xl border transition-all duration-200',
          'bg-white dark:bg-gray-900',
          'border-gray-200 dark:border-gray-700',
          'group-focus-within:border-brand-500 group-focus-within:ring-4 group-focus-within:ring-brand-500/10',
          'shadow-sm group-focus-within:shadow-md',
        )}>
          <div className="absolute left-4 top-4 text-gray-400 dark:text-gray-500 pointer-events-none">
            <Search className="w-5 h-5" />
          </div>

          <textarea
            ref={textareaRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKey}
            onPaste={handlePaste}
            placeholder="Describe your legal scenario, or paste text from a case PDF…"
            rows={compact ? 2 : 4}
            className={clsx(
              'w-full resize-none bg-transparent',
              'pl-12 pr-28 py-4',
              'text-gray-900 dark:text-gray-100',
              'placeholder-gray-400 dark:placeholder-gray-600',
              'text-sm leading-relaxed',
              'focus:outline-none',
            )}
          />

          {/* Right action buttons */}
          <div className="absolute right-3 bottom-3 flex items-center gap-1.5">
            {/* PDF upload */}
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileChange}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isLoading}
              className={clsx(
                'p-2 rounded-lg transition-all duration-200',
                'text-gray-400 hover:text-brand-600 dark:hover:text-brand-400',
                'hover:bg-brand-50 dark:hover:bg-brand-950/30',
                'disabled:opacity-40 disabled:cursor-not-allowed',
              )}
              title="Upload a PDF to find similar cases"
            >
              {uploading
                ? <Loader2 className="w-4 h-4 animate-spin" />
                : <Upload className="w-4 h-4" />}
            </button>

            {/* Voice */}
            <button
              onClick={handleVoice}
              className={clsx(
                'p-2 rounded-lg transition-all duration-200',
                listening
                  ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 animate-pulse-soft'
                  : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800',
              )}
              title={listening ? 'Stop listening' : 'Speak your scenario'}
            >
              {listening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </button>

            {/* Text search */}
            <button
              onClick={() => submit()}
              disabled={isLoading || query.trim().length < 10}
              className="btn-primary py-2 px-3 text-xs"
            >
              {isLoading
                ? <Loader2 className="w-4 h-4 animate-spin" />
                : <Sparkles className="w-4 h-4" />}
              {isLoading ? 'Searching…' : 'Search'}
            </button>
          </div>
        </div>

        {/* Hints */}
        <div className="mt-2 flex items-center gap-3 pl-1">
          <p className="text-xs text-gray-400 dark:text-gray-600">
            <kbd className="px-1 py-0.5 rounded bg-gray-100 dark:bg-gray-800 font-mono">Ctrl+Enter</kbd> to search
            · Paste PDF text directly · Upload PDF
          </p>
        </div>
      </div>

      {/* Example pills — landing only */}
      {!compact && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mt-5 flex flex-wrap gap-2"
        >
          <span className="text-xs text-gray-400 dark:text-gray-600 self-center">Try:</span>
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => { setQuery(ex); submit(ex) }}
              className="text-xs px-3 py-1.5 rounded-full border border-gray-200 dark:border-gray-700
                         text-gray-600 dark:text-gray-400 hover:border-brand-400 hover:text-brand-600
                         dark:hover:border-brand-500 dark:hover:text-brand-400
                         transition-all duration-150 bg-white dark:bg-gray-900 hover:bg-brand-50 dark:hover:bg-brand-950/30"
            >
              {ex.length > 50 ? ex.slice(0, 50) + '…' : ex}
            </button>
          ))}
        </motion.div>
      )}
    </div>
  )
}
