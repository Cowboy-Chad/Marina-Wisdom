const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api'

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

export function startAnalysis(data) {
  return request('/analyze', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function startFileAnalysis(formData) {
  return fetch(`${API_BASE}/analyze/file`, {
    method: 'POST',
    body: formData,
  }).then(async (resp) => {
    if (!resp.ok) throw new Error(await resp.text())
    return resp.json()
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

export function checkResult(source, url, pattern, model) {
  const params = new URLSearchParams({ source, url, pattern })
  if (model) params.set('model', model)
  return request(`/check-result?${params.toString()}`)
}

export function getModels() {
  return request('/models')
}