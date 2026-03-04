import { 
  Users, 
  AlertTriangle, 
  Cpu, 
  Activity,
  TrendingUp,
  Clock,
  CheckCircle,
  XCircle,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react'
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell
} from 'recharts'

// 더미 데이터
const stats = [
  { 
    label: '돌봄 대상자', 
    value: 1234, 
    change: '+12', 
    trend: 'up',
    icon: Users,
    color: 'primary'
  },
  { 
    label: '활성 케이스', 
    value: 23, 
    change: '-5', 
    trend: 'down',
    icon: AlertTriangle,
    color: 'warning'
  },
  { 
    label: '온라인 디바이스', 
    value: 567, 
    change: '+3', 
    trend: 'up',
    icon: Cpu,
    color: 'secondary'
  },
  { 
    label: '오늘 이벤트', 
    value: 89, 
    change: '+15', 
    trend: 'up',
    icon: Activity,
    color: 'accent'
  },
]

const eventData = [
  { time: '00:00', events: 12 },
  { time: '04:00', events: 8 },
  { time: '08:00', events: 45 },
  { time: '12:00', events: 32 },
  { time: '16:00', events: 28 },
  { time: '20:00', events: 41 },
  { time: '24:00', events: 15 },
]

const casesByType = [
  { name: '낙상', value: 35, color: '#EF4444' },
  { name: '무활동', value: 28, color: '#F97316' },
  { name: '응급버튼', value: 20, color: '#F59E0B' },
  { name: '생체이상', value: 17, color: '#10B981' },
]

const recentCases = [
  { id: 'CS-001', user: '김영희', type: '낙상 감지', severity: 'critical', time: '5분 전', status: 'open' },
  { id: 'CS-002', user: '이철수', type: '무활동', severity: 'warning', time: '12분 전', status: 'in_progress' },
  { id: 'CS-003', user: '박민수', type: '응급버튼', severity: 'critical', time: '23분 전', status: 'resolved' },
  { id: 'CS-004', user: '최순자', type: '생체이상', severity: 'info', time: '1시간 전', status: 'resolved' },
]

const severityColors: Record<string, string> = {
  critical: 'bg-danger text-white',
  warning: 'bg-warning text-white',
  info: 'bg-primary text-white',
}

const statusColors: Record<string, string> = {
  open: 'text-danger',
  in_progress: 'text-warning',
  resolved: 'text-secondary',
}

export default function Dashboard() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">대시보드</h1>
          <p className="text-text-secondary">전체 시스템 현황을 한눈에 확인하세요.</p>
        </div>
        <div className="flex items-center gap-2 text-text-secondary">
          <Clock size={16} />
          <span className="text-sm">마지막 업데이트: 방금 전</span>
        </div>
      </div>

      {/* 통계 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => (
          <div 
            key={stat.label}
            className="bg-bg-card rounded-2xl p-6 border border-border hover:border-border-light transition-colors"
          >
            <div className="flex items-start justify-between">
              <div className={`p-3 rounded-xl bg-${stat.color}/20`}>
                <stat.icon className={`w-6 h-6 text-${stat.color}`} style={{ color: `var(--${stat.color})` }} />
              </div>
              <div className={`flex items-center gap-1 text-sm ${
                stat.trend === 'up' ? 'text-secondary' : 'text-danger'
              }`}>
                {stat.trend === 'up' ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}
                {stat.change}
              </div>
            </div>
            <div className="mt-4">
              <p className="text-3xl font-bold">{stat.value.toLocaleString()}</p>
              <p className="text-text-secondary text-sm mt-1">{stat.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* 차트 영역 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 이벤트 추이 */}
        <div className="lg:col-span-2 bg-bg-card rounded-2xl p-6 border border-border">
          <h3 className="font-semibold mb-6">오늘 이벤트 추이</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={eventData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="time" stroke="var(--text-muted)" />
              <YAxis stroke="var(--text-muted)" />
              <Tooltip 
                contentStyle={{ 
                  background: 'var(--bg-card)', 
                  border: '1px solid var(--border)',
                  borderRadius: '8px'
                }}
              />
              <Line 
                type="monotone" 
                dataKey="events" 
                stroke="var(--primary)" 
                strokeWidth={3}
                dot={{ fill: 'var(--primary)', strokeWidth: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* 케이스 유형 분포 */}
        <div className="bg-bg-card rounded-2xl p-6 border border-border">
          <h3 className="font-semibold mb-6">케이스 유형 분포</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={casesByType}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                paddingAngle={5}
                dataKey="value"
              >
                {casesByType.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ 
                  background: 'var(--bg-card)', 
                  border: '1px solid var(--border)',
                  borderRadius: '8px'
                }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="grid grid-cols-2 gap-2 mt-4">
            {casesByType.map((item) => (
              <div key={item.name} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ background: item.color }}></div>
                <span className="text-sm text-text-secondary">{item.name}</span>
                <span className="text-sm font-medium ml-auto">{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 최근 케이스 */}
      <div className="bg-bg-card rounded-2xl border border-border overflow-hidden">
        <div className="p-6 border-b border-border">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">최근 케이스</h3>
            <a href="/cases" className="text-primary text-sm hover:underline">
              전체 보기 →
            </a>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table>
            <thead>
              <tr>
                <th>케이스 ID</th>
                <th>대상자</th>
                <th>유형</th>
                <th>심각도</th>
                <th>발생 시간</th>
                <th>상태</th>
              </tr>
            </thead>
            <tbody>
              {recentCases.map((caseItem) => (
                <tr key={caseItem.id} className="hover:bg-bg-tertiary">
                  <td className="font-mono text-primary">{caseItem.id}</td>
                  <td>{caseItem.user}</td>
                  <td>{caseItem.type}</td>
                  <td>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${severityColors[caseItem.severity]}`}>
                      {caseItem.severity === 'critical' ? '위험' : caseItem.severity === 'warning' ? '주의' : '정보'}
                    </span>
                  </td>
                  <td className="text-text-secondary">{caseItem.time}</td>
                  <td>
                    <span className={`flex items-center gap-1 ${statusColors[caseItem.status]}`}>
                      {caseItem.status === 'resolved' ? (
                        <CheckCircle size={14} />
                      ) : caseItem.status === 'open' ? (
                        <XCircle size={14} />
                      ) : (
                        <Clock size={14} />
                      )}
                      {caseItem.status === 'open' ? '미처리' : caseItem.status === 'in_progress' ? '처리 중' : '해결됨'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
