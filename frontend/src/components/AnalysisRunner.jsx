import { useEffect, useState } from 'react'
import { pollJob } from '../api/client'
import { Loader2 } from 'lucide-react'
import MetadataDisplay from './MetadataDisplay'

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
      {job?.metadata_json && <MetadataDisplay meta={job.metadata_json} />}

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

  const buildHeader = () => {
    if (!meta) return { text: '', rows: [] }
    const m = meta
    const rows = []
    if (m.title) {
      rows.push({ label: 'Title', value: m.title })
      if (m.webpage_url) rows.push({ label: 'Title URL', value: m.webpage_url, href: m.webpage_url })
    }
    if (m.channel) {
      const subs = m.channel_subscribers ? ` (${m.channel_subscribers.toLocaleString()} subscribers)` : ''
      rows.push({ label: 'Channel', value: m.channel + subs })
      if (m.channel_url) rows.push({ label: 'Channel URL', value: m.channel_url, href: m.channel_url })
    }
    if (m.view_count != null) rows.push({ label: 'Views', value: m.view_count.toLocaleString() })
    if (m.duration_display) rows.push({ label: 'Video Length', value: m.duration_display })
    if (m.upload_date_display) {
      const rel = m.upload_date_relative ? ` (${m.upload_date_relative})` : ''
      rows.push({ label: 'Published', value: `${m.upload_date_display}${rel}` })
    }
    if (m.fabric_pattern) rows.push({ label: 'Pattern', value: m.fabric_pattern })
    if (m.estimated_cost != null) rows.push({ label: 'Pattern Cost', value: `$${Number(m.estimated_cost).toFixed(4)}` })
    const text = rows.map(r => `${r.label}: ${r.value}`).join('\n')
    return { text: text ? text + '\n\n' : '', rows }
  }

  const header = buildHeader()
  const fullResult = header.text + result

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
        {header.rows.length > 0 && (
          <div className="mb-3 pb-3 border-b border-gray-700 text-xs space-y-0.5">
            {header.rows.map((r, i) => (
              <div key={i} className="flex gap-2">
                <span className="w-24 shrink-0 text-gray-500">{r.label}</span>
                {r.href ? (
                  <a href={r.href} target="_blank" rel="noreferrer" className="text-blue-400 hover:text-blue-300 truncate">{r.value}</a>
                ) : (
                  <span>{r.value}</span>
                )}
              </div>
            ))}
          </div>
        )}
        {result}
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