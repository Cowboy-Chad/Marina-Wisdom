import { useState } from 'react'
import { MonitorPlay, Video, Upload, Globe } from 'lucide-react'
import YouTubeTab from '../components/YouTubeTab'
import RumbleTab from '../components/RumbleTab'
import FileUploadTab from '../components/FileUploadTab'
import WebScrapeTab from '../components/WebScrapeTab'
import AnalysisRunner from '../components/AnalysisRunner'
import { startAnalysis, startFileAnalysis } from '../api/client'

const TABS = [
  { key: 'youtube', label: 'YouTube', icon: MonitorPlay },
  { key: 'rumble', label: 'Rumble', icon: Video },
  { key: 'file', label: 'File Upload', icon: Upload },
  { key: 'web', label: 'Web Scraping', icon: Globe },
]

export default function AnalysisPage() {
  const [activeTab, setActiveTab] = useState('youtube')
  const [jobId, setJobId] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const handleAnalyze = async ({ source, url, pattern, formData }) => {
    setSubmitting(true)
    setError('')
    setJobId('')
    try {
      const data = formData
        ? await startFileAnalysis(formData)
        : await startAnalysis({ source, url, pattern })
      setJobId(data.job_id)
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
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

      <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-6">
        {activeTab === 'youtube' && <YouTubeTab onAnalyze={handleAnalyze} />}
        {activeTab === 'rumble' && <RumbleTab onAnalyze={handleAnalyze} />}
        {activeTab === 'file' && <FileUploadTab onAnalyze={handleAnalyze} />}
        {activeTab === 'web' && <WebScrapeTab onAnalyze={handleAnalyze} />}

        {error && (
          <div className="mt-4 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm">
            {error}
          </div>
        )}
        {submitting && (
          <div className="mt-4 text-sm text-blue-400">Starting analysis...</div>
        )}
      </div>

      <AnalysisRunner jobId={jobId} />
    </div>
  )
}