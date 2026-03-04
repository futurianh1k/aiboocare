import { useState } from 'react'
import { 
  Search, 
  Download,
  FileText,
  Calendar,
  User,
  Eye,
  X,
  ChevronRight,
  Edit,
  Trash2,
  Upload,
  Play,
  RotateCcw,
  Plus
} from 'lucide-react'
import { format } from 'date-fns'

// 더미 데이터
const auditLogs = [
  {
    id: 'audit-001',
    timestamp: new Date(2026, 2, 4, 14, 23, 45),
    actor: '관리자',
    actorRole: 'admin',
    action: 'WRITE',
    resourceType: 'threshold',
    resourceId: 'vitals.spo2.low',
    detail: 'Updated value from 90 to 92',
    diff: {
      before: { value: 90, durationSec: 60 },
      after: { value: 92, durationSec: 60 }
    }
  },
  {
    id: 'audit-002',
    timestamp: new Date(2026, 2, 4, 11, 15, 20),
    actor: '관리자',
    actorRole: 'admin',
    action: 'PUBLISH',
    resourceType: 'bundle',
    resourceId: 'default v1.2.0',
    detail: 'Published bundle to production',
    diff: null
  },
  {
    id: 'audit-003',
    timestamp: new Date(2026, 2, 3, 16, 45, 10),
    actor: '운영자',
    actorRole: 'operator',
    action: 'WRITE',
    resourceType: 'rule',
    resourceId: 'ems.fall_critical',
    detail: 'Enabled rule',
    diff: {
      before: { enabled: false },
      after: { enabled: true }
    }
  },
  {
    id: 'audit-004',
    timestamp: new Date(2026, 2, 3, 10, 30, 0),
    actor: '관리자',
    actorRole: 'admin',
    action: 'DELETE',
    resourceType: 'threshold',
    resourceId: 'env.humidity.high',
    detail: 'Removed unused threshold',
    diff: null
  },
  {
    id: 'audit-005',
    timestamp: new Date(2026, 2, 2, 9, 20, 15),
    actor: '관리자',
    actorRole: 'admin',
    action: 'ROLLBACK',
    resourceType: 'bundle',
    resourceId: 'default v1.1.0',
    detail: 'Rolled back to previous version',
    diff: null
  },
  {
    id: 'audit-006',
    timestamp: new Date(2026, 2, 1, 15, 45, 30),
    actor: '관리자',
    actorRole: 'admin',
    action: 'WRITE',
    resourceType: 'plan',
    resourceId: 'default_escalation',
    detail: 'Added new stage',
    diff: {
      before: { stageCount: 4 },
      after: { stageCount: 5 }
    }
  },
  {
    id: 'audit-007',
    timestamp: new Date(2026, 2, 1, 11, 10, 0),
    actor: '운영자',
    actorRole: 'operator',
    action: 'READ',
    resourceType: 'bundle',
    resourceId: 'default v1.2.0',
    detail: 'Viewed bundle details',
    diff: null
  },
]

const actionConfig: Record<string, { label: string; class: string; icon: any }> = {
  READ: { label: 'READ', class: 'badge-info', icon: Eye },
  WRITE: { label: 'WRITE', class: 'badge-warning', icon: Edit },
  PUBLISH: { label: 'PUBLISH', class: 'badge-success', icon: Upload },
  ROLLBACK: { label: 'ROLLBACK', class: 'badge-error', icon: RotateCcw },
  DELETE: { label: 'DELETE', class: 'badge-error', icon: Trash2 },
}

const resourceTypeConfig: Record<string, string> = {
  bundle: 'badge-primary',
  threshold: 'badge-warning',
  rule: 'badge-info',
  plan: 'badge-success',
  binding: 'badge-gray',
}

export default function Audit() {
  const [searchQuery, setSearchQuery] = useState('')
  const [actionFilter, setActionFilter] = useState('all')
  const [resourceFilter, setResourceFilter] = useState('all')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selectedLog, setSelectedLog] = useState<typeof auditLogs[0] | null>(null)

  const filteredLogs = auditLogs.filter(log => {
    const matchesSearch = log.resourceId.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          log.actor.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesAction = actionFilter === 'all' || log.action === actionFilter
    const matchesResource = resourceFilter === 'all' || log.resourceType === resourceFilter
    return matchesSearch && matchesAction && matchesResource
  })

  const openDetailDrawer = (log: typeof auditLogs[0]) => {
    setSelectedLog(log)
    setDrawerOpen(true)
  }

  return (
    <div className="animate-fade-in">
      {/* 페이지 헤더 */}
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Audit</h1>
        <p className="text-gray-500 mt-1">Track all policy changes and user actions</p>
      </div>

      {/* 필터 바 */}
      <div className="card card-body mb-6">
        <div className="flex items-center gap-4 flex-wrap">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Date Range</label>
            <div className="flex items-center gap-2">
              <input 
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="w-36 text-sm"
              />
              <span className="text-gray-400">~</span>
              <input 
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="w-36 text-sm"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1">Actor</label>
            <div className="input-with-icon">
              <User size={14} className="icon" />
              <input
                type="text"
                placeholder="Search actor..."
                className="w-40 text-sm"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1">Action</label>
            <select 
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="w-32"
            >
              <option value="all">All</option>
              <option value="READ">READ</option>
              <option value="WRITE">WRITE</option>
              <option value="PUBLISH">PUBLISH</option>
              <option value="ROLLBACK">ROLLBACK</option>
              <option value="DELETE">DELETE</option>
            </select>
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1">Resource</label>
            <select 
              value={resourceFilter}
              onChange={(e) => setResourceFilter(e.target.value)}
              className="w-32"
            >
              <option value="all">All</option>
              <option value="bundle">bundle</option>
              <option value="threshold">threshold</option>
              <option value="rule">rule</option>
              <option value="plan">plan</option>
              <option value="binding">binding</option>
            </select>
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1">Search</label>
            <div className="input-with-icon">
              <Search size={14} className="icon" />
              <input
                type="text"
                placeholder="Resource ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-40 text-sm"
              />
            </div>
          </div>

          <div className="ml-auto pt-4">
            <button className="btn btn-secondary btn-sm">
              <Download size={16} />
              Export
            </button>
          </div>
        </div>
      </div>

      {/* 테이블 */}
      <div className="card">
        <div className="overflow-x-auto">
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Actor</th>
                <th>Action</th>
                <th>Resource</th>
                <th>Resource ID</th>
                <th>Detail</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.map((log) => {
                const ActionIcon = actionConfig[log.action].icon
                return (
                  <tr 
                    key={log.id}
                    className="cursor-pointer"
                    onClick={() => openDetailDrawer(log)}
                  >
                    <td className="text-sm font-mono text-gray-500">
                      {format(log.timestamp, 'MM-dd HH:mm:ss')}
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center text-xs font-medium">
                          {log.actor.charAt(0)}
                        </div>
                        <span className="text-sm">{log.actor}</span>
                      </div>
                    </td>
                    <td>
                      <span className={`badge ${actionConfig[log.action].class}`}>
                        <ActionIcon size={12} className="mr-1" />
                        {actionConfig[log.action].label}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${resourceTypeConfig[log.resourceType]}`}>
                        {log.resourceType}
                      </span>
                    </td>
                    <td>
                      <span className="font-mono text-sm text-primary">{log.resourceId}</span>
                    </td>
                    <td className="text-sm text-gray-500 max-w-xs truncate">
                      {log.detail}
                    </td>
                    <td>
                      <ChevronRight size={16} className="text-gray-400" />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Drawer */}
      {drawerOpen && selectedLog && (
        <>
          <div className="drawer-overlay" onClick={() => setDrawerOpen(false)}></div>
          <div className="drawer animate-slide-in" style={{ width: '480px' }}>
            <div className="drawer-header">
              <h3 className="font-semibold">Audit Detail</h3>
              <button 
                className="btn btn-ghost btn-sm p-1"
                onClick={() => setDrawerOpen(false)}
              >
                <X size={20} />
              </button>
            </div>
            
            <div className="drawer-body space-y-6">
              {/* Basic Info */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-3">Basic Info</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Timestamp</span>
                    <p className="font-mono">{format(selectedLog.timestamp, 'yyyy-MM-dd HH:mm:ss')}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Actor</span>
                    <p className="font-medium">{selectedLog.actor}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Role</span>
                    <p>{selectedLog.actorRole}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Action</span>
                    <p>
                      <span className={`badge ${actionConfig[selectedLog.action].class}`}>
                        {selectedLog.action}
                      </span>
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-500">Resource Type</span>
                    <p>
                      <span className={`badge ${resourceTypeConfig[selectedLog.resourceType]}`}>
                        {selectedLog.resourceType}
                      </span>
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-500">Resource ID</span>
                    <p className="font-mono text-primary">{selectedLog.resourceId}</p>
                  </div>
                </div>
              </div>

              {/* Detail */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-3">Detail</h4>
                <p className="text-sm text-gray-600 p-3 bg-gray-50 rounded-lg">
                  {selectedLog.detail}
                </p>
              </div>

              {/* Diff View */}
              {selectedLog.diff && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-3">Changes</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs text-gray-500 mb-2">Before</p>
                      <pre className="p-3 bg-error-50 rounded-lg text-sm font-mono overflow-x-auto">
                        {JSON.stringify(selectedLog.diff.before, null, 2)}
                      </pre>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 mb-2">After</p>
                      <pre className="p-3 bg-success-50 rounded-lg text-sm font-mono overflow-x-auto">
                        {JSON.stringify(selectedLog.diff.after, null, 2)}
                      </pre>
                    </div>
                  </div>
                </div>
              )}

              {/* Raw Detail JSON */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-3">Raw Data</h4>
                <pre className="p-3 bg-gray-50 rounded-lg text-xs font-mono overflow-x-auto max-h-48">
                  {JSON.stringify(selectedLog, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
