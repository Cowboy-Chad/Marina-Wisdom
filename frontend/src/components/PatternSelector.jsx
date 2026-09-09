import { useEffect, useRef, useState } from 'react'
import { getPatterns } from '../api/client'
import { Check } from 'lucide-react'
import usePersistedState from '../hooks/usePersistedState'

export default function PatternSelector({ value, onChange, storageKey = 'shared' }) {
  const [patterns, setPatterns] = useState([])
  const [search, setSearch] = usePersistedState(`pattern-search-${storageKey}`, '')
  const [confirmed, setConfirmed] = usePersistedState(`pattern-confirmed-${storageKey}`, '')
  const lastClickRef = useRef({ name: '', time: 0 })

  useEffect(() => {
    getPatterns().then(setPatterns).catch(() => {})
  }, [])

  const filtered = patterns.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase()),
  )

  const handleClick = (name) => {
    const now = Date.now()
    if (name === lastClickRef.current.name && now - lastClickRef.current.time < 400) {
      onChange(name)
      setConfirmed(name)
      lastClickRef.current = { name: '', time: 0 }
      return
    }
    lastClickRef.current = { name, time: now }
    onChange(name)
    setConfirmed('')
  }

  return (
    <div>
      <label className="block text-sm font-medium text-gray-300 mb-1">
        Analysis Pattern
      </label>
      <input
        type="text"
        placeholder="Search patterns..."
        value={search}
        onChange={(e) => {
          setSearch(e.target.value)
          setConfirmed('')
        }}
        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 mb-1.5 text-sm text-gray-300 focus:outline-none focus:ring-2 focus:ring-violet-500"
      />
      <div className="w-full bg-gray-800 border border-gray-700 rounded-lg overflow-y-auto min-h-[120px] max-h-[200px]">
        {filtered.map((p) => (
          <div
            key={p.name}
            onClick={() => handleClick(p.name)}
            className={`px-3 py-1.5 text-sm cursor-pointer transition ${
              p.name === value
                ? 'bg-violet-600/30 text-violet-200'
                : 'text-gray-100 hover:bg-gray-700'
            }`}
          >
            {p.name}
          </div>
        ))}
      </div>
      {confirmed && (
        <div className="mt-2 flex items-center gap-2 px-3 py-2 bg-gray-800 border border-violet-600/50 rounded-lg text-sm text-violet-300">
          <Check size={16} className="text-violet-400" />
          <span className="font-medium">{confirmed}</span>
        </div>
      )}
    </div>
  )
}