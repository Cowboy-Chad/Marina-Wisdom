import { useCallback, useState } from 'react'

export default function usePersistedState(key, initialValue) {
  const [value, setValue] = useState(() => {
    try {
      const raw = sessionStorage.getItem(key)
      if (raw != null) return JSON.parse(raw)
    } catch {
      // ignore corrupt storage
    }
    return initialValue
  })

  const setValueAndPersist = useCallback((next) => {
    setValue((prev) => {
      const resolved = typeof next === 'function' ? next(prev) : next
      try {
        if (resolved == null) sessionStorage.removeItem(key)
        else sessionStorage.setItem(key, JSON.stringify(resolved))
      } catch {
        // storage unavailable
      }
      return resolved
    })
  }, [key])

  return [value, setValueAndPersist]
}