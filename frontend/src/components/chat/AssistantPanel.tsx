/**
 * AssistantPanel.tsx — VakilAI general legal assistant
 * - Hindi + English auto-detected (no manual toggle needed)
 * - TTS auto-picks Hindi or English voice based on response language
 * - Markdown stripped before speaking
 */
import { useRef, useState, useEffect, KeyboardEvent } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X, Send, Loader2, Volume2, VolumeX,
  Mic, MicOff, Trash2, Scale, User,
} from 'lucide-react'
import clsx from 'clsx'
import ReactMarkdown from 'react-markdown'
import toast from 'react-hot-toast'

import { sendAssistantMessage } from '@/lib/api'
import type { ChatMessage } from '@/lib/api'
import { useVoice } from '@/hooks/useVoice'

interface Props {
  onClose: () => void
}

const STARTERS: { text: string; lang: 'hi' | 'en' }[] = [
  { text: 'मेरे मौलिक अधिकार क्या हैं?',                  lang: 'hi' },
  { text: 'पुलिस गिरफ्तारी पर क्या करें?',               lang: 'hi' },
  { text: 'What is Article 21 of the Constitution?',       lang: 'en' },
  { text: 'How to file a consumer complaint?',             lang: 'en' },
  { text: 'किरायेदार को बेदखल करने की प्रक्रिया क्या है?', lang: 'hi' },
  { text: 'What are my rights if police arrests me?',      lang: 'en' },
]

export default function AssistantPanel({ onClose }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input,    setInput]    = useState('')
  const [loading,  setLoading]  = useState(false)
  const bottomRef               = useRef<HTMLDivElement>(null)
  const { listening, speaking, startListening, stopListening, speak, stopSpeaking } = useVoice()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const send = async (text?: string) => {
    const content = (text ?? input).trim()
    if (!content) return
    const userMsg: ChatMessage = { role: 'user', content }
    const updated = [...messages, userMsg]
    setMessages(updated)
    setInput('')
    setLoading(true)
    try {
      const resp = await sendAssistantMessage(updated)
      setMessages(prev => [...prev, { role: 'assistant', content: resp.reply }])
    } catch {
      toast.error('Assistant unavailable. Check backend.')
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'क्षमा करें, एक त्रुटि हुई। / Sorry, an error occurred.',
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  const handleVoice = () => {
    if (listening) { stopListening(); return }
    startListening((transcript) => {
      setInput(transcript)
      setTimeout(() => send(transcript), 150)
    })
  }

  const handleSpeak = (text: string) => {
    // speak() auto-detects Hindi vs English and strips Markdown
    if (speaking) { stopSpeaking(); return }
    speak(text)
  }

  return (
    <AnimatePresence>
      <motion.div
        key="assistant-panel"
        initial={{ opacity: 0, x: 40 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: 40 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className="fixed right-0 top-0 h-full w-full sm:w-[440px] z-50
                   flex flex-col card rounded-none sm:rounded-l-2xl shadow-2xl border-r-0"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 flex-shrink-0
                        border-b border-gray-200 dark:border-gray-800
                        bg-brand-50 dark:bg-brand-950/30">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-brand-600 flex items-center justify-center shadow-sm">
              <Scale className="w-4 h-4 text-white" strokeWidth={2.5} />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 font-serif">
                VakilAI
              </h3>
              <p className="text-xs text-brand-600 dark:text-brand-400">
                हिंदी / English · Auto-detected
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setMessages([])}
              className="btn-ghost text-xs py-1 px-2"
              title="Clear chat"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
            <button onClick={onClose} className="btn-ghost">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">

          {/* Welcome screen */}
          {messages.length === 0 && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
              <p className="text-center text-sm text-gray-500 dark:text-gray-400 mb-4">
                हिंदी या English में पूछें — भाषा अपने आप पहचानी जाएगी
                <br />
                <span className="text-xs text-gray-400 dark:text-gray-600">
                  Ask in Hindi or English — language auto-detected
                </span>
              </p>

              {/* Constitution quick ref */}
              <div className="card p-3 mb-4 border-brand-100 dark:border-brand-900/50">
                <p className="text-xs font-medium text-brand-700 dark:text-brand-400 mb-2">
                  मुख्य अनुच्छेद · Key Articles
                </p>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                  {[
                    ['अनु॰ 14', 'समानता'],
                    ['अनु॰ 19', 'स्वतंत्रता'],
                    ['अनु॰ 21', 'जीवन का अधिकार'],
                    ['अनु॰ 32', 'संवैधानिक उपाय'],
                  ].map(([a, l]) => (
                    <div key={a} className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                      <span className="font-mono font-medium text-brand-500">{a}</span>
                      <span>{l}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Starters */}
              <div className="flex flex-col gap-2">
                {STARTERS.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => send(s.text)}
                    className="text-left text-xs px-3 py-2 rounded-xl
                               border border-gray-200 dark:border-gray-700
                               text-gray-600 dark:text-gray-400
                               hover:border-brand-400 hover:text-brand-600
                               dark:hover:border-brand-500 dark:hover:text-brand-400
                               hover:bg-brand-50 dark:hover:bg-brand-950/30
                               transition-all bg-white dark:bg-gray-900"
                  >
                    {s.text}
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          {/* Chat messages */}
          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className={clsx('flex gap-2.5', msg.role === 'user' ? 'flex-row-reverse' : 'flex-row')}
            >
              <div className={clsx(
                'flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center',
                msg.role === 'user'
                  ? 'bg-brand-100 dark:bg-brand-900/40 text-brand-600 dark:text-brand-400'
                  : 'bg-brand-50 dark:bg-brand-950/40 text-brand-500',
              )}>
                {msg.role === 'user'
                  ? <User className="w-3.5 h-3.5" />
                  : <Scale className="w-3.5 h-3.5" />}
              </div>

              <div className={clsx(
                'group relative max-w-[84%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed',
                msg.role === 'user'
                  ? 'bg-brand-600 text-white rounded-tr-sm'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 rounded-tl-sm',
              )}>
                <ReactMarkdown className="prose prose-sm dark:prose-invert max-w-none">
                  {msg.content}
                </ReactMarkdown>

                {msg.role === 'assistant' && (
                  <button
                    onClick={() => handleSpeak(msg.content)}
                    className="absolute -bottom-1 -right-1 opacity-0 group-hover:opacity-100
                               transition-opacity p-1 rounded-full
                               bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700
                               text-gray-400 hover:text-brand-500 shadow-sm"
                    title={speaking ? 'रोकें / Stop' : 'सुनें / Listen'}
                  >
                    {speaking ? <VolumeX className="w-3 h-3" /> : <Volume2 className="w-3 h-3" />}
                  </button>
                )}
              </div>
            </motion.div>
          ))}

          {/* Typing dots */}
          {loading && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-2.5">
              <div className="w-7 h-7 rounded-full bg-brand-50 dark:bg-brand-950/40 flex items-center justify-center">
                <Scale className="w-3.5 h-3.5 text-brand-500" />
              </div>
              <div className="bg-gray-100 dark:bg-gray-800 rounded-2xl rounded-tl-sm px-4 py-3 flex gap-1 items-center">
                {[0, 1, 2].map(i => (
                  <motion.div
                    key={i}
                    className="w-1.5 h-1.5 rounded-full bg-gray-400 dark:bg-gray-500"
                    animate={{ y: [0, -4, 0] }}
                    transition={{ repeat: Infinity, duration: 0.8, delay: i * 0.15 }}
                  />
                ))}
              </div>
            </motion.div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input area */}
        <div className="border-t border-gray-200 dark:border-gray-800 p-3 flex-shrink-0">
          <p className="text-xs text-center text-gray-400 dark:text-gray-600 mb-2">
            यह कानूनी जानकारी है, औपचारिक सलाह नहीं · Information only, not legal advice
          </p>
          <div className="flex items-end gap-2">
            <div className="flex-1 relative">
              <textarea
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="हिंदी या English में पूछें… / Ask in Hindi or English…"
                rows={1}
                className="input-base py-2.5 text-sm resize-none max-h-32 overflow-y-auto pr-10"
              />
              <button
                onClick={handleVoice}
                className={clsx(
                  'absolute right-2.5 bottom-2.5 p-1 rounded transition-colors',
                  listening
                    ? 'text-red-500 animate-pulse-soft'
                    : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300',
                )}
                title={listening ? 'रोकें · Stop' : 'बोलें · Speak'}
              >
                {listening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
              </button>
            </div>
            <button
              onClick={() => send()}
              disabled={loading || !input.trim()}
              className="btn-primary p-2.5 flex-shrink-0"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </motion.div>

      <motion.div
        key="assistant-backdrop"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 bg-black/30 dark:bg-black/50 z-40 sm:hidden"
      />
    </AnimatePresence>
  )
}
