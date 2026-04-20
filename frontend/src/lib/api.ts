/**
 * lib/api.ts
 * Typed axios API client — mirrors backend Pydantic schemas exactly.
 */

import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120_000,
})

// ── Types ──────────────────────────────────────────────────────────────────────

export interface CaseSummary {
  pdf_index:       string
  relevance_score: number
  confidence:      string   // "High" | "Medium" | "Low"
  summary:         string
  snippet:         string
  available:       boolean
  chunk_hits:      number   // how many chunks matched
}

export interface SearchResponse {
  query:                      string
  expanded_queries:           string[]   // original + Groq expansions used
  results:                    CaseSummary[]
  total_candidates_evaluated: number
}

export interface CasePreviewResponse {
  pdf_index:    string
  text_preview: string
  available:    boolean
}

export interface ChatMessage {
  role:    'user' | 'assistant'
  content: string
}

export interface ChatResponse {
  reply:     string
  pdf_index: string
}

export interface AssistantResponse {
  reply: string
}

export interface VoiceInfo {
  short_name:    string
  friendly_name: string
  locale:        string
  gender:        string
}

// ── Search ─────────────────────────────────────────────────────────────────────

export const searchCases = async (
  query: string,
  top_k = 5,
): Promise<SearchResponse> => {
  const { data } = await api.post<SearchResponse>('/search', { query, top_k })
  return data
}

// ── Cases ──────────────────────────────────────────────────────────────────────

export const getCasePreview = async (pdfIndex: string): Promise<CasePreviewResponse> => {
  const { data } = await api.get<CasePreviewResponse>(
    `/cases/${encodeURIComponent(pdfIndex)}/preview`,
  )
  return data
}

export const getDownloadUrl = (pdfIndex: string): string =>
  `/api/cases/${encodeURIComponent(pdfIndex)}/download`

// ── Chat ───────────────────────────────────────────────────────────────────────

export const sendChatMessage = async (
  pdfIndex: string,
  messages: ChatMessage[],
): Promise<ChatResponse> => {
  const { data } = await api.post<ChatResponse>('/chat', {
    pdf_index: pdfIndex,
    messages,
  })
  return data
}

// ── Assistant ─────────────────────────────────────────────────────────────────

export const sendAssistantMessage = async (
  messages: ChatMessage[],
): Promise<AssistantResponse> => {
  const { data } = await api.post<AssistantResponse>('/assistant', { messages })
  return data
}

// ── Voice ──────────────────────────────────────────────────────────────────────

export const synthesizeSpeech = async (
  text: string,
  voice?: string,
): Promise<Blob> => {
  const { data } = await api.post(
    '/voice/tts',
    { text, voice },
    { responseType: 'blob' },
  )
  return data as Blob
}

export const getVoices = async (): Promise<VoiceInfo[]> => {
  const { data } = await api.get<{ voices: VoiceInfo[] }>('/voice/voices')
  return data.voices
}

export default api

// ── PDF upload search ──────────────────────────────────────────────────────────

export const searchFromPdf = async (file: File): Promise<SearchResponse> => {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<SearchResponse>('/upload/pdf', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180_000,  // PDF extraction + search can take longer
  })
  return data
}
