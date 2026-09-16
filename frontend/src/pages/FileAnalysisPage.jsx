import { useState, useRef, useEffect } from 'react'
import { Upload } from 'lucide-react'
import PatternSelector from '../components/PatternSelector'
import AnalysisRunner from '../components/AnalysisRunner'
import usePersistedState from '../hooks/usePersistedState'
import { startFileAnalysis, getModels } from '../api/client'

export default function FileAnalysisPage() {
  const [file, setFile] = useState(null)
  const [pattern, setPattern] = usePersistedState('file-pattern', 'create_micro_summary')
  const [model, setModel] = usePersistedState('analysis-model', '')
  const [models, setModels] = useState([])
  const [jobId, setJobId] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef(null)

  useEffect(() => {
    getModels().then((data) => {
      setModels(data.models || [])
      setModel((current) => current || data.default || '')
    }).catch((e) => console.error('Failed to load models:', e))
  }, [])

  const handleSubmit = async () => {
    if (!file || !pattern) return
    setSubmitting(true)
    setError('')
    setJobId('')
    const formData = new FormData()
    formData.append('file', file)
    formData.append('pattern', pattern)
    if (model) formData.append('model', model)
    try {
      const data = await startFileAnalysis(formData)
      setJobId(data.job_id)
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">File Upload</h1>

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
        <div
          onClick={() => inputRef.current?.click()}
          className="border-2 border-dashed border-gray-600 rounded-lg p-8 text-center cursor-pointer hover:border-violet-500 transition"
        >
          <Upload className="mx-auto mb-2 text-gray-400" size={24} />
          <p className="text-sm text-gray-400">
            {file ? file.name : 'Click to upload audio/video file'}
          </p>
          <input
            ref={inputRef}
            type="file"
            accept="audio/*,video/*"
            className="hidden"
            onChange={(e) => setFile(e.target.files[0])}
          />
        </div>

        <PatternSelector
          value={pattern}
          onChange={setPattern}
          onEnter={handleSubmit}
          storageKey="file"
        />

        <button
          onClick={handleSubmit}
          disabled={!file || !pattern}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-violet-600 hover:bg-violet-500 disabled:bg-gray-700 disabled:text-gray-500 rounded-lg font-medium transition"
        >
          <Upload size={18} /> Upload & Analyze
        </button>

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