import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import YouTubeAnalysisPage from './pages/YouTubeAnalysisPage'
import RumbleAnalysisPage from './pages/RumbleAnalysisPage'
import WebAnalysisPage from './pages/WebAnalysisPage'
import FileAnalysisPage from './pages/FileAnalysisPage'
import HistoryPage from './pages/HistoryPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/analysis/youtube" replace />} />
      <Route
        path="/analysis/youtube"
        element={<Layout><YouTubeAnalysisPage /></Layout>}
      />
      <Route
        path="/analysis/rumble"
        element={<Layout><RumbleAnalysisPage /></Layout>}
      />
      <Route
        path="/analysis/web"
        element={<Layout><WebAnalysisPage /></Layout>}
      />
      <Route
        path="/analysis/file"
        element={<Layout><FileAnalysisPage /></Layout>}
      />
      <Route
        path="/history"
        element={<Layout><HistoryPage /></Layout>}
      />
    </Routes>
  )
}

export default App