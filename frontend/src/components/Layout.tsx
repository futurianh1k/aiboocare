import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { 
  LayoutDashboard, 
  Users, 
  AlertTriangle, 
  Cpu, 
  Settings, 
  LogOut,
  Heart,
  Bell,
  Menu,
  X
} from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '../hooks/useAuth'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: '대시보드' },
  { to: '/users', icon: Users, label: '돌봄 대상자' },
  { to: '/cases', icon: AlertTriangle, label: '케이스 관리' },
  { to: '/devices', icon: Cpu, label: '디바이스' },
]

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <div className="flex min-h-screen">
      {/* 사이드바 */}
      <aside 
        className={`fixed left-0 top-0 h-full bg-bg-secondary border-r border-border transition-all duration-300 z-50 ${
          sidebarOpen ? 'w-64' : 'w-20'
        }`}
      >
        {/* 로고 */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center">
              <Heart className="w-5 h-5 text-white" />
            </div>
            {sidebarOpen && (
              <div>
                <h1 className="font-bold text-lg">AI BooCare</h1>
                <p className="text-xs text-text-muted">Care Console</p>
              </div>
            )}
          </div>
          <button 
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-bg-tertiary rounded-lg"
          >
            {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>

        {/* 네비게이션 */}
        <nav className="p-4 space-y-2">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${
                  isActive 
                    ? 'bg-primary/20 text-primary' 
                    : 'hover:bg-bg-tertiary text-text-secondary hover:text-text-primary'
                }`
              }
            >
              <item.icon size={20} />
              {sidebarOpen && <span>{item.label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* 유저 정보 */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-border">
          {sidebarOpen ? (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-bg-tertiary flex items-center justify-center">
                  <span className="text-sm font-medium">{user?.name?.charAt(0)}</span>
                </div>
                <div>
                  <p className="font-medium text-sm">{user?.name}</p>
                  <p className="text-xs text-text-muted">{user?.role}</p>
                </div>
              </div>
              <button 
                onClick={handleLogout}
                className="p-2 hover:bg-bg-tertiary rounded-lg text-text-secondary hover:text-danger"
              >
                <LogOut size={18} />
              </button>
            </div>
          ) : (
            <button 
              onClick={handleLogout}
              className="w-full p-3 hover:bg-bg-tertiary rounded-lg text-text-secondary hover:text-danger flex justify-center"
            >
              <LogOut size={20} />
            </button>
          )}
        </div>
      </aside>

      {/* 메인 콘텐츠 */}
      <main className={`flex-1 transition-all duration-300 ${sidebarOpen ? 'ml-64' : 'ml-20'}`}>
        {/* 상단 바 */}
        <header className="sticky top-0 z-40 bg-bg-primary/80 backdrop-blur-lg border-b border-border">
          <div className="flex items-center justify-between px-6 py-4">
            <div>
              <h2 className="text-xl font-semibold">AI Care Companion</h2>
              <p className="text-sm text-text-muted">독거노인 돌봄 관제 시스템</p>
            </div>
            <div className="flex items-center gap-4">
              <button className="relative p-2 hover:bg-bg-secondary rounded-lg">
                <Bell size={20} />
                <span className="absolute top-1 right-1 w-2 h-2 bg-danger rounded-full animate-pulse"></span>
              </button>
              <button className="p-2 hover:bg-bg-secondary rounded-lg">
                <Settings size={20} />
              </button>
            </div>
          </div>
        </header>

        {/* 페이지 콘텐츠 */}
        <div className="p-6">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
