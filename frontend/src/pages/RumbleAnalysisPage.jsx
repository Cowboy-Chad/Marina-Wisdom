import { useState, useEffect } from 'react'
import { Video } from 'lucide-react'
import PatternSelector from '../components/PatternSelector'
import AnalysisRunner from '../components/AnalysisRunner'
import usePersistedState from '../hooks/usePersistedState'
import { startRumbleAnalysis, getModels, checkRumbleResult } from '../api/client'

export default function RumbleAnalysisPage() {
  const [url, setUrl] = usePersistedState('rumble-url', '')
  const [pattern, setPattern] = usePersistedState('rumble-pattern', 'create_micro_summary')
  const [model, setModel] = usePersistedState('analysis-model', '')
  const [models, setModels] = useState([])
  const [jobId, setJobId] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [checkMessage, setCheckMessage] = useState('')

  useEffect(() => {
    getModels().then((data) => {
      setModels(data.models || [])
      setModel((current) => current || data.default || '')
    }).catch((e) => console.error('Failed to load models:', e))
  }, [])

  const handleAnalyze = async () => {
    setSubmitting(true)
    setError('')
    setJobId('')
    setCheckMessage('')
    try {
      const data = await startRumbleAnalysis({ url, pattern, model: model || undefined })
      setJobId(data.job_id)
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleAutoCheck = async () => {
    setError('')
    setCheckMessage('')
    setJobId('')
    try {
      const data = await checkRumbleResult(url, pattern, model || undefined)
      if (data.found) {
        setJobId(data.job.id)
      } else {
        setCheckMessage('not_found')
      }
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Rumble Analysis</h1>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-300 mb-1">Model</label>
        <select
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-violet-500"
        >
          {models.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
        <p className="mt-1 text-xs text-gray-500">
          {model ? `Will analyze with: ${model}` : 'Using default model'}
        </p>
      </div>

      <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Rumble URL</label>
          <input
            type="text"
            placeholder="https://rumble.com/v..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-gray-100 focus:outline-none focus:ring-2 focus:ring-violet-500"
          />
        </div>

        <PatternSelector
          value={pattern}
          onChange={setPattern}
          onEnter={handleAnalyze}
          onConfirm={handleAutoCheck}
          storageKey="rumble"
        />

        <button
          onClick={handleAnalyze}
          disabled={!url || !pattern}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-violet-600 hover:bg-violet-500 disabled:bg-gray-700 disabled:text-gray-500 rounded-lg font-medium transition"
        >
          <Video size={18} /> Analyze Rumble Video
        </button>

        {checkMessage === 'not_found' && (
          <div className="inline-block px-3 py-1.5 bg-red-900/50 border border-red-700 rounded text-xs text-red-300">
            No prior analysis found for this video.
          </div>
        )}

        {error && (
          <div className="p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm">{error}</div>
        )}

        {submitting && (
          <div className="text-sm text-blue-400">Starting analysis...</div>
        )}
      </div>

      <AnalysisRunner jobId={jobId} />
    </div>
  )
}