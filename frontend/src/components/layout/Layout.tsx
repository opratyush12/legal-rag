import { Scale, Moon, Sun, MessageSquare } from 'lucide-react'
import { useThemeStore } from '@/store'
import { useEffect, useState } from 'react'
import AssistantPanel from '@/components/chat/AssistantPanel'

export default function Layout({ children }: { children: React.ReactNode }) {
  const { dark, toggleDark } = useThemeStore()
  const [showAssistant, setShowAssistant] = useState(false)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
  }, [dark])

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 transition-colors duration-300">
      {/* Header */}
      <header className="sticky top-0 z-50 glass border-b border-gray-200/60 dark:border-gray-800/60">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center shadow-sm">
              <Scale className="w-4 h-4 text-white" strokeWidth={2.5} />
            </div>
            <span className="font-serif font-semibold text-lg text-gray-900 dark:text-white tracking-tight">
              Lex<span className="text-brand-500">Search</span>
            </span>
            <span className="hidden sm:inline-block px-2 py-0.5 rounded-full bg-gold-100 dark:bg-gold-900/30 text-gold-700 dark:text-gold-400 text-xs font-medium">
              34k cases
            </span>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1">
            {/* VakilAI assistant button */}
            <button
              onClick={() => setShowAssistant(v => !v)}
              className={`btn-ghost gap-1.5 text-xs ${showAssistant ? 'text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-950/30' : ''}`}
              title="VakilAI — Legal Assistant"
            >
              <MessageSquare className="w-4 h-4" />
              <span className="hidden sm:inline">VakilAI</span>
            </button>

            <button
              onClick={toggleDark}
              className="btn-ghost"
              aria-label="Toggle theme"
            >
              {dark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </header>

      {/* Page content */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        {children}
      </main>

      {/* VakilAI panel */}
      {showAssistant && <AssistantPanel onClose={() => setShowAssistant(false)} />}
    </div>
  )
}
