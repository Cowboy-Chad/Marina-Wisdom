import { Cpu, DollarSign, Timer, FileText } from 'lucide-react'

export default function MetadataDisplay({ meta }) {
  if (!meta || Object.keys(meta).length === 0) return null

  const rows = []

  if (meta.title) rows.push(['Title', meta.title])
  if (meta.webpage_url) rows.push(['Video URL', meta.webpage_url, meta.webpage_url])
  if (meta.channel) {
    const subs = meta.channel_subscribers
      ? ` (${meta.channel_subscribers.toLocaleString()} subscribers)`
      : ''
    rows.push(['Channel', meta.channel + subs])
  }
  if (meta.channel_url) rows.push(['Channel URL', meta.channel_url, meta.channel_url])
  if (meta.upload_date_display) {
    const rel = meta.upload_date_relative ? ` (${meta.upload_date_relative})` : ''
    rows.push(['Published', `${meta.upload_date_display} ${rel}`])
  }
  if (meta.duration_display) rows.push(['Duration', meta.duration_display])
  if (meta.view_count != null) rows.push(['Views', meta.view_count.toLocaleString()])
  if (meta.fabric_pattern) rows.push(['Fabric Pattern', meta.fabric_pattern])
  if (meta.model) rows.push(['Model', meta.model])
  if (meta.processing_time_seconds != null) {
    rows.push(['Processing Time', `${meta.processing_time_seconds}s`])
  }
  if (meta.transcript_source) rows.push(['Transcript Source', meta.transcript_source])
  if (meta.input_tokens != null) {
    rows.push([
      'Tokens',
      `${meta.input_tokens} in / ${meta.output_tokens} out (via tiktoken)`,
    ])
  }
  if (meta.estimated_cost != null) {
    rows.push(['Pattern Cost', `$${meta.estimated_cost.toFixed(4)}`])
  }
  if (meta.pricing_source) rows.push(['Pricing Source', meta.pricing_source])

  return (
    <div className="bg-gray-800/30 border border-gray-700 rounded-lg p-4 text-xs text-gray-400">
      <div className="flex items-center gap-2 text-gray-300 text-xs font-medium mb-2">
        <FileText size={14} /> Analysis Metadata
      </div>
      <div className="space-y-1">
        {rows.map(([label, value, href]) => (
          <div key={label} className="flex gap-2">
            <span className="w-32 shrink-0 text-gray-500">{label}</span>
            {href ? (
              <a
                href={href}
                target="_blank"
                rel="noreferrer"
                className="text-blue-400 hover:text-blue-300 truncate"
              >
                {value}
              </a>
            ) : (
              <span>{value}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}