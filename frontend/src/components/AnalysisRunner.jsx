import { useEffect, useState } from 'react'
import { pollJob } from '../api/client'
import { Loader2 } from 'lucide-react'

export default function AnalysisRunner({ jobId }) {
  const [job, setJob] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!jobId) return
    setJob(null)
    setError('')
    let cancelled = false

    const poll = async () => {
      while (!cancelled) {
        try {
          const data = await pollJob(jobId)
          if (cancelled) break
          setJob(data)
          if (data.status === 'completed' || data.status === 'failed') break
        } catch (e) {
          if (!cancelled) setError(e.message)
          break
        }
        await new Promise((r) => setTimeout(r, 2000))
      }
    }
    poll()
    return () => { cancelled = true }
  }, [jobId])

  if (!jobId) return null
  if (error) return <div className="mt-4 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300">{error}</div>

  const statusColors = {
    pending: 'text-yellow-400',
    running: 'text-blue-400',
    completed: 'text-green-400',
    failed: 'text-red-400',
  }

  return (
    <div className="mt-6">
      <div className="flex items-center gap-2 mb-3">
        <span className={`text-sm font-medium ${statusColors[job?.status] || 'text-gray-400'}`}>
          {job?.status || 'pending'}
        </span>
        {(job?.status === 'pending' || job?.status === 'running') && (
          <Loader2 className="animate-spin text-blue-400" size={16} />
        )}
      </div>
      {job?.status === 'completed' && job?.result && (
        <ResultDisplay result={job.result} transcript={job.transcript} />
      )}
      {job?.status === 'failed' && (
        <div className="p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300">
          {job.error || 'Analysis failed'}
        </div>
      )}
    </div>
  )
}

function ResultDisplay({ result, transcript }) {
  const [expanded, setExpanded] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(result)
  }

  const handleExportPDF = async () => {
    const { jsPDF } = await import('jspdf')
    const doc = new jsPDF()
    doc.setFontSize(10)
    const lines = doc.splitTextToSize(result, 180)
    doc.text(lines, 15, 20)
    doc.save('analysis-result.pdf')
  }

  return (
    <div className="space-y-3">
      <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4 whitespace-pre-wrap text-sm leading-relaxed">
        {result}
      </div>
      <div className="flex gap-2">
        <button onClick={handleCopy} className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-sm">
          Copy Result
        </button>
        <button onClick={handleExportPDF} className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-sm">
          Export PDF
        </button>
        <button
          onClick={() => setExpanded(!expanded)}
          className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-sm"
        >
          {expanded ? 'Hide' : 'Show'} Transcript
        </button>
      </div>
      {expanded && transcript && (
        <div className="bg-gray-800/30 border border-gray-700 rounded-lg p-4 whitespace-pre-wrap text-xs text-gray-400 max-h-60 overflow-y-auto">
          {transcript}
        </div>
      )}
    </div>
  )
}