import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { 
  LayoutDashboard, 
  Users, 
  AlertTriangle, 
  Cpu, 
  LogOut,
  Heart,
  Bell,
  Search,
  ChevronDown,
  Package,
  Gauge,
  GitBranch,
  FileCode,
  Play,
  FileText,
  HelpCircle,
  Settings
} from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '../hooks/useAuth'

// 문서 기반 네비게이션 구조
const navSections = [
  {
    title: '모니터링',
    items: [
      { to: '/', icon: LayoutDashboard, label: '대시보드' },
      { to: '/users', icon: Users, label: '돌봄 대상자' },
      { to: '/cases', icon: AlertTriangle, label: '케이스 관리' },
      { to: '/devices', icon: Cpu, label: '디바이스' },
    ]
  },
  {
    title: '정책 관리',
    items: [
      { to: '/bundles', icon: Package, label: 'Bundles' },
      { to: '/thresholds', icon: Gauge, label: 'Thresholds' },
      { to: '/calltree', icon: GitBranch, label: 'Call Tree' },
      { to: '/rules', icon: FileCode, label: 'Rules' },
    ]
  },
  {
    title: '도구',
    items: [
      { to: '/simulator', icon: Play, label: 'Simulator' },
      { to: '/audit', icon: FileText, label: 'Audit' },
    ]
  }
]

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <div className="flex min-h-screen">
      {/* 좌측 사이드바 (240px) */}
      <aside 
        className="fixed left-0 top-0 h-full bg-gray-900 flex flex-col"
        style={{ width: 'var(--sidebar-width)' }}
      >
        {/* 로고 */}
        <div className="p-4 border-b border-gray-800">
          <div className="flex items-center gap-3">
            <div 
              className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, var(--primary-500), var(--success-500))' }}
            >
              <Heart className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-semibold text-white">AI BooCare</h1>
              <p className="text-xs text-gray-400">Policy Console</p>
            </div>
          </div>
        </div>

        {/* Tenant Switcher */}
        <div className="p-4 border-b border-gray-800">
          <button className="w-full flex items-center justify-between px-3 py-2 bg-gray-800 rounded-lg text-sm text-gray-300 hover:bg-gray-700 transition">
            <span>Default Tenant</span>
            <ChevronDown size={16} />
          </button>
        </div>

        {/* 네비게이션 */}
        <nav className="flex-1 overflow-y-auto p-4">
          {navSections.map((section) => (
            <div key={section.title} className="mb-6">
              <h3 className="px-3 mb-2 text-xs font-medium text-gray-500 uppercase tracking-wider">
                {section.title}
              </h3>
              <div className="space-y-1">
                {section.items.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === '/'}
                    className={({ isActive }) =>
                      `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition ${
                        isActive 
                          ? 'bg-primary-600 text-white' 
                          : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                      }`
                    }
                  >
                    <item.icon size={18} />
                    <span>{item.label}</span>
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        {/* 하단 영역 */}
        <div className="p-4 border-t border-gray-800">
          <div className="flex items-center gap-3 mb-4">
            <a href="#" className="text-gray-400 hover:text-white transition">
              <HelpCircle size={18} />
            </a>
            <a href="/api/v1/docs" target="_blank" className="text-xs text-gray-500 hover:text-gray-300">
              API Docs
            </a>
            <span className="ml-auto text-xs text-gray-600">v0.1.0</span>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center text-sm font-medium text-white">
              {user?.name?.charAt(0) || 'A'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{user?.name}</p>
              <p className="text-xs text-gray-500">{user?.role}</p>
            </div>
            <button 
              onClick={handleLogout}
              className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition"
              title="로그아웃"
            >
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </aside>

      {/* 메인 콘텐츠 */}
      <main 
        className="flex-1 flex flex-col"
        style={{ marginLeft: 'var(--sidebar-width)' }}
      >
        {/* 상단 헤더 (56px) */}
        <header 
          className="sticky top-0 z-30 bg-white border-b flex items-center justify-between px-6"
          style={{ height: 'var(--header-height)' }}
        >
          {/* 좌측: Breadcrumbs */}
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-400">AI Care Companion</span>
            <span className="text-gray-300">/</span>
            <span className="font-medium text-gray-700">Policy Console</span>
          </div>

          {/* 중앙: 검색 */}
          <div className="flex-1 max-w-md mx-8">
            <div className="input-with-icon">
              <Search size={16} className="icon" />
              <input
                type="text"
                placeholder="Search rules, thresholds by key..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full"
              />
            </div>
          </div>

          {/* 우측: 유저 메뉴 */}
          <div className="flex items-center gap-4">
            <button className="relative p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition">
              <Bell size={20} />
              <span className="absolute top-1 right-1 w-2 h-2 bg-error-500 rounded-full"></span>
            </button>
            <button className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition">
              <Settings size={20} />
            </button>
            <div className="flex items-center gap-2 pl-4 border-l">
              <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center text-primary-700 font-medium text-sm">
                {user?.name?.charAt(0) || 'A'}
              </div>
              <span className="badge badge-primary text-xs">{user?.role}</span>
            </div>
          </div>
        </header>

        {/* 페이지 콘텐츠 */}
        <div className="flex-1 p-6 bg-gray-50">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
