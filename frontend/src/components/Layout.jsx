import { Link, NavLink } from 'react-router-dom'
import { Shield, History, MonitorPlay, Video } from 'lucide-react'

const navLinkClass = ({ isActive }) =>
  `flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition ${
    isActive
      ? 'bg-violet-600 text-white'
      : 'text-gray-300 hover:bg-gray-800 hover:text-white'
  }`

export default function Layout({ children }) {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <nav className="border-b border-gray-800 bg-gray-900/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link to="/analysis/youtube" className="flex items-center gap-2 text-lg font-bold">
            <Shield className="text-violet-400" size={22} />
            CVE-OSINT-1
          </Link>
          <div className="flex items-center gap-1 flex-wrap">
            <NavLink to="/analysis/youtube" className={navLinkClass}>
              <MonitorPlay size={16} /> YouTube
            </NavLink>
            <NavLink to="/analysis/rumble" className={navLinkClass}>
              <Video size={16} /> Rumble
            </NavLink>
            <NavLink to="/history" className={navLinkClass}>
              <History size={16} /> History
            </NavLink>
          </div>
        </div>
      </nav>
      <main className="max-w-6xl mx-auto px-4 py-8">{children}</main>
    </div>
  )
}