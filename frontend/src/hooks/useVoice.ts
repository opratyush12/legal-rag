/**
 * hooks/useVoice.ts
 *
 * STT — Web Speech API (browser-native, free)
 *   Detects Hindi or English automatically based on what the user says.
 *   Primary: hi-IN, fallback: en-IN
 *
 * TTS — edge-tts via /api/voice/tts
 *   Auto-detects language of the text:
 *     - Contains Hindi (Devanagari) chars → hi-IN-SwaraNeural
 *     - English text → en-IN-NeerjaNeural (Indian accent)
 *   Strips all Markdown before speaking so "**bold**" is never read aloud.
 */

import { useCallback, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { synthesizeSpeech } from '@/lib/api'
import { stripMarkdownForSpeech } from '@/lib/textUtils'

declare global {
  interface Window {
    SpeechRecognition:       typeof SpeechRecognition | undefined
    webkitSpeechRecognition: typeof SpeechRecognition | undefined
  }
}

/** Returns true if text contains Devanagari characters (Hindi). */
function isHindi(text: string): boolean {
  return /[\u0900-\u097F]/.test(text)
}

/** Pick the right TTS voice based on text language. */
function voiceForText(text: string): string {
  return isHindi(text) ? 'hi-IN-SwaraNeural' : 'en-IN-NeerjaNeural'
}

export function useVoice() {
  const [listening,  setListening]  = useState(false)
  const [speaking,   setSpeaking]   = useState(false)
  const recognitionRef              = useRef<SpeechRecognition | null>(null)
  const audioRef                    = useRef<HTMLAudioElement | null>(null)

  // ── STT ────────────────────────────────────────────────────────────────────

  const startListening = useCallback(
    (onResult: (transcript: string) => void, forceLang?: string) => {
      const SR = window.SpeechRecognition ?? window.webkitSpeechRecognition
      if (!SR) {
        toast.error('Speech not supported. Please use Chrome or Edge.')
        return
      }

      const recognition           = new SR()
      recognition.lang            = forceLang ?? 'hi-IN'
      recognition.continuous      = false
      recognition.interimResults  = false
      recognition.maxAlternatives = 1

      recognition.onresult = (e: SpeechRecognitionEvent) => {
        const transcript = e.results[0][0].transcript
        onResult(transcript)
        setListening(false)
      }

      recognition.onerror = (e: SpeechRecognitionErrorEvent) => {
        if ((e.error === 'language-not-supported' || e.error === 'no-speech') && !forceLang) {
          // Retry once with Indian English
          startListening(onResult, 'en-IN')
          return
        }
        if (e.error === 'not-allowed') {
          toast.error('Microphone access denied. Please allow it in browser settings.')
        } else if (e.error !== 'no-speech') {
          toast.error('Voice input failed. Try typing instead.')
        }
        setListening(false)
      }

      recognition.onend = () => setListening(false)
      recognition.start()
      recognitionRef.current = recognition
      setListening(true)
    },
    [],
  )

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop()
    setListening(false)
  }, [])

  // ── TTS ────────────────────────────────────────────────────────────────────

  const speak = useCallback(
    async (rawText: string, voiceOverride?: string) => {
      // Toggle off if already speaking
      if (speaking) {
        audioRef.current?.pause()
        setSpeaking(false)
        return
      }

      // 1. Strip all Markdown so "**Article 21**" becomes "Article 21"
      const cleanText = stripMarkdownForSpeech(rawText)
      if (!cleanText) return

      // 2. Auto-pick voice based on language unless caller overrides
      const voice = voiceOverride ?? voiceForText(cleanText)

      try {
        setSpeaking(true)
        const blob  = await synthesizeSpeech(cleanText.slice(0, 2500), voice)
        const url   = URL.createObjectURL(blob)
        const audio = new Audio(url)
        audioRef.current = audio

        audio.onended = () => {
          setSpeaking(false)
          URL.revokeObjectURL(url)
        }
        audio.onerror = () => {
          setSpeaking(false)
          toast.error('Audio playback failed.')
        }
        await audio.play()
      } catch {
        setSpeaking(false)
        toast.error('Voice unavailable. Check backend.')
      }
    },
    [speaking],
  )

  const stopSpeaking = useCallback(() => {
    audioRef.current?.pause()
    setSpeaking(false)
  }, [])

  return { listening, speaking, startListening, stopListening, speak, stopSpeaking }
}
