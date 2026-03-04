import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import CareUsers from './pages/CareUsers'
import Cases from './pages/Cases'
import Devices from './pages/Devices'
import Bundles from './pages/Bundles'
import Thresholds from './pages/Thresholds'
import CallTree from './pages/CallTree'
import Rules from './pages/Rules'
import Simulator from './pages/Simulator'
import Audit from './pages/Audit'
import Login from './pages/Login'
import { useAuth } from './hooks/useAuth'

function App() {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <div className="w-10 h-10 border-3 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-500">로딩 중...</p>
        </div>
      </div>
    )
  }

  return (
    <Routes>
      <Route path="/login" element={
        isAuthenticated ? <Navigate to="/" replace /> : <Login />
      } />
      
      <Route path="/" element={
        isAuthenticated ? <Layout /> : <Navigate to="/login" replace />
      }>
        {/* 모니터링 */}
        <Route index element={<Dashboard />} />
        <Route path="users" element={<CareUsers />} />
        <Route path="cases" element={<Cases />} />
        <Route path="devices" element={<Devices />} />
        
        {/* 정책 관리 */}
        <Route path="bundles" element={<Bundles />} />
        <Route path="thresholds" element={<Thresholds />} />
        <Route path="calltree" element={<CallTree />} />
        <Route path="rules" element={<Rules />} />
        
        {/* 도구 */}
        <Route path="simulator" element={<Simulator />} />
        <Route path="audit" element={<Audit />} />
      </Route>
    </Routes>
  )
}

export default App
