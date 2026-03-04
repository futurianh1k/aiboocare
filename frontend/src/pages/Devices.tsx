import { useState } from 'react'
import { Search, Filter, Cpu, Wifi, WifiOff, Battery, Signal, MoreVertical, RefreshCw } from 'lucide-react'

// 더미 데이터
const devices = [
  { 
    id: 'ESP32-001', 
    model: 'ESP32-S3',
    user: '김영희',
    status: 'active',
    firmware: '1.2.3',
    lastHeartbeat: '방금 전',
    battery: 85,
    rssi: -45,
    sensors: { spo2: 'ok', imu: 'ok', mic: 'ok' }
  },
  { 
    id: 'ESP32-002', 
    model: 'ESP32-S3',
    user: '이철수',
    status: 'active',
    firmware: '1.2.3',
    lastHeartbeat: '1분 전',
    battery: 72,
    rssi: -55,
    sensors: { spo2: 'ok', imu: 'ok', mic: 'ok' }
  },
  { 
    id: 'RPi-001', 
    model: 'Raspberry Pi 4',
    user: '박민수',
    status: 'active',
    firmware: '2.0.1',
    lastHeartbeat: '30초 전',
    battery: null,
    rssi: -40,
    sensors: { camera: 'ok', radar: 'ok' }
  },
  { 
    id: 'ESP32-003', 
    model: 'ESP32-S3',
    user: null,
    status: 'inactive',
    firmware: '1.2.0',
    lastHeartbeat: '3시간 전',
    battery: 23,
    rssi: null,
    sensors: { spo2: 'error', imu: 'ok', mic: 'ok' }
  },
  { 
    id: 'ESP32-004', 
    model: 'ESP32-S3',
    user: '최순자',
    status: 'offline',
    firmware: '1.1.0',
    lastHeartbeat: '2일 전',
    battery: null,
    rssi: null,
    sensors: {}
  },
]

const statusConfig: Record<string, { label: string; color: string; bg: string }> = {
  active: { label: '온라인', color: 'text-secondary', bg: 'bg-secondary' },
  inactive: { label: '비활성', color: 'text-warning', bg: 'bg-warning' },
  offline: { label: '오프라인', color: 'text-text-muted', bg: 'bg-text-muted' },
}

function getRssiLevel(rssi: number | null): { label: string; bars: number } {
  if (rssi === null) return { label: '없음', bars: 0 }
  if (rssi > -50) return { label: '매우 좋음', bars: 4 }
  if (rssi > -60) return { label: '좋음', bars: 3 }
  if (rssi > -70) return { label: '보통', bars: 2 }
  return { label: '약함', bars: 1 }
}

function getBatteryColor(battery: number | null): string {
  if (battery === null) return 'text-text-muted'
  if (battery > 60) return 'text-secondary'
  if (battery > 30) return 'text-warning'
  return 'text-danger'
}

export default function Devices() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedStatus, setSelectedStatus] = useState('all')

  const filteredDevices = devices.filter(device => {
    const matchesSearch = device.id.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          device.user?.includes(searchQuery)
    const matchesStatus = selectedStatus === 'all' || device.status === selectedStatus
    return matchesSearch && matchesStatus
  })

  const stats = {
    total: devices.length,
    active: devices.filter(d => d.status === 'active').length,
    inactive: devices.filter(d => d.status === 'inactive').length,
    offline: devices.filter(d => d.status === 'offline').length,
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">디바이스</h1>
          <p className="text-text-secondary">등록된 IoT 디바이스를 관리합니다.</p>
        </div>
        <button className="bg-primary hover:bg-primary-dark text-white font-medium py-2.5 px-4 rounded-xl flex items-center gap-2">
          <RefreshCw size={18} />
          새로고침
        </button>
      </div>

      {/* 상태 요약 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-bg-card rounded-xl p-4 border border-border">
          <p className="text-text-muted text-sm">전체</p>
          <p className="text-2xl font-bold">{stats.total}</p>
        </div>
        <div className="bg-bg-card rounded-xl p-4 border border-border">
          <p className="text-secondary text-sm">온라인</p>
          <p className="text-2xl font-bold text-secondary">{stats.active}</p>
        </div>
        <div className="bg-bg-card rounded-xl p-4 border border-border">
          <p className="text-warning text-sm">비활성</p>
          <p className="text-2xl font-bold text-warning">{stats.inactive}</p>
        </div>
        <div className="bg-bg-card rounded-xl p-4 border border-border">
          <p className="text-text-muted text-sm">오프라인</p>
          <p className="text-2xl font-bold">{stats.offline}</p>
        </div>
      </div>

      {/* 필터 */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
          <input
            type="text"
            placeholder="디바이스 ID 또는 사용자로 검색..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-12"
          />
        </div>
        <select 
          value={selectedStatus}
          onChange={(e) => setSelectedStatus(e.target.value)}
          className="px-4 py-2 rounded-xl"
        >
          <option value="all">전체 상태</option>
          <option value="active">온라인</option>
          <option value="inactive">비활성</option>
          <option value="offline">오프라인</option>
        </select>
      </div>

      {/* 디바이스 테이블 */}
      <div className="bg-bg-card rounded-2xl border border-border overflow-hidden">
        <div className="overflow-x-auto">
          <table>
            <thead>
              <tr>
                <th>디바이스</th>
                <th>사용자</th>
                <th>상태</th>
                <th>펌웨어</th>
                <th>배터리</th>
                <th>신호</th>
                <th>마지막 통신</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filteredDevices.map((device) => {
                const rssiInfo = getRssiLevel(device.rssi)
                const status = statusConfig[device.status]
                
                return (
                  <tr key={device.id}>
                    <td>
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-bg-tertiary rounded-lg">
                          <Cpu className="w-5 h-5 text-primary" />
                        </div>
                        <div>
                          <p className="font-mono font-medium">{device.id}</p>
                          <p className="text-sm text-text-muted">{device.model}</p>
                        </div>
                      </div>
                    </td>
                    <td>
                      {device.user ? (
                        <span>{device.user}</span>
                      ) : (
                        <span className="text-text-muted">미할당</span>
                      )}
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${status.bg}`}></span>
                        <span className={status.color}>{status.label}</span>
                      </div>
                    </td>
                    <td>
                      <span className="font-mono text-sm">{device.firmware}</span>
                    </td>
                    <td>
                      {device.battery !== null ? (
                        <div className="flex items-center gap-2">
                          <Battery className={`w-4 h-4 ${getBatteryColor(device.battery)}`} />
                          <span className={getBatteryColor(device.battery)}>{device.battery}%</span>
                        </div>
                      ) : (
                        <span className="text-text-muted">-</span>
                      )}
                    </td>
                    <td>
                      <div className="flex items-center gap-1">
                        {device.status === 'active' ? (
                          <Wifi className="w-4 h-4 text-secondary" />
                        ) : (
                          <WifiOff className="w-4 h-4 text-text-muted" />
                        )}
                        <div className="flex gap-0.5">
                          {[1, 2, 3, 4].map((bar) => (
                            <div
                              key={bar}
                              className={`w-1 rounded-sm ${
                                bar <= rssiInfo.bars ? 'bg-secondary' : 'bg-bg-tertiary'
                              }`}
                              style={{ height: `${bar * 4}px` }}
                            />
                          ))}
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="text-text-secondary">{device.lastHeartbeat}</span>
                    </td>
                    <td>
                      <button className="p-2 hover:bg-bg-tertiary rounded-lg">
                        <MoreVertical size={16} className="text-text-muted" />
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
