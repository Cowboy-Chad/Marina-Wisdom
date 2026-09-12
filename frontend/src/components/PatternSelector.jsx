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
  const [highlightedIndex, setHighlightedIndex] = useState(-1)
  const dropdownRef = useRef(null)

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

  useEffect(() => {
    if (highlightedIndex < 0 || !dropdownRef.current) return
    const items = dropdownRef.current.children
    if (items[highlightedIndex]) {
      items[highlightedIndex].scrollIntoView({ block: 'nearest' })
    }
  }, [highlightedIndex])

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
          if (e.key === 'ArrowDown') {
            e.preventDefault()
            setHighlightedIndex((prev) =>
              prev < filtered.length - 1 ? prev + 1 : 0
            )
          } else if (e.key === 'ArrowUp') {
            e.preventDefault()
            setHighlightedIndex((prev) =>
              prev > 0 ? prev - 1 : filtered.length - 1
            )
          } else if (e.key === 'Enter') {
            if (confirmed) {
              if (onEnter) onEnter()
            } else if (filtered.length > 0) {
              const idx = highlightedIndex >= 0 ? highlightedIndex : 0
              const name = filtered[idx].name
              onChange(name)
              setSearch(name)
              setConfirmed(name)
              if (onEnter) onEnter()
            }
          } else {
            setHighlightedIndex(-1)
          }
        }}
        className={`w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 mb-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 ${
          confirmed ? 'text-green-400' : 'text-gray-300'
        }`}
      />
      {showDropdown && (
        <div ref={dropdownRef} className="w-full bg-gray-800 border border-gray-700 rounded-lg overflow-y-auto min-h-[120px] max-h-[200px]">
          {loading ? (
            <div className="px-3 py-1.5 text-sm text-gray-500">Loading patterns...</div>
          ) : filtered.length === 0 ? (
            <div className="px-3 py-1.5 text-sm text-gray-500">No patterns match your search</div>
          ) : filtered.map((p, idx) => (
            <div
              key={p.name}
              onClick={() => handleClick(p.name)}
              className={`px-3 py-1.5 text-sm cursor-pointer transition ${
                p.name === value
                  ? 'bg-violet-600/30 text-violet-200'
                  : idx === highlightedIndex
                    ? 'bg-gray-600 text-white'
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