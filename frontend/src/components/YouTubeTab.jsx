import { MonitorPlay } from 'lucide-react'
import PatternSelector from './PatternSelector'
import usePersistedState from '../hooks/usePersistedState'

export default function YouTubeTab({ onAnalyze, onConfirm }) {
  const [url, setUrl] = usePersistedState('tab-youtube-url', '')
  const [pattern, setPattern] = usePersistedState('tab-youtube-pattern', 'create_micro_summary')

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">YouTube URL</label>
        <input
          type="text"
          placeholder="https://www.youtube.com/watch?v=..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-gray-100 focus:outline-none focus:ring-2 focus:ring-violet-500"
        />
      </div>
      <PatternSelector value={pattern} onChange={setPattern} onEnter={() => onAnalyze({ source: 'youtube', url, pattern })} onConfirm={(p) => onConfirm({ source: 'youtube', url, pattern: p })} storageKey="youtube" />
      <button
        onClick={() => onAnalyze({ source: 'youtube', url, pattern })}
        disabled={!url || !pattern}
        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-violet-600 hover:bg-violet-500 disabled:bg-gray-700 disabled:text-gray-500 rounded-lg font-medium transition"
      >
        <MonitorPlay size={18} /> Analyze YouTube Video
      </button>
    </div>
  )
}