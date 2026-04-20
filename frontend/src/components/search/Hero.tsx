import { motion } from 'framer-motion'
import { Scale, Gavel, BookOpen, TrendingUp } from 'lucide-react'

const STATS = [
  { icon: BookOpen,    label: '34,137',    sub: 'cases indexed'     },
  { icon: Gavel,       label: 'AI-ranked', sub: 'semantic search'   },
  { icon: TrendingUp,  label: 'Groq LLM',  sub: 'instant summaries' },
]

export default function Hero() {
  return (
    <section className="text-center mb-12">
      {/* Badge */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="inline-flex items-center gap-2 px-3 py-1 rounded-full
                   bg-brand-50 dark:bg-brand-950/40 border border-brand-200 dark:border-brand-800
                   text-brand-600 dark:text-brand-400 text-xs font-medium mb-6"
      >
        <Scale className="w-3.5 h-3.5" />
        Supreme Court of India · AI-Powered Research
      </motion.div>

      {/* Heading */}
      <motion.h1
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="font-serif font-semibold text-4xl sm:text-5xl text-gray-900 dark:text-white
                   leading-tight tracking-tight mb-4"
      >
        Find the right{' '}
        <span className="text-brand-600 dark:text-brand-400">legal precedent</span>
        <br className="hidden sm:block" />
        {' '}for your case
      </motion.h1>

      {/* Subheading */}
      <motion.p
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.18 }}
        className="text-base text-gray-500 dark:text-gray-400 max-w-xl mx-auto mb-10 leading-relaxed"
      >
        Describe your scenario in plain language. Our AI searches 34k judgments,
        ranks by relevance, and lets you chat with each case instantly.
      </motion.p>

      {/* Stats */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.26 }}
        className="flex items-center justify-center gap-8 mb-10"
      >
        {STATS.map(({ icon: Icon, label, sub }) => (
          <div key={sub} className="flex flex-col items-center gap-1">
            <div className="flex items-center gap-1.5 text-gray-900 dark:text-gray-100">
              <Icon className="w-4 h-4 text-brand-500" />
              <span className="font-semibold text-sm">{label}</span>
            </div>
            <span className="text-xs text-gray-400 dark:text-gray-600">{sub}</span>
          </div>
        ))}
      </motion.div>
    </section>
  )
}
