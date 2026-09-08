import { useEffect, useState } from 'react'
import { getHistory } from '../api/client'
import { Clock, MonitorPlay, Video, Globe, Upload, Copy, ExternalLink, ChevronDown, ChevronUp, X } from 'lucide-react'
import MetadataDisplay from '../components/MetadataDisplay'

const SOURCE_ICONS = {
  youtube: MonitorPlay,
  rumble: Video,
  file: Upload,
  web: Globe,
}

const SOURCE_COLORS = {
  youtube: 'text-red-400',
  rumble: 'text-green-400',
  file: 'text-blue-400',
  web: 'text-purple-400',
}

export default function HistoryPage() {
  const [jobs, setJobs] = useState([])
  const [source, setSource] = useState('')
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState(null)
  const [showMetaId, setShowMetaId] = useState(null)

  useEffect(() => {
    setLoading(true)
    getHistory(source ? { source } : {})
      .then(setJobs)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [source])

  const handleCopy = (text) => navigator.clipboard.writeText(text)

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">History</h1>

      <div className="flex gap-2 mb-6">
        {['', 'youtube', 'rumble', 'file', 'web'].map((s) => (
          <button
            key={s}
            onClick={() => setSource(s)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
              source === s
                ? 'bg-violet-600 text-white'
                : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
            }`}
          >
            {s ? s.charAt(0).toUpperCase() + s.slice(1) : 'All'}
          </button>
        ))}
      </div>

      {loading && <div className="text-gray-400">Loading...</div>}

      {!loading && jobs.length === 0 && (
        <div className="text-gray-500 text-center py-12">No results yet. Run an analysis first.</div>
      )}

      <div className="space-y-3">
        {jobs.map((job) => {
          const Icon = SOURCE_ICONS[job.source] || Clock
          const color = SOURCE_COLORS[job.source] || 'text-gray-400'
          const expanded = expandedId === job.id

          return (
            <div key={job.id} className="bg-gray-900/50 border border-gray-800 rounded-lg overflow-hidden">
              <div
                onClick={() => setExpandedId(expanded ? null : job.id)}
                className="flex items-center gap-3 p-4 cursor-pointer hover:bg-gray-800/50 transition"
              >
                <Icon className={color} size={20} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium truncate">{job.url || job.file_path || '—'}</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded ${
                      job.status === 'completed' ? 'bg-green-900/50 text-green-300' :
                      job.status === 'failed' ? 'bg-red-900/50 text-red-300' :
                      'bg-yellow-900/50 text-yellow-300'
                    }`}>{job.status}</span>
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    Pattern: {job.pattern} · {new Date(job.created_at).toLocaleString()}
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  {job.metadata_json && (
                    <button
                      onClick={(e) => { e.stopPropagation(); setShowMetaId(job.id) }}
                      className="px-2 py-1 text-xs font-medium bg-violet-600/80 hover:bg-violet-600 text-white rounded transition"
                    >
                      Show Meta
                    </button>
                  )}
                  {expanded ? <ChevronUp size={18} className="text-gray-500" /> : <ChevronDown size={18} className="text-gray-500" />}
                </div>
              </div>

              {expanded && (
                <div className="px-4 pb-4 border-t border-gray-800 pt-3 space-y-3">
                  {job.result && (
                    <div>
                      <div className="text-xs font-medium text-gray-400 mb-1">Result</div>
                      <div className="bg-gray-800/50 rounded p-3 text-sm whitespace-pre-wrap max-h-60 overflow-y-auto">{job.result}</div>
                    </div>
                  )}
                  {job.transcript && (
                    <div>
                      <div className="text-xs font-medium text-gray-400 mb-1">Transcript</div>
                      <div className="bg-gray-800/30 rounded p-3 text-xs text-gray-400 whitespace-pre-wrap max-h-40 overflow-y-auto">{job.transcript}</div>
                    </div>
                  )}
                  {job.error && (
                    <div className="text-red-400 text-xs">{job.error}</div>
                  )}
                  <div className="flex gap-2">
                    {job.result && (
                      <button onClick={() => handleCopy(job.result)} className="flex items-center gap-1 text-xs px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded">
                        <Copy size={12} /> Copy Result
                      </button>
                    )}
                    {job.transcript && (
                      <button onClick={() => handleCopy(job.transcript)} className="flex items-center gap-1 text-xs px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded">
                        <Copy size={12} /> Copy Transcript
                      </button>
                    )}
                    {job.url && (
                      <a href={job.url} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-xs px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded">
                        <ExternalLink size={12} /> Open Original
                      </a>
                    )}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {showMetaId && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
          onClick={() => setShowMetaId(null)}
        >
          <div
            className="bg-gray-800 border border-gray-600 rounded-xl p-6 max-w-lg w-full mx-4 max-h-[80vh] overflow-y-auto shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-200">Analysis Metadata</h2>
              <button
                onClick={() => setShowMetaId(null)}
                className="p-1 hover:bg-gray-700 rounded transition"
              >
                <X size={18} className="text-gray-400" />
              </button>
            </div>
            <MetadataDisplay meta={jobs.find((j) => j.id === showMetaId)?.metadata_json} />
          </div>
        </div>
      )}
    </div>
  )
}