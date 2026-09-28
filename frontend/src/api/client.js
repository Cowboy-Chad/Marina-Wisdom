// Relative by default: in production the backend serves this app and the API on
// the same origin; in dev Vite proxies /api to the backend. Override with
// VITE_API_BASE to point at a backend elsewhere.
const API_BASE = import.meta.env.VITE_API_BASE || '/api'

const TOKEN_KEY = 'cve_osint_token'

// localStorage can throw (private windows, blocked site data). A signed-out app
// is a working app, so never let a storage failure break the page.
export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    // ignore
  }
}

async function request(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  const resp = await fetch(`${API_BASE}${path}`, { ...options, headers })

  if (!resp.ok) {
    // FastAPI sends rejections as {"detail": "..."}. Surface that text so the
    // user sees the actual reason instead of raw JSON.
    let message = `Request failed: ${resp.status}`
    try {
      const body = await resp.json()
      if (body?.detail) message = body.detail
    } catch {
      // not JSON; keep the status-based message
    }
    if (resp.status === 401) {
      // The token is gone or was revoked. Drop it and let the app show the
      // login form rather than leaving every page failing in place.
      setToken(null)
      window.dispatchEvent(new Event('auth:expired'))
    }
    const error = new Error(message)
    error.status = resp.status
    throw error
  }

  return resp.json()
}

export function register(username, email) {
  return request('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, email }),
  })
}

export function getMe() {
  return request('/auth/me')
}

export function logout() {
  // Best effort: the local token is cleared regardless, so the user is signed
  // out here even if the server call fails.
  return request('/auth/logout', { method: 'POST' }).catch(() => {})
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

export function checkRumbleResult(url, pattern, model) {
  const params = new URLSearchParams({ url, pattern })
  if (model) params.set('model', model)
  return request(`/rumble/check-result?${params.toString()}`)
}

export function getModels() {
  return request('/models')
}
