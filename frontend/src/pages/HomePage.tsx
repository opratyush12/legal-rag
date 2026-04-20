import { useSearchStore } from '@/store'
import Hero from '@/components/search/Hero'
import SearchBar from '@/components/search/SearchBar'
import ResultsList from '@/components/cases/ResultsList'

export default function HomePage() {
  const { searched } = useSearchStore()

  return (
    <div className="animate-fade-in">
      {/* Show full hero only before first search */}
      {!searched && <Hero />}

      {/* Compact header after search */}
      {searched && (
        <div className="flex items-center gap-3 mb-6">
          <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center">
            <span className="text-white text-xs font-bold font-serif">L</span>
          </div>
          <span className="font-serif font-semibold text-lg text-gray-900 dark:text-white">
            Lex<span className="text-brand-500">Search</span>
          </span>
        </div>
      )}

      <SearchBar compact={searched} />
      <ResultsList />
    </div>
  )
}
