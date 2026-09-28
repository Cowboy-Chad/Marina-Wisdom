// Relative by default: in production the backend serves this app and the API on
// the same origin; in dev Vite proxies /api to the backend. Override with
// VITE_API_BASE to point at a backend elsewhere.
const API_BASE = import.meta.env.VITE_API_BASE || '/api'

async function request(path, options = {}) {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(text || `Request failed: ${resp.status}`)
  }
  return resp.json()
}

export function startYouTubeAnalysis(data) {
  return request('/youtube/analyze', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function startRumbleAnalysis(data) {
  return request('/rumble/analyze', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function pollJob(jobId) {
  return request(`/jobs/${jobId}`)
}

export function getHistory(params = {}) {
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v) qs.set(k, v)
  }
  return request(`/history?${qs.toString()}`)
}

export function getPatterns() {
  return request('/patterns')
}

export function checkYouTubeResult(url, pattern, model) {
  const params = new URLSearchParams({ url, pattern })
  if (model) params.set('model', model)
  return request(`/youtube/check-result?${params.toString()}`)
}

export function checkRumbleResult(url, pattern, model) {
  const params = new URLSearchParams({ url, pattern })
  if (model) params.set('model', model)
  return request(`/rumble/check-result?${params.toString()}`)
}

export function getModels() {
  return request('/models')
}