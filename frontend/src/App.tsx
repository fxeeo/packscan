import { Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { HomePage } from './pages/HomePage'
import { ScanPage } from './pages/ScanPage'
import { BarcodePage } from './pages/BarcodePage'
import { ResultPage } from './pages/ResultPage'
import { HistoryPage } from './pages/HistoryPage'
import { DashboardPage } from './pages/DashboardPage'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/barcode" element={<BarcodePage />} />
        <Route path="/scan" element={<ScanPage />} />
        <Route path="/result/:id" element={<ResultPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
      </Routes>
    </Layout>
  )
}
