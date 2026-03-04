import { useState } from 'react'
import { Search, Plus, Filter, MoreVertical, User, Phone, MapPin, Heart } from 'lucide-react'

// 더미 데이터
const careUsers = [
  { 
    id: 'USR-001', 
    name: '김영희', 
    age: 78, 
    address: '서울시 강남구', 
    phone: '010-1234-5678',
    status: 'active',
    device: 'ESP32-001',
    lastActivity: '방금 전',
    guardians: 2
  },
  { 
    id: 'USR-002', 
    name: '이철수', 
    age: 82, 
    address: '서울시 서초구', 
    phone: '010-2345-6789',
    status: 'warning',
    device: 'ESP32-002',
    lastActivity: '30분 전',
    guardians: 1
  },
  { 
    id: 'USR-003', 
    name: '박민수', 
    age: 75, 
    address: '서울시 송파구', 
    phone: '010-3456-7890',
    status: 'active',
    device: 'RPi-001',
    lastActivity: '5분 전',
    guardians: 3
  },
  { 
    id: 'USR-004', 
    name: '최순자', 
    age: 80, 
    address: '서울시 강동구', 
    phone: '010-4567-8901',
    status: 'inactive',
    device: null,
    lastActivity: '2시간 전',
    guardians: 2
  },
]

const statusConfig: Record<string, { label: string; color: string; bg: string }> = {
  active: { label: '정상', color: 'text-secondary', bg: 'bg-secondary/20' },
  warning: { label: '주의', color: 'text-warning', bg: 'bg-warning/20' },
  inactive: { label: '오프라인', color: 'text-text-muted', bg: 'bg-bg-tertiary' },
}

export default function CareUsers() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedStatus, setSelectedStatus] = useState('all')

  const filteredUsers = careUsers.filter(user => {
    const matchesSearch = user.name.includes(searchQuery) || user.id.includes(searchQuery)
    const matchesStatus = selectedStatus === 'all' || user.status === selectedStatus
    return matchesSearch && matchesStatus
  })

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">돌봄 대상자</h1>
          <p className="text-text-secondary">등록된 돌봄 대상자를 관리합니다.</p>
        </div>
        <button className="bg-primary hover:bg-primary-dark text-white font-medium py-2.5 px-4 rounded-xl flex items-center gap-2">
          <Plus size={18} />
          대상자 등록
        </button>
      </div>

      {/* 필터 영역 */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
          <input
            type="text"
            placeholder="이름 또는 ID로 검색..."
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
            <option value="active">정상</option>
            <option value="warning">주의</option>
            <option value="inactive">오프라인</option>
          </select>
          <button className="p-3 bg-bg-secondary hover:bg-bg-tertiary border border-border rounded-xl">
            <Filter size={18} />
          </button>
        </div>
      </div>

      {/* 유저 그리드 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredUsers.map((user) => (
          <div 
            key={user.id}
            className="bg-bg-card rounded-2xl border border-border hover:border-border-light transition-all hover:shadow-lg cursor-pointer"
          >
            <div className="p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center">
                    <User className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h3 className="font-semibold">{user.name}</h3>
                    <p className="text-sm text-text-muted">{user.id}</p>
                  </div>
                </div>
                <button className="p-2 hover:bg-bg-tertiary rounded-lg">
                  <MoreVertical size={18} className="text-text-muted" />
                </button>
              </div>

              <div className="space-y-3">
                <div className="flex items-center gap-2 text-text-secondary">
                  <Heart size={16} />
                  <span className="text-sm">{user.age}세</span>
                </div>
                <div className="flex items-center gap-2 text-text-secondary">
                  <MapPin size={16} />
                  <span className="text-sm">{user.address}</span>
                </div>
                <div className="flex items-center gap-2 text-text-secondary">
                  <Phone size={16} />
                  <span className="text-sm">{user.phone}</span>
                </div>
              </div>
            </div>

            <div className="border-t border-border px-6 py-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${statusConfig[user.status].bg} ${statusConfig[user.status].color}`}>
                  {statusConfig[user.status].label}
                </span>
                {user.device && (
                  <span className="text-xs text-text-muted">
                    {user.device}
                  </span>
                )}
              </div>
              <span className="text-xs text-text-muted">
                {user.lastActivity}
              </span>
            </div>
          </div>
        ))}
      </div>

      {filteredUsers.length === 0 && (
        <div className="text-center py-12">
          <User className="w-12 h-12 text-text-muted mx-auto mb-4" />
          <p className="text-text-secondary">검색 결과가 없습니다.</p>
        </div>
      )}
    </div>
  )
}
