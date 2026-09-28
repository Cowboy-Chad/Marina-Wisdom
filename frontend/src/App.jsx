import { useEffect, useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import RumbleAnalysisPage from './pages/RumbleAnalysisPage'
import HistoryPage from './pages/HistoryPage'
import { getMe, getToken, logout, setToken } from './api/client'

function App() {
  const [user, setUser] = useState(null)
  // Only worth a round trip if we think we have a token; otherwise the login
  // form would be held back by a spinner for nothing.
  const [checking, setChecking] = useState(Boolean(getToken()))

  useEffect(() => {
    if (!getToken()) return
    getMe()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setChecking(false))
  }, [])

  // Raised by the API client whenever the backend rejects our token, so an
  // expired session lands on the login form instead of a wall of failures.
  useEffect(() => {
    const onExpired = () => setUser(null)
    window.addEventListener('auth:expired', onExpired)
    return () => window.removeEventListener('auth:expired', onExpired)
  }, [])

  const handleSignOut = async () => {
    await logout() // needs the token, so it must run before we clear it
    setToken(null)
    setUser(null)
  }

  if (checking) {
    return (
      <div className="min-h-screen bg-gray-950 text-gray-400 flex items-center justify-center">
        Loading...
      </div>
    )
  }

  if (!user) return <LoginPage onSignedIn={setUser} />

  return (
    <Routes>
      <Route path="/" element={<Navigate to="/analysis/rumble" replace />} />
      <Route
        path="/analysis/rumble"
        element={<Layout user={user} onSignOut={handleSignOut}><RumbleAnalysisPage /></Layout>}
      />
      <Route
        path="/history"
        element={<Layout user={user} onSignOut={handleSignOut}><HistoryPage /></Layout>}
      />
      <Route path="*" element={<Navigate to="/analysis/rumble" replace />} />
    </Routes>
  )
}

export default App
