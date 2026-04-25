import { useRef, useState, useEffect, KeyboardEvent } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Send, Loader2, Volume2, VolumeX, Mic, MicOff, Trash2, Bot, User } from 'lucide-react'
import clsx from 'clsx'
import ReactMarkdown from 'react-markdown'
import toast from 'react-hot-toast'

import { useActiveCaseStore } from '@/store'
import { sendChatMessage } from '@/lib/api'
import type { ChatMessage } from '@/lib/api'
import { useVoice } from '@/hooks/useVoice'
import { getDownloadUrl } from '@/lib/api'

export default function ChatPanel() {
  const {
    activeCase,
    setActiveCase,
    chatHistory,
    appendMessage,
    clearChat,
    chatLoading,
    setChatLoading,
  } = useActiveCaseStore()

  const [input,      setInput]      = useState('')
  const bottomRef                   = useRef<HTMLDivElement>(null)
  const inputRef                    = useRef<HTMLTextAreaElement>(null)
  const { listening, speaking, startListening, stopListening, speak, stopSpeaking } = useVoice()

  const pdfIndex = activeCase?.pdf_index ?? ''
  const messages: ChatMessage[] = chatHistory[pdfIndex] ?? []
  const messageCount = messages.length

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messageCount, chatLoading])

  if (!activeCase) return null

  const caseName = pdfIndex.replace(/\.pdf$/i, '')

  const send = async (text?: string) => {
    const content = (text ?? input).trim()
    if (!content) return

    const userMsg: ChatMessage = { role: 'user', content }
    appendMessage(pdfIndex, userMsg)
    setInput('')
    setChatLoading(true)

    try {
      const allMsgs = [...messages, userMsg]
      const resp    = await sendChatMessage(pdfIndex, allMsgs)
      appendMessage(pdfIndex, { role: 'assistant', content: resp.reply })
    } catch {
      toast.error('Chat failed. Check backend.')
      appendMessage(pdfIndex, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
      })
    } finally {
      setChatLoading(false)
    }
  }

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  const handleVoice = () => {
    if (listening) { stopListening(); return }
    startListening((transcript) => {
      setInput(transcript)
      setTimeout(() => send(transcript), 200)
    })
  }

  const handleSpeak = (text: string) => {
    if (speaking) { stopSpeaking(); return }
    speak(text)
  }

  return (
    <AnimatePresence>
      <motion.div
        key="chat-panel"
        initial={{ opacity: 0, x: 40 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: 40 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className="fixed right-0 top-0 h-full w-full sm:w-[420px] z-50
                   flex flex-col card rounded-none sm:rounded-l-2xl shadow-2xl border-r-0"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3
                        border-b border-gray-200 dark:border-gray-800 flex-shrink-0">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse-soft" />
              <span className="text-xs text-gray-500 dark:text-gray-400">Chatting with</span>
            </div>
            <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 font-mono truncate mt-0.5">
              {caseName}
            </h3>
          </div>
          <div className="flex items-center gap-1 flex-shrink-0">
            {activeCase.available && (
              <a
                href={getDownloadUrl(pdfIndex)}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-ghost text-xs py-1 px-2"
                title="Download PDF"
              >
                PDF
              </a>
            )}
            <button
              onClick={() => clearChat(pdfIndex)}
              className="btn-ghost text-xs py-1 px-2"
              title="Clear chat"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setActiveCase(null)}
              className="btn-ghost"
              title="Close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {/* Welcome message */}
          {messages.length === 0 && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center py-8"
            >
              <div className="w-12 h-12 rounded-2xl bg-brand-50 dark:bg-brand-950/40
                              flex items-center justify-center mx-auto mb-3">
                <Bot className="w-6 h-6 text-brand-500" />
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 max-w-xs mx-auto leading-relaxed">
                Ask me anything about <strong className="font-medium text-gray-800 dark:text-gray-200">{caseName}</strong>.
                I can explain the judgment, legal principles, and how it relates to your scenario.
              </p>
              <div className="mt-4 flex flex-col gap-2">
                {[
                  'What is the main judgment?',
                  'What legal principles apply?',
                  'How does this relate to my case?',
                ].map(q => (
                  <button
                    key={q}
                    onClick={() => send(q)}
                    className="mx-auto text-xs px-3 py-1.5 rounded-full border border-gray-200
                               dark:border-gray-700 text-gray-600 dark:text-gray-400
                               hover:border-brand-400 hover:text-brand-600
                               dark:hover:border-brand-500 dark:hover:text-brand-400
                               transition-all bg-white dark:bg-gray-900"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          {/* Message bubbles */}
          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 }}
              className={clsx('flex gap-2.5', msg.role === 'user' ? 'flex-row-reverse' : 'flex-row')}
            >
              {/* Avatar */}
              <div className={clsx(
                'flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs',
                msg.role === 'user'
                  ? 'bg-brand-100 dark:bg-brand-900/40 text-brand-600 dark:text-brand-400'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400',
              )}>
                {msg.role === 'user' ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
              </div>

              {/* Bubble */}
              <div className={clsx(
                'group relative max-w-[82%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed',
                msg.role === 'user'
                  ? 'bg-brand-600 text-white rounded-tr-sm'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 rounded-tl-sm',
              )}>
                <ReactMarkdown className="prose prose-sm dark:prose-invert max-w-none">
                  {msg.content}
                </ReactMarkdown>

                {/* TTS button on assistant messages */}
                {msg.role === 'assistant' && (
                  <button
                    onClick={() => handleSpeak(msg.content)}
                    className="absolute -bottom-1 -right-1 opacity-0 group-hover:opacity-100
                               transition-opacity p-1 rounded-full
                               bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700
                               text-gray-400 hover:text-brand-500 shadow-sm"
                    title={speaking ? 'Stop' : 'Read aloud'}
                  >
                    {speaking
                      ? <VolumeX className="w-3 h-3" />
                      : <Volume2 className="w-3 h-3" />}
                  </button>
                )}
              </div>
            </motion.div>
          ))}

          {/* Typing indicator */}
          {chatLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex gap-2.5"
            >
              <div className="w-7 h-7 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
                <Bot className="w-3.5 h-3.5 text-gray-400" />
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

        {/* Input */}
        <div className="border-t border-gray-200 dark:border-gray-800 p-3 flex-shrink-0">
          <div className="flex items-end gap-2">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Ask about this case… (Enter to send)"
                rows={1}
                className="input-base py-2.5 text-sm resize-none max-h-32 overflow-y-auto pr-10"
              />
              {/* Voice in input */}
              <button
                onClick={handleVoice}
                className={clsx(
                  'absolute right-2.5 bottom-2.5 p-1 rounded transition-colors',
                  listening
                    ? 'text-red-500 animate-pulse-soft'
                    : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300',
                )}
              >
                {listening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
              </button>
            </div>
            <button
              onClick={() => send()}
              disabled={chatLoading || !input.trim()}
              className="btn-primary p-2.5 flex-shrink-0"
            >
              {chatLoading
                ? <Loader2 className="w-4 h-4 animate-spin" />
                : <Send className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </motion.div>

      {/* Backdrop */}
      <motion.div
        key="backdrop"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={() => setActiveCase(null)}
        className="fixed inset-0 bg-black/30 dark:bg-black/50 z-40 sm:hidden"
      />
    </AnimatePresence>
  )
}
