import { useState } from 'react'
import { Shield, Loader2 } from 'lucide-react'
import { register, setToken } from '../api/client'

export default function LoginPage({ onSignedIn }) {
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const canSubmit = username.trim().length >= 3 && email.trim().includes('@')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!canSubmit || busy) return
    setBusy(true)
    setError(null)
    try {
      const data = await register(username.trim(), email.trim())
      setToken(data.token)
      onSignedIn({ username: data.username, email: data.email })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center justify-center gap-2 mb-2">
          <Shield className="text-violet-400" size={26} />
          <h1 className="text-xl font-bold">CVE-OSINT-1</h1>
        </div>
        <p className="text-center text-sm text-gray-400 mb-6">
          Sign in to analyze videos from Marina Jacobi&apos;s Rumble channel.
        </p>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label htmlFor="username" className="block text-xs font-medium text-gray-400 mb-1">
              Username
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              placeholder="Pick any name you like"
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-violet-500 transition"
            />
          </div>

          <div>
            <label htmlFor="email" className="block text-xs font-medium text-gray-400 mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              placeholder="you@example.com"
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-violet-500 transition"
            />
          </div>

          {error && (
            <div className="text-sm text-red-400 bg-red-950/40 border border-red-900/60 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={!canSubmit || busy}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 disabled:bg-gray-800 disabled:text-gray-500 rounded-lg text-sm font-medium transition"
          >
            {busy && <Loader2 size={14} className="animate-spin" />}
            {busy ? 'Signing in...' : 'Enter'}
          </button>
        </form>

        <p className="text-xs text-gray-500 mt-4 text-center leading-relaxed">
          No password needed. Use the same username and email next time to get
          back to your history.
        </p>
      </div>
    </div>
  )
}
