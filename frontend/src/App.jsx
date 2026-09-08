import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import AnalysisPage from './pages/AnalysisPage'
import HistoryPage from './pages/HistoryPage'

function App() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <Layout>
            <Navigate to="/analysis" replace />
          </Layout>
        }
      />
      <Route
        path="/analysis"
        element={
          <Layout>
            <AnalysisPage />
          </Layout>
        }
      />
      <Route
        path="/history"
        element={
          <Layout>
            <HistoryPage />
          </Layout>
        }
      />
    </Routes>
  )
}

export default App