import { 
  Users, 
  AlertTriangle, 
  Cpu, 
  Activity,
  TrendingUp,
  Clock,
  ChevronRight,
  Shield
} from 'lucide-react'
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar
} from 'recharts'
import { Link } from 'react-router-dom'

// 더미 데이터
const alertTrend = [
  { time: '00:00', count: 12 },
  { time: '04:00', count: 8 },
  { time: '08:00', count: 25 },
  { time: '12:00', count: 18 },
  { time: '16:00', count: 22 },
  { time: '20:00', count: 15 },
]

const casesByStatus = [
  { name: 'Open', value: 12, color: '#EF4444' },
  { name: 'In Progress', value: 8, color: '#F59E0B' },
  { name: 'Escalated', value: 3, color: '#6366F1' },
  { name: 'Resolved', value: 45, color: '#22C55E' },
]

const deviceStatus = [
  { name: 'Online', count: 456, color: '#22C55E' },
  { name: 'Offline', count: 12, color: '#6B7280' },
  { name: 'Alert', count: 8, color: '#EF4444' },
]

const recentCases = [
  { id: 'CASE-001', user: '김영수', type: 'fall', severity: 'CRITICAL', status: 'open', time: '5분 전' },
  { id: 'CASE-002', user: '박순이', type: 'vitals', severity: 'ALERT', status: 'in_progress', time: '12분 전' },
  { id: 'CASE-003', user: '이철호', type: 'inactivity', severity: 'WARNING', status: 'escalated', time: '23분 전' },
  { id: 'CASE-004', user: '정미영', type: 'device', severity: 'INFO', status: 'resolved', time: '1시간 전' },
]

const severityConfig: Record<string, string> = {
  CRITICAL: 'badge-error',
  ALERT: 'badge-warning',
  WARNING: 'badge-info',
  INFO: 'badge-gray',
}

const statusConfig: Record<string, string> = {
  open: 'text-error',
  in_progress: 'text-warning',
  escalated: 'text-primary',
  resolved: 'text-success',
}

export default function Dashboard() {
  return (
    <div className="animate-fade-in space-y-6">
      {/* 페이지 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">대시보드</h1>
          <p className="text-gray-500 mt-1">실시간 모니터링 현황</p>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Clock size={16} />
          <span>마지막 업데이트: 방금 전</span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="card card-body">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-info-50 flex items-center justify-center">
              <Users size={24} className="text-info" />
            </div>
            <div>
              <p className="text-2xl font-bold">1,234</p>
              <p className="text-sm text-gray-500">돌봄 대상자</p>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t flex items-center justify-between text-sm">
            <span className="text-success">+12 이번 주</span>
            <Link to="/users" className="text-primary hover:underline flex items-center gap-1">
              상세보기 <ChevronRight size={14} />
            </Link>
          </div>
        </div>

        <div className="card card-body">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-error-50 flex items-center justify-center">
              <AlertTriangle size={24} className="text-error" />
            </div>
            <div>
              <p className="text-2xl font-bold text-error">23</p>
              <p className="text-sm text-gray-500">열린 케이스</p>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t flex items-center justify-between text-sm">
            <span className="text-error">3 Critical</span>
            <Link to="/cases" className="text-primary hover:underline flex items-center gap-1">
              상세보기 <ChevronRight size={14} />
            </Link>
          </div>
        </div>

        <div className="card card-body">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-success-50 flex items-center justify-center">
              <Cpu size={24} className="text-success" />
            </div>
            <div>
              <p className="text-2xl font-bold">476</p>
              <p className="text-sm text-gray-500">활성 디바이스</p>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t flex items-center justify-between text-sm">
            <span className="text-gray-500">12 오프라인</span>
            <Link to="/devices" className="text-primary hover:underline flex items-center gap-1">
              상세보기 <ChevronRight size={14} />
            </Link>
          </div>
        </div>

        <div className="card card-body">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-warning-50 flex items-center justify-center">
              <Shield size={24} className="text-warning" />
            </div>
            <div>
              <p className="text-2xl font-bold text-warning">Medium</p>
              <p className="text-sm text-gray-500">시스템 위험도</p>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t flex items-center justify-between text-sm">
            <span className="text-gray-500">정책 기준</span>
            <Link to="/simulator" className="text-primary hover:underline flex items-center gap-1">
              시뮬레이션 <ChevronRight size={14} />
            </Link>
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-3 gap-6">
        {/* Alert Trend */}
        <div className="col-span-2 card card-body">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">알림 추이 (24시간)</h3>
            <select className="text-sm py-1 px-2">
              <option>오늘</option>
              <option>이번 주</option>
              <option>이번 달</option>
            </select>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={alertTrend}>
                <defs>
                  <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366F1" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#6366F1" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="time" tick={{ fontSize: 12 }} stroke="#9CA3AF" />
                <YAxis tick={{ fontSize: 12 }} stroke="#9CA3AF" />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'white', 
                    border: '1px solid #E5E7EB',
                    borderRadius: '8px'
                  }}
                />
                <Area 
                  type="monotone" 
                  dataKey="count" 
                  stroke="#6366F1" 
                  strokeWidth={2}
                  fillOpacity={1} 
                  fill="url(#colorCount)" 
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Case Status */}
        <div className="card card-body">
          <h3 className="font-semibold mb-4">케이스 현황</h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={casesByStatus}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={70}
                  paddingAngle={2}
                >
                  {casesByStatus.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-wrap justify-center gap-3 mt-2">
            {casesByStatus.map((item) => (
              <div key={item.name} className="flex items-center gap-2 text-sm">
                <div 
                  className="w-3 h-3 rounded-full" 
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-gray-600">{item.name}</span>
                <span className="font-medium">{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-3 gap-6">
        {/* Recent Cases */}
        <div className="col-span-2 card">
          <div className="card-header flex items-center justify-between">
            <h3 className="font-semibold">최근 케이스</h3>
            <Link to="/cases" className="text-sm text-primary hover:underline">
              전체 보기
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table>
              <thead>
                <tr>
                  <th>Case ID</th>
                  <th>대상자</th>
                  <th>유형</th>
                  <th>심각도</th>
                  <th>상태</th>
                  <th>시간</th>
                </tr>
              </thead>
              <tbody>
                {recentCases.map((c) => (
                  <tr key={c.id} className="cursor-pointer hover:bg-gray-50">
                    <td className="font-mono text-sm text-primary">{c.id}</td>
                    <td>{c.user}</td>
                    <td className="text-sm">{c.type}</td>
                    <td>
                      <span className={`badge ${severityConfig[c.severity]}`}>
                        {c.severity}
                      </span>
                    </td>
                    <td className={`font-medium ${statusConfig[c.status]}`}>
                      {c.status.replace('_', ' ')}
                    </td>
                    <td className="text-gray-500 text-sm">{c.time}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Device Status */}
        <div className="card card-body">
          <h3 className="font-semibold mb-4">디바이스 상태</h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={deviceStatus} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" />
                <YAxis dataKey="name" type="category" width={60} />
                <Tooltip />
                <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                  {deviceStatus.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 pt-4 border-t">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500">총 디바이스</span>
              <span className="font-semibold">{deviceStatus.reduce((a, b) => a + b.count, 0)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
