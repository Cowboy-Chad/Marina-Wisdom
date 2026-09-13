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
        <ResultDisplay result={job.result} transcript={job.transcript} meta={job.metadata_json} />
      )}
      {job?.status === 'failed' && (
        <div className="p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300">
          {job.error || 'Analysis failed'}
        </div>
      )}
    </div>
  )
}

function ResultDisplay({ result, transcript, meta }) {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied] = useState(false)

  const metaLines = (meta ? [
    meta.title && `Title: ${meta.title}`,
    meta.webpage_url && `Title URL: ${meta.webpage_url}`,
    meta.channel && `Channel: ${meta.channel}`,
    meta.channel_url && `Channel URL: ${meta.channel_url}`,
    meta.view_count != null && `Views: ${meta.view_count.toLocaleString()}`,
    meta.duration_display && `Video Length: ${meta.duration_display}`,
    meta.upload_date_display && `Published: ${meta.upload_date_display}`,
    meta.fabric_pattern && `Fabric Pattern: ${meta.fabric_pattern}`,
    meta.model && `Model: ${meta.model}`,
    meta.processing_time_seconds != null && `Processing Time: ${meta.processing_time_seconds}s`,
    meta.transcript_source && `Transcript Source: ${meta.transcript_source}`,
    meta.input_tokens != null && `Tokens: ${meta.input_tokens} in / ${meta.output_tokens} out (via tiktoken)`,
    meta.estimated_cost != null && `Pattern Cost: $${Number(meta.estimated_cost).toFixed(4)}`,
    meta.pricing_source && `Pricing Source: ${meta.pricing_source}`,
  ].filter(Boolean) : [])

  const fullResult = metaLines.length > 0 ? metaLines.join('\n') + '\n\n' + result : result

  const handleCopy = () => {
    navigator.clipboard.writeText(fullResult)
    setCopied(true)
    setTimeout(() => setCopied(false), 5000)
  }

  const handleExportPDF = async () => {
    try {
      const { jsPDF } = await import('jspdf')
      const doc = new jsPDF()
      let y = 20
      doc.setFontSize(10)
      const lines = doc.splitTextToSize(fullResult, 180)
      doc.text(lines, 15, y)
      const filename = meta?.title
        ? `${meta.title.replace(/[/\\?%*:|"<>.]/g, ' - ').replace(/\s+/g, ' ').trim().slice(0, 100)}.pdf`
        : 'analysis-result.pdf'
      doc.save(filename)
    } catch (e) {
      console.error('PDF generation failed:', e)
    }
  }

  return (
    <div className="space-y-3">
      <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4 whitespace-pre-wrap text-sm leading-relaxed">
        {fullResult}
      </div>
      <div className="flex gap-2">
        <button onClick={handleCopy} className={`px-3 py-1.5 rounded text-sm ${copied ? 'bg-green-600 hover:bg-green-500' : 'bg-gray-700 hover:bg-gray-600'}`}>
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