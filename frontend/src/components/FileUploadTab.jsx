import { useState, useRef } from 'react'
import { Upload } from 'lucide-react'
import PatternSelector from './PatternSelector'
import usePersistedState from '../hooks/usePersistedState'

export default function FileUploadTab({ onAnalyze }) {
  const [file, setFile] = useState(null)
  const [pattern, setPattern] = usePersistedState('tab-file-pattern', 'create_micro_summary')
  const inputRef = useRef(null)

  const handleSubmit = () => {
    if (!file || !pattern) return
    const formData = new FormData()
    formData.append('file', file)
    formData.append('pattern', pattern)
    onAnalyze({ source: 'file', file: file.name, pattern, formData })
  }

  return (
    <div className="space-y-4">
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
      <PatternSelector value={pattern} onChange={setPattern} />
      <button
        onClick={handleSubmit}
        disabled={!file || !pattern}
        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-violet-600 hover:bg-violet-500 disabled:bg-gray-700 disabled:text-gray-500 rounded-lg font-medium transition"
      >
        <Upload size={18} /> Upload & Analyze
      </button>
    </div>
  )
}