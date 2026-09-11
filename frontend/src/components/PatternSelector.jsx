import { useEffect, useRef, useState } from 'react'
import { getPatterns } from '../api/client'
import usePersistedState from '../hooks/usePersistedState'

export default function PatternSelector({ value, onChange, storageKey = 'shared', onEnter }) {
  const [patterns, setPatterns] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = usePersistedState(`pattern-search-${storageKey}`, '')
  const [confirmed, setConfirmed] = usePersistedState(`pattern-confirmed-${storageKey}`, '')
  const showDropdown = !confirmed
  const lastClickRef = useRef({ name: '', time: 0 })

  useEffect(() => {
    setLoading(true)
    getPatterns().then((data) => {
      setPatterns(data)
      setLoading(false)
    }).catch((e) => {
      console.error('Failed to load patterns:', e)
      setLoading(false)
    })
  }, [])

  const filtered = patterns.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase()),
  )

  const handleClick = (name) => {
    const now = Date.now()
    if (name === lastClickRef.current.name && now - lastClickRef.current.time < 400) {
      onChange(name)
      setSearch(name)
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
        onKeyDown={(e) => {
          if (e.key === 'Enter' && filtered.length > 0) {
            const name = filtered[0].name
            onChange(name)
            setSearch(name)
            setConfirmed(name)
            if (onEnter) onEnter()
          }
        }}
        className={`w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 mb-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 ${
          confirmed ? 'text-green-400' : 'text-gray-300'
        }`}
      />
      {showDropdown && (
        <div className="w-full bg-gray-800 border border-gray-700 rounded-lg overflow-y-auto min-h-[120px] max-h-[200px]">
          {loading ? (
            <div className="px-3 py-1.5 text-sm text-gray-500">Loading patterns...</div>
          ) : filtered.length === 0 ? (
            <div className="px-3 py-1.5 text-sm text-gray-500">No patterns match your search</div>
          ) : filtered.map((p) => (
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
      )}
    </div>
  )
}