import { useState, useEffect } from 'react'
import usePersistedState from '../hooks/usePersistedState'
import { MonitorPlay, Video, Upload, Globe } from 'lucide-react'
import YouTubeTab from '../components/YouTubeTab'
import RumbleTab from '../components/RumbleTab'
import FileUploadTab from '../components/FileUploadTab'
import WebScrapeTab from '../components/WebScrapeTab'
import AnalysisRunner from '../components/AnalysisRunner'
import { startAnalysis, startFileAnalysis, getModels, checkResult } from '../api/client'

const TABS = [
  { key: 'youtube', label: 'YouTube', icon: MonitorPlay },
  { key: 'rumble', label: 'Rumble', icon: Video },
  { key: 'file', label: 'File Upload', icon: Upload },
  { key: 'web', label: 'Web Scraping', icon: Globe },
]

export default function AnalysisPage() {
  const [activeTab, setActiveTab] = usePersistedState('analysis-tab', 'youtube')
  const [jobId, setJobId] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [model, setModel] = usePersistedState('analysis-model-v2', '')
  const [models, setModels] = useState([])
  const [checkMessage, setCheckMessage] = useState('')

  useEffect(() => {
    getModels().then((data) => {
      setModels(data.models || [])
      setModel((current) => current || data.default || '')
    }).catch((e) => console.error('Failed to load models:', e))
  }, [setModels, setModel])

  const handleAnalyze = async ({ source, url, pattern, formData }) => {
    setSubmitting(true)
    setError('')
    setJobId('')
    setCheckMessage('')
    const effectiveModel = model || undefined
    try {
      const payload = { source, pattern, model: effectiveModel }
      if (formData) {
        if (effectiveModel) formData.set('model', effectiveModel)
        const data = await startFileAnalysis(formData)
        setJobId(data.job_id)
      } else {
        const data = await startAnalysis({ ...payload, url })
        setJobId(data.job_id)
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleAutoCheck = async ({ source, url, pattern }) => {
    setError('')
    setCheckMessage('')
    setJobId('')
    const effectiveModel = model || undefined
    try {
      const data = await checkResult(source, url, pattern, effectiveModel)
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
      <h1 className="text-2xl font-bold mb-6">Analysis</h1>
      <div className="flex gap-2 mb-6 border-b border-gray-800 pb-px">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-t-lg text-sm font-medium transition ${
              activeTab === key
                ? 'bg-gray-800 text-white border-b-2 border-violet-500'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <Icon size={16} /> {label}
          </button>
        ))}
      </div>

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

      <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-6">
        {activeTab === 'youtube' && <YouTubeTab onAnalyze={handleAnalyze} onConfirm={handleAutoCheck} />}
        {activeTab === 'rumble' && <RumbleTab onAnalyze={handleAnalyze} onConfirm={handleAutoCheck} />}
        {activeTab === 'file' && <FileUploadTab onAnalyze={handleAnalyze} onConfirm={handleAutoCheck} />}
        {activeTab === 'web' && <WebScrapeTab onAnalyze={handleAnalyze} onConfirm={handleAutoCheck} />}

        {error && (
          <div className="mt-4 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm">
            {error}
          </div>
        )}
        {submitting && (
          <div className="mt-4 text-sm text-blue-400">Starting analysis...</div>
        )}
      </div>

      {checkMessage === 'not_found' && (
        <div className="mt-4 inline-block px-3 py-1.5 bg-red-900/50 border border-red-700 rounded text-xs text-red-300">
          Analysis has not been done before.
        </div>
      )}

      <AnalysisRunner jobId={jobId} />
    </div>
  )
}