import { useState } from 'react'
import { 
  Play, 
  AlertTriangle,
  Clock,
  Users,
  Cpu,
  TrendingUp,
  Activity,
  Shield,
  FileText,
  ChevronRight
} from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell, PieChart, Pie, Legend } from 'recharts'

// 더미 데이터
const simulationResult = {
  totalAlerts: 156,
  criticalCount: 12,
  escalationsTo119: 3,
  stormRiskScore: 'Medium',
  byGroup: [
    { name: 'VITALS', count: 78, color: '#EF4444' },
    { name: 'FALL', count: 42, color: '#F59E0B' },
    { name: 'INACTIVITY', count: 28, color: '#3B82F6' },
    { name: 'ENV', count: 8, color: '#6B7280' },
  ],
  bySeverity: [
    { name: 'CRITICAL', count: 12, color: '#B91C1C' },
    { name: 'ALERT', count: 45, color: '#EF4444' },
    { name: 'WARNING', count: 67, color: '#F59E0B' },
    { name: 'INFO', count: 32, color: '#3B82F6' },
  ],
  byStage: [
    { stage: 'Stage 1', count: 156 },
    { stage: 'Stage 2', count: 89 },
    { stage: 'Stage 3', count: 34 },
    { stage: 'Stage 4', count: 8 },
    { stage: '119', count: 3 },
  ],
  topTriggers: [
    { key: 'vitals.heart_rate.high', count: 45, users: 23, notes: 'Frequent during exercise hours' },
    { key: 'fall.impact.high', count: 42, users: 18, notes: 'Morning activity spike' },
    { key: 'inactivity.duration.long', count: 28, users: 15, notes: 'Night hours' },
    { key: 'vitals.spo2.low', count: 23, users: 12, notes: 'Monitor closely' },
    { key: 'env.temperature.high', count: 18, users: 8, notes: 'Summer pattern' },
  ],
  timeline: [
    { time: '00:00', alerts: 5 },
    { time: '02:00', alerts: 3 },
    { time: '04:00', alerts: 2 },
    { time: '06:00', alerts: 12 },
    { time: '08:00', alerts: 25 },
    { time: '10:00', alerts: 18 },
    { time: '12:00', alerts: 15 },
    { time: '14:00', alerts: 20 },
    { time: '16:00', alerts: 22 },
    { time: '18:00', alerts: 16 },
    { time: '20:00', alerts: 12 },
    { time: '22:00', alerts: 6 },
  ]
}

export default function Simulator() {
  const [scope, setScope] = useState('tenant')
  const [period, setPeriod] = useState('24h')
  const [bundleA, setBundleA] = useState('active')
  const [compareMode, setCompareMode] = useState(false)
  const [hasResult, setHasResult] = useState(false)

  const runSimulation = () => {
    setHasResult(true)
  }

  return (
    <div className="animate-fade-in">
      {/* 페이지 헤더 */}
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Simulator</h1>
        <p className="text-gray-500 mt-1">Dry-run policy against historical data</p>
      </div>

      {/* 입력 패널 */}
      <div className="card card-body mb-6">
        <div className="grid grid-cols-4 gap-6">
          {/* 대상 선택 */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-3">Target Scope</h4>
            <div className="space-y-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input 
                  type="radio" 
                  name="scope" 
                  value="tenant"
                  checked={scope === 'tenant'}
                  onChange={(e) => setScope(e.target.value)}
                />
                <span className="text-sm">Tenant 전체</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input 
                  type="radio" 
                  name="scope" 
                  value="user"
                  checked={scope === 'user'}
                  onChange={(e) => setScope(e.target.value)}
                />
                <span className="text-sm">특정 User</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input 
                  type="radio" 
                  name="scope" 
                  value="device"
                  checked={scope === 'device'}
                  onChange={(e) => setScope(e.target.value)}
                />
                <span className="text-sm">특정 Device</span>
              </label>
            </div>
            {scope === 'user' && (
              <input 
                type="text" 
                placeholder="Search user..."
                className="w-full mt-2 text-sm"
              />
            )}
            {scope === 'device' && (
              <input 
                type="text" 
                placeholder="Search device..."
                className="w-full mt-2 text-sm"
              />
            )}
          </div>

          {/* 기간 */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-3">Period</h4>
            <div className="flex gap-2 mb-2">
              {['1h', '24h', '7d'].map(p => (
                <button
                  key={p}
                  className={`px-3 py-1.5 text-sm rounded-lg border transition ${
                    period === p 
                      ? 'bg-primary-50 border-primary-500 text-primary-700' 
                      : 'border-gray-300 text-gray-600 hover:bg-gray-50'
                  }`}
                  onClick={() => setPeriod(p)}
                >
                  {p}
                </button>
              ))}
            </div>
            <input 
              type="datetime-local" 
              className="w-full text-sm"
              defaultValue="2026-03-04T00:00"
            />
          </div>

          {/* 정책 선택 */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-3">Policy Bundle</h4>
            <select 
              value={bundleA}
              onChange={(e) => setBundleA(e.target.value)}
              className="w-full mb-2"
            >
              <option value="active">default v1.2.0 (Active)</option>
              <option value="draft">default v1.3.0-draft</option>
            </select>
            <label className="flex items-center gap-2 cursor-pointer">
              <input 
                type="checkbox"
                checked={compareMode}
                onChange={(e) => setCompareMode(e.target.checked)}
              />
              <span className="text-sm">Compare mode</span>
            </label>
            {compareMode && (
              <select className="w-full mt-2">
                <option value="active">default v1.2.0 (Active)</option>
                <option value="draft">default v1.3.0-draft</option>
              </select>
            )}
          </div>

          {/* 실행 */}
          <div className="flex flex-col justify-end">
            <button 
              className="btn btn-primary btn-lg w-full"
              onClick={runSimulation}
            >
              <Play size={18} />
              Run Simulation
            </button>
            <label className="flex items-center gap-2 mt-2 text-xs text-gray-500">
              <input type="checkbox" />
              Include cooldown events
            </label>
          </div>
        </div>
      </div>

      {/* 결과 */}
      {hasResult && (
        <div className="grid gap-6" style={{ gridTemplateColumns: '1fr 380px' }}>
          {/* 좌측: 결과 요약 */}
          <div className="space-y-6">
            {/* KPI Row */}
            <div className="grid grid-cols-4 gap-4">
              <div className="card card-body">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-info-50 flex items-center justify-center">
                    <Activity size={20} className="text-info" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{simulationResult.totalAlerts}</p>
                    <p className="text-xs text-gray-500">Total Alerts</p>
                  </div>
                </div>
              </div>
              <div className="card card-body">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-error-50 flex items-center justify-center">
                    <AlertTriangle size={20} className="text-error" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-error">{simulationResult.criticalCount}</p>
                    <p className="text-xs text-gray-500">Critical</p>
                  </div>
                </div>
              </div>
              <div className="card card-body">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-error-50 flex items-center justify-center">
                    <TrendingUp size={20} className="text-error" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-error">{simulationResult.escalationsTo119}</p>
                    <p className="text-xs text-gray-500">119 Escalations</p>
                  </div>
                </div>
              </div>
              <div className="card card-body">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-warning-50 flex items-center justify-center">
                    <Shield size={20} className="text-warning" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-warning">{simulationResult.stormRiskScore}</p>
                    <p className="text-xs text-gray-500">Storm Risk</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Charts */}
            <div className="grid grid-cols-2 gap-4">
              <div className="card card-body">
                <h4 className="font-medium mb-4">By Event Group</h4>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={simulationResult.byGroup} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" />
                      <YAxis dataKey="name" type="category" width={80} />
                      <Tooltip />
                      <Bar dataKey="count">
                        {simulationResult.byGroup.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="card card-body">
                <h4 className="font-medium mb-4">By Severity</h4>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={simulationResult.bySeverity}
                        dataKey="count"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={70}
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                        labelLine={false}
                      >
                        {simulationResult.bySeverity.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* Stage Funnel */}
            <div className="card card-body">
              <h4 className="font-medium mb-4">Escalation Funnel (by Stage)</h4>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={simulationResult.byStage}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="stage" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="count" fill="#6366F1" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Top Triggers Table */}
            <div className="card">
              <div className="card-header">
                <h4 className="font-medium">Top Triggers</h4>
              </div>
              <div className="overflow-x-auto">
                <table>
                  <thead>
                    <tr>
                      <th>Key</th>
                      <th>Count</th>
                      <th>Users</th>
                      <th>Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {simulationResult.topTriggers.map((trigger) => (
                      <tr key={trigger.key}>
                        <td>
                          <span className="font-mono text-sm text-primary">{trigger.key}</span>
                        </td>
                        <td className="font-semibold">{trigger.count}</td>
                        <td>{trigger.users}</td>
                        <td className="text-sm text-gray-500">{trigger.notes}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* 우측: 타임라인 & Findings */}
          <div className="space-y-4">
            {/* Findings */}
            <div className="card card-body">
              <h4 className="font-medium mb-3">Findings</h4>
              <div className="space-y-2">
                <div className="p-3 bg-warning-50 rounded-lg border border-warning-100">
                  <div className="flex items-start gap-2">
                    <AlertTriangle size={16} className="text-warning mt-0.5" />
                    <div className="text-sm">
                      <p className="font-medium text-warning-700">Expected Alert Surge</p>
                      <p className="text-warning-600">08:00-10:00 시간대에 25개 알림 예상</p>
                    </div>
                  </div>
                </div>
                <div className="p-3 bg-info-50 rounded-lg border border-info-100">
                  <div className="flex items-start gap-2">
                    <FileText size={16} className="text-info mt-0.5" />
                    <div className="text-sm">
                      <p className="font-medium text-info-700">Cooldown Recommendation</p>
                      <p className="text-info-600">heart_rate.high 룰에 cooldown 추가 권장</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Timeline Chart */}
            <div className="card card-body">
              <h4 className="font-medium mb-3">Hourly Distribution</h4>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={simulationResult.timeline}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" tick={{ fontSize: 10 }} />
                    <YAxis />
                    <Tooltip />
                    <Area 
                      type="monotone" 
                      dataKey="alerts" 
                      stroke="#6366F1" 
                      fill="#E0E7FF" 
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Event Timeline */}
            <div className="card">
              <div className="card-header">
                <h4 className="font-medium">Recent Events</h4>
              </div>
              <div className="divide-y max-h-96 overflow-y-auto">
                {[
                  { time: '08:23:15', type: 'heart_rate.high', rule: 'vitals.heart_rate.high', stage: 1 },
                  { time: '08:25:42', type: 'fall', rule: 'fall.impact.high', stage: 1 },
                  { time: '08:30:10', type: 'no_response', rule: 'escalation.no_response', stage: 2 },
                  { time: '08:45:00', type: 'spo2_low', rule: 'vitals.spo2.low', stage: 1 },
                  { time: '09:12:33', type: 'inactivity', rule: 'inactivity.duration.long', stage: 1 },
                ].map((event, i) => (
                  <div key={i} className="p-3 hover:bg-gray-50 cursor-pointer">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-xs text-gray-400 font-mono">{event.time}</p>
                        <p className="text-sm font-medium">{event.type}</p>
                        <p className="text-xs text-gray-500">{event.rule}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="badge badge-primary">Stage {event.stage}</span>
                        <ChevronRight size={14} className="text-gray-400" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {!hasResult && (
        <div className="card card-body empty-state" style={{ minHeight: '400px' }}>
          <Play size={48} className="mb-4" />
          <p className="text-gray-500">Configure options and run simulation</p>
        </div>
      )}
    </div>
  )
}
