import { Link, NavLink } from 'react-router-dom'
import { Shield, History, Video, LogOut } from 'lucide-react'

const navLinkClass = ({ isActive }) =>
  `flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition ${
    isActive
      ? 'bg-violet-600 text-white'
      : 'text-gray-300 hover:bg-gray-800 hover:text-white'
  }`

export default function Layout({ children, user, onSignOut }) {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <nav className="border-b border-gray-800 bg-gray-900/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between gap-4">
          <Link to="/analysis/rumble" className="flex items-center gap-2 text-lg font-bold shrink-0">
            <Shield className="text-violet-400" size={22} />
            CVE-OSINT-1
          </Link>
          <div className="flex items-center gap-1 flex-wrap justify-end">
            <NavLink to="/analysis/rumble" className={navLinkClass}>
              <Video size={16} /> Rumble
            </NavLink>
            <NavLink to="/history" className={navLinkClass}>
              <History size={16} /> History
            </NavLink>
            {user && (
              <div className="flex items-center gap-2 pl-2 ml-1 border-l border-gray-800">
                <span className="text-sm text-gray-400 truncate max-w-[10rem]" title={user.email}>
                  {user.username}
                </span>
                <button
                  onClick={onSignOut}
                  title="Sign out"
                  className="flex items-center gap-1 px-2 py-1.5 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition"
                >
                  <LogOut size={15} />
                  <span className="hidden sm:inline">Sign out</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </nav>
      <main className="max-w-6xl mx-auto px-4 py-8">{children}</main>
    </div>
  )
}
