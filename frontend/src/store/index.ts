import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { CaseSummary, ChatMessage } from '@/lib/api'

// ── Search slice ───────────────────────────────────────────────────────────────

interface SearchState {
  query:           string
  results:         CaseSummary[]
  expandedQueries: string[]
  loading:         boolean
  error:           string | null
  searched:        boolean
  setQuery:        (q: string) => void
  setResults:      (r: CaseSummary[], expanded: string[]) => void
  setLoading:      (v: boolean) => void
  setError:        (e: string | null) => void
  reset:           () => void
}

export const useSearchStore = create<SearchState>()((set) => ({
  query:           '',
  results:         [],
  expandedQueries: [],
  loading:         false,
  error:           null,
  searched:        false,
  setQuery:        (q)         => set({ query: q }),
  setResults:      (r, expanded) => set({ results: r, expandedQueries: expanded, searched: true }),
  setLoading:      (v)         => set({ loading: v }),
  setError:        (e)         => set({ error: e }),
  reset:           ()          => set({ query: '', results: [], expandedQueries: [], error: null, searched: false }),
}))

// ── Active case slice ──────────────────────────────────────────────────────────

interface ActiveCaseState {
  activeCase:     CaseSummary | null
  chatHistory:    Record<string, ChatMessage[]>
  chatLoading:    boolean
  setActiveCase:  (c: CaseSummary | null) => void
  appendMessage:  (pdfIndex: string, msg: ChatMessage) => void
  clearChat:      (pdfIndex: string) => void
  setChatLoading: (v: boolean) => void
}

export const useActiveCaseStore = create<ActiveCaseState>()((set) => ({
  activeCase:     null,
  chatHistory:    {},
  chatLoading:    false,
  setActiveCase:  (c)         => set({ activeCase: c }),
  appendMessage:  (pid, msg)  => set((s) => ({
    chatHistory: { ...s.chatHistory, [pid]: [...(s.chatHistory[pid] ?? []), msg] },
  })),
  clearChat:      (pid)       => set((s) => ({ chatHistory: { ...s.chatHistory, [pid]: [] } })),
  setChatLoading: (v)         => set({ chatLoading: v }),
}))

// ── Theme slice ────────────────────────────────────────────────────────────────

interface ThemeState {
  dark:       boolean
  toggleDark: () => void
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      dark: window.matchMedia('(prefers-color-scheme: dark)').matches,
      toggleDark: () => {
        const next = !get().dark
        document.documentElement.classList.toggle('dark', next)
        set({ dark: next })
      },
    }),
    { name: 'theme' },
  ),
)
