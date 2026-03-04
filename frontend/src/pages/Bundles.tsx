import { useState } from 'react'
import { 
  Search, 
  Plus, 
  Copy, 
  Check, 
  AlertTriangle,
  RotateCcw,
  MoreVertical,
  Package,
  Users,
  Cpu,
  ChevronRight,
  FileJson,
  History,
  Shield
} from 'lucide-react'
import { format } from 'date-fns'

// 더미 데이터
const bundles = [
  {
    id: 'bundle-001',
    name: 'default',
    version: '1.2.0',
    status: 'active',
    effectiveFrom: new Date(2026, 1, 15),
    updatedAt: new Date(2026, 2, 1),
    createdBy: '관리자',
    description: '기본 정책 번들',
    usersAffected: 1234,
    devicesAffected: 567,
    thresholdsCount: 15,
    rulesCount: 8,
    plansCount: 3,
    lastValidation: { status: 'ok', errors: 0, warnings: 2 },
    stormRisk: 'low'
  },
  {
    id: 'bundle-002',
    name: 'default',
    version: '1.3.0-draft',
    status: 'draft',
    effectiveFrom: null,
    updatedAt: new Date(2026, 2, 3),
    createdBy: '관리자',
    description: '새로운 임계값 추가',
    usersAffected: 0,
    devicesAffected: 0,
    thresholdsCount: 18,
    rulesCount: 10,
    plansCount: 3,
    lastValidation: { status: 'warning', errors: 0, warnings: 5 },
    stormRisk: 'medium'
  },
  {
    id: 'bundle-003',
    name: 'seoul-region',
    version: '1.0.0',
    status: 'active',
    effectiveFrom: new Date(2026, 0, 10),
    updatedAt: new Date(2026, 1, 20),
    createdBy: '운영자',
    description: '서울 지역 특화 정책',
    usersAffected: 456,
    devicesAffected: 200,
    thresholdsCount: 12,
    rulesCount: 6,
    plansCount: 2,
    lastValidation: { status: 'ok', errors: 0, warnings: 0 },
    stormRisk: 'low'
  },
  {
    id: 'bundle-004',
    name: 'default',
    version: '1.1.0',
    status: 'archived',
    effectiveFrom: new Date(2025, 11, 1),
    updatedAt: new Date(2026, 1, 15),
    createdBy: '관리자',
    description: '이전 버전',
    usersAffected: 0,
    devicesAffected: 0,
    thresholdsCount: 12,
    rulesCount: 6,
    plansCount: 2,
    lastValidation: { status: 'ok', errors: 0, warnings: 1 },
    stormRisk: 'low'
  },
]

const statusConfig: Record<string, { label: string; class: string }> = {
  draft: { label: 'Draft', class: 'badge-warning' },
  active: { label: 'Active', class: 'badge-success' },
  archived: { label: 'Archived', class: 'badge-gray' },
}

const stormRiskConfig: Record<string, { label: string; class: string }> = {
  low: { label: 'Low', class: 'text-success' },
  medium: { label: 'Medium', class: 'text-warning' },
  high: { label: 'High', class: 'text-error' },
}

type TabType = 'overview' | 'policies' | 'diff' | 'validation' | 'history'

export default function Bundles() {
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [selectedBundle, setSelectedBundle] = useState<typeof bundles[0] | null>(bundles[0])
  const [activeTab, setActiveTab] = useState<TabType>('overview')

  const filteredBundles = bundles.filter(bundle => {
    const matchesSearch = bundle.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          bundle.version.includes(searchQuery)
    const matchesStatus = statusFilter === 'all' || bundle.status === statusFilter
    return matchesSearch && matchesStatus
  })

  return (
    <div className="animate-fade-in">
      {/* 페이지 헤더 */}
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Policy Bundles</h1>
        <p className="text-gray-500 mt-1">Create, validate, publish and rollback policy versions</p>
      </div>

      {/* 컨트롤 바 */}
      <div className="flex items-center justify-between mb-6 gap-4">
        <div className="flex items-center gap-3 flex-1">
          <select 
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-36"
          >
            <option value="all">All Status</option>
            <option value="draft">Draft</option>
            <option value="active">Active</option>
            <option value="archived">Archived</option>
          </select>
          
          <div className="input-with-icon flex-1 max-w-xs">
            <Search size={16} className="icon" />
            <input
              type="text"
              placeholder="Search by name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button className="btn btn-secondary">
            <Copy size={16} />
            Clone Active
          </button>
          <button className="btn btn-primary">
            <Plus size={16} />
            Create Draft
          </button>
        </div>
      </div>

      {/* 콘텐츠 그리드 */}
      <div className="grid gap-6" style={{ gridTemplateColumns: '1fr 420px' }}>
        {/* 좌측: 번들 목록 */}
        <div className="card">
          <div className="overflow-x-auto">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Version</th>
                  <th>Status</th>
                  <th>Effective From</th>
                  <th>Updated</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filteredBundles.map((bundle) => (
                  <tr 
                    key={bundle.id}
                    onClick={() => setSelectedBundle(bundle)}
                    className={`cursor-pointer ${selectedBundle?.id === bundle.id ? 'bg-primary-50' : ''}`}
                  >
                    <td>
                      <div className="flex items-center gap-3">
                        <Package size={18} className="text-gray-400" />
                        <span className="font-medium">{bundle.name}</span>
                      </div>
                    </td>
                    <td>
                      <span className="font-mono text-sm">{bundle.version}</span>
                    </td>
                    <td>
                      <span className={`badge ${statusConfig[bundle.status].class}`}>
                        {statusConfig[bundle.status].label}
                      </span>
                    </td>
                    <td className="text-gray-500">
                      {bundle.effectiveFrom ? format(bundle.effectiveFrom, 'yyyy-MM-dd') : '-'}
                    </td>
                    <td className="text-gray-500">
                      {format(bundle.updatedAt, 'MM-dd HH:mm')}
                    </td>
                    <td>
                      <ChevronRight size={16} className="text-gray-400" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* 우측: 상세 패널 */}
        <div className="space-y-4">
          {selectedBundle ? (
            <>
              {/* Bundle Summary Card */}
              <div className="card card-body">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="font-semibold text-lg">{selectedBundle.name}</h3>
                    <p className="text-sm text-gray-500">{selectedBundle.description}</p>
                  </div>
                  <span className={`badge ${statusConfig[selectedBundle.status].class}`}>
                    {statusConfig[selectedBundle.status].label}
                  </span>
                </div>
                
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Version</span>
                    <p className="font-mono font-medium">{selectedBundle.version}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Created by</span>
                    <p className="font-medium">{selectedBundle.createdBy}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Effective From</span>
                    <p className="font-medium">
                      {selectedBundle.effectiveFrom 
                        ? format(selectedBundle.effectiveFrom, 'yyyy-MM-dd')
                        : 'Not deployed'
                      }
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-500">Updated</span>
                    <p className="font-medium">{format(selectedBundle.updatedAt, 'yyyy-MM-dd HH:mm')}</p>
                  </div>
                </div>
              </div>

              {/* Quick Health Card */}
              <div className="card card-body">
                <h4 className="font-medium mb-3">Quick Health</h4>
                
                <div className="flex items-center gap-3 mb-3">
                  {selectedBundle.lastValidation.status === 'ok' ? (
                    <Check size={18} className="text-success" />
                  ) : (
                    <AlertTriangle size={18} className="text-warning" />
                  )}
                  <span className="text-sm">
                    Last Validation: {' '}
                    {selectedBundle.lastValidation.errors > 0 && (
                      <span className="text-error">{selectedBundle.lastValidation.errors} Errors</span>
                    )}
                    {selectedBundle.lastValidation.warnings > 0 && (
                      <span className="text-warning ml-2">{selectedBundle.lastValidation.warnings} Warnings</span>
                    )}
                    {selectedBundle.lastValidation.errors === 0 && selectedBundle.lastValidation.warnings === 0 && (
                      <span className="text-success">OK</span>
                    )}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <Shield size={16} className="text-gray-400" />
                  <span className="text-sm text-gray-500">Storm Risk:</span>
                  <span className={`text-sm font-medium ${stormRiskConfig[selectedBundle.stormRisk].class}`}>
                    {stormRiskConfig[selectedBundle.stormRisk].label}
                  </span>
                </div>
              </div>

              {/* Scope Coverage Card */}
              <div className="card card-body">
                <h4 className="font-medium mb-3">Scope Coverage</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-info-50 flex items-center justify-center">
                      <Users size={18} className="text-info" />
                    </div>
                    <div>
                      <p className="text-xl font-semibold">{selectedBundle.usersAffected.toLocaleString()}</p>
                      <p className="text-xs text-gray-500">Users affected</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-info-50 flex items-center justify-center">
                      <Cpu size={18} className="text-info" />
                    </div>
                    <div>
                      <p className="text-xl font-semibold">{selectedBundle.devicesAffected.toLocaleString()}</p>
                      <p className="text-xs text-gray-500">Devices affected</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Quick Actions Card */}
              <div className="card card-body">
                <h4 className="font-medium mb-3">Quick Actions</h4>
                <div className="space-y-2">
                  <button className="btn btn-secondary w-full justify-start">
                    <Check size={16} />
                    Validate
                  </button>
                  {selectedBundle.status === 'draft' && (
                    <button className="btn btn-primary w-full justify-start">
                      <Package size={16} />
                      Publish
                    </button>
                  )}
                  <button className="btn btn-secondary w-full justify-start">
                    <FileJson size={16} />
                    View Diff
                  </button>
                  {selectedBundle.status === 'active' && (
                    <button className="btn btn-danger w-full justify-start">
                      <RotateCcw size={16} />
                      Rollback
                    </button>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="card card-body empty-state">
              <Package size={48} className="mb-4" />
              <p>Select a bundle to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
