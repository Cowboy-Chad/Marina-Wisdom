import { useEffect, useState } from 'react'
import { getPatterns } from '../api/client'

export default function PatternSelector({ value, onChange }) {
  const [patterns, setPatterns] = useState([])
  const [search, setSearch] = useState('')

  useEffect(() => {
    getPatterns().then(setPatterns).catch(() => {})
  }, [])

  const filtered = patterns.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase()),
  )

  return (
    <div>
      <label className="block text-sm font-medium text-gray-300 mb-1">
        Analysis Pattern
      </label>
      <input
        type="text"
        placeholder="Search patterns..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 mb-1.5 text-sm text-gray-300 focus:outline-none focus:ring-2 focus:ring-violet-500"
      />
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        size={5}
        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-gray-100 focus:outline-none focus:ring-2 focus:ring-violet-500 min-h-[120px]"
      >
        {filtered.map((p) => (
          <option key={p.name} value={p.name}>
            {p.name}
          </option>
        ))}
      </select>
    </div>
  )
}