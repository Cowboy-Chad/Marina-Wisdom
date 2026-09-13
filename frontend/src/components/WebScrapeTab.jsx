import { Globe } from 'lucide-react'
import PatternSelector from './PatternSelector'
import usePersistedState from '../hooks/usePersistedState'

export default function WebScrapeTab({ onAnalyze, onConfirm }) {
  const [url, setUrl] = usePersistedState('tab-web-url', '')
  const [pattern, setPattern] = usePersistedState('tab-web-pattern', 'analyze_claims')

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">Web URL</label>
        <input
          type="text"
          placeholder="https://example.com/article"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-gray-100 focus:outline-none focus:ring-2 focus:ring-violet-500"
        />
      </div>
      <PatternSelector value={pattern} onChange={setPattern} onEnter={() => onAnalyze({ source: 'web', url, pattern })} onConfirm={(p) => onConfirm({ source: 'web', url, pattern: p })} storageKey="web" />
      <button
        onClick={() => onAnalyze({ source: 'web', url, pattern })}
        disabled={!url || !pattern}
        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-violet-600 hover:bg-violet-500 disabled:bg-gray-700 disabled:text-gray-500 rounded-lg font-medium transition"
      >
        <Globe size={18} /> Scrape & Analyze
      </button>
    </div>
  )
}