import { useState } from 'react'
import { 
  Search, 
  Filter, 
  AlertTriangle, 
  Clock, 
  CheckCircle, 
  XCircle,
  ChevronRight,
  Phone,
  User,
  MapPin
} from 'lucide-react'
import { format } from 'date-fns'
import { ko } from 'date-fns/locale'

// 더미 데이터
const cases = [
  { 
    id: 'CS-2026-0001', 
    user: { id: 'USR-001', name: '김영희', age: 78, address: '서울시 강남구' },
    type: 'fall',
    typeLabel: '낙상 감지',
    severity: 'critical',
    status: 'open',
    createdAt: new Date(2026, 2, 4, 10, 30),
    description: '욕실에서 낙상 감지. 충격 강도 2.3g.',
    escalationStep: 1
  },
  { 
    id: 'CS-2026-0002', 
    user: { id: 'USR-002', name: '이철수', age: 82, address: '서울시 서초구' },
    type: 'inactivity',
    typeLabel: '무활동',
    severity: 'warning',
    status: 'in_progress',
    createdAt: new Date(2026, 2, 4, 9, 15),
    description: '2시간 이상 움직임 없음.',
    escalationStep: 2
  },
  { 
    id: 'CS-2026-0003', 
    user: { id: 'USR-003', name: '박민수', age: 75, address: '서울시 송파구' },
    type: 'emergency_button',
    typeLabel: '응급버튼',
    severity: 'critical',
    status: 'resolved',
    createdAt: new Date(2026, 2, 4, 8, 0),
    description: '응급 버튼 3초 이상 누름.',
    escalationStep: 3,
    resolvedAt: new Date(2026, 2, 4, 8, 45)
  },
  { 
    id: 'CS-2026-0004', 
    user: { id: 'USR-004', name: '최순자', age: 80, address: '서울시 강동구' },
    type: 'low_spo2',
    typeLabel: 'SpO2 저하',
    severity: 'warning',
    status: 'resolved',
    createdAt: new Date(2026, 2, 3, 22, 30),
    description: 'SpO2 92% 감지. 정상 범위 이하.',
    escalationStep: 1,
    resolvedAt: new Date(2026, 2, 3, 23, 15)
  },
]

const severityConfig: Record<string, { label: string; color: string; bg: string; icon: any }> = {
  critical: { label: '위험', color: 'text-danger', bg: 'bg-danger/20', icon: XCircle },
  warning: { label: '주의', color: 'text-warning', bg: 'bg-warning/20', icon: AlertTriangle },
  info: { label: '정보', color: 'text-primary', bg: 'bg-primary/20', icon: AlertTriangle },
}

const statusConfig: Record<string, { label: string; color: string; bg: string }> = {
  open: { label: '미처리', color: 'text-danger', bg: 'bg-danger/20' },
  in_progress: { label: '처리 중', color: 'text-warning', bg: 'bg-warning/20' },
  resolved: { label: '해결됨', color: 'text-secondary', bg: 'bg-secondary/20' },
}

export default function Cases() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedStatus, setSelectedStatus] = useState('all')
  const [selectedCase, setSelectedCase] = useState<typeof cases[0] | null>(null)

  const filteredCases = cases.filter(c => {
    const matchesSearch = c.user.name.includes(searchQuery) || c.id.includes(searchQuery)
    const matchesStatus = selectedStatus === 'all' || c.status === selectedStatus
    return matchesSearch && matchesStatus
  })

  return (
    <div className="flex gap-6 animate-fade-in">
      {/* 케이스 목록 */}
      <div className={`flex-1 space-y-6 ${selectedCase ? 'hidden lg:block' : ''}`}>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">케이스 관리</h1>
            <p className="text-text-secondary">발생한 이벤트와 케이스를 관리합니다.</p>
          </div>
        </div>

        {/* 필터 */}
        <div className="flex flex-col md:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
            <input
              type="text"
              placeholder="이름 또는 케이스 ID로 검색..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-12"
            />
          </div>
          <div className="flex gap-2">
            <select 
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="px-4 py-2 rounded-xl"
            >
              <option value="all">전체 상태</option>
              <option value="open">미처리</option>
              <option value="in_progress">처리 중</option>
              <option value="resolved">해결됨</option>
            </select>
          </div>
        </div>

        {/* 케이스 리스트 */}
        <div className="space-y-4">
          {filteredCases.map((caseItem) => {
            const severity = severityConfig[caseItem.severity]
            const status = statusConfig[caseItem.status]
            const SeverityIcon = severity.icon

            return (
              <div
                key={caseItem.id}
                onClick={() => setSelectedCase(caseItem)}
                className={`bg-bg-card rounded-xl border border-border hover:border-border-light p-4 cursor-pointer transition-all ${
                  selectedCase?.id === caseItem.id ? 'border-primary' : ''
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4">
                    <div className={`p-3 rounded-xl ${severity.bg}`}>
                      <SeverityIcon className={`w-5 h-5 ${severity.color}`} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-mono text-sm text-text-muted">{caseItem.id}</span>
                        <span className={`px-2 py-0.5 rounded-full text-xs ${severity.bg} ${severity.color}`}>
                          {severity.label}
                        </span>
                        <span className={`px-2 py-0.5 rounded-full text-xs ${status.bg} ${status.color}`}>
                          {status.label}
                        </span>
                      </div>
                      <h3 className="font-medium">{caseItem.typeLabel}</h3>
                      <p className="text-sm text-text-secondary mt-1">
                        {caseItem.user.name} ({caseItem.user.age}세) · {caseItem.user.address}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-text-muted">
                      {format(caseItem.createdAt, 'MM.dd HH:mm', { locale: ko })}
                    </p>
                    <ChevronRight className="w-5 h-5 text-text-muted mt-2 ml-auto" />
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* 케이스 상세 */}
      {selectedCase && (
        <div className="w-full lg:w-[400px] bg-bg-card rounded-2xl border border-border p-6 sticky top-24 h-fit">
          <button 
            className="lg:hidden mb-4 text-primary"
            onClick={() => setSelectedCase(null)}
          >
            ← 목록으로
          </button>
          
          <div className="flex items-center gap-2 mb-4">
            <span className={`px-3 py-1 rounded-full text-sm ${severityConfig[selectedCase.severity].bg} ${severityConfig[selectedCase.severity].color}`}>
              {severityConfig[selectedCase.severity].label}
            </span>
            <span className={`px-3 py-1 rounded-full text-sm ${statusConfig[selectedCase.status].bg} ${statusConfig[selectedCase.status].color}`}>
              {statusConfig[selectedCase.status].label}
            </span>
          </div>

          <h2 className="text-xl font-bold mb-2">{selectedCase.typeLabel}</h2>
          <p className="text-text-secondary mb-6">{selectedCase.description}</p>

          <div className="space-y-4 mb-6">
            <div className="flex items-center gap-3">
              <User className="w-5 h-5 text-text-muted" />
              <span>{selectedCase.user.name} ({selectedCase.user.age}세)</span>
            </div>
            <div className="flex items-center gap-3">
              <MapPin className="w-5 h-5 text-text-muted" />
              <span>{selectedCase.user.address}</span>
            </div>
            <div className="flex items-center gap-3">
              <Clock className="w-5 h-5 text-text-muted" />
              <span>{format(selectedCase.createdAt, 'yyyy.MM.dd HH:mm:ss', { locale: ko })}</span>
            </div>
          </div>

          {/* 에스컬레이션 상태 */}
          <div className="bg-bg-secondary rounded-xl p-4 mb-6">
            <h4 className="font-medium mb-3">콜 트리 진행 상황</h4>
            <div className="flex items-center gap-2">
              {[1, 2, 3, 4].map((step) => (
                <div
                  key={step}
                  className={`flex-1 h-2 rounded-full ${
                    step <= selectedCase.escalationStep 
                      ? 'bg-primary' 
                      : 'bg-bg-tertiary'
                  }`}
                />
              ))}
            </div>
            <p className="text-sm text-text-muted mt-2">
              {selectedCase.escalationStep}단계 진행 중
            </p>
          </div>

          {/* 액션 버튼 */}
          {selectedCase.status !== 'resolved' && (
            <div className="space-y-3">
              <button className="w-full bg-secondary hover:bg-secondary/80 text-white font-medium py-3 rounded-xl flex items-center justify-center gap-2">
                <CheckCircle size={18} />
                케이스 해결 처리
              </button>
              <button className="w-full bg-bg-tertiary hover:bg-border text-text-primary font-medium py-3 rounded-xl flex items-center justify-center gap-2">
                <Phone size={18} />
                보호자 연락
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
