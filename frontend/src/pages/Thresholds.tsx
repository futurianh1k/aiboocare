import { useState } from 'react'
import { 
  Search, 
  Plus, 
  Download,
  Upload,
  X,
  Save,
  Gauge,
  MoreVertical,
  Copy,
  Power
} from 'lucide-react'

// 더미 데이터
const thresholds = [
  {
    key: 'vitals.spo2.low',
    domain: 'VITALS',
    metric: 'spo2',
    operator: '<',
    value: 92,
    durationSec: 60,
    occurrences: 3,
    severity: 'CRITICAL',
    enabled: true,
    updatedAt: '2026-03-01'
  },
  {
    key: 'vitals.heart_rate.high',
    domain: 'VITALS',
    metric: 'heart_rate',
    operator: '>',
    value: 120,
    durationSec: 300,
    occurrences: 5,
    severity: 'ALERT',
    enabled: true,
    updatedAt: '2026-02-28'
  },
  {
    key: 'vitals.heart_rate.low',
    domain: 'VITALS',
    metric: 'heart_rate',
    operator: '<',
    value: 50,
    durationSec: 120,
    occurrences: 3,
    severity: 'ALERT',
    enabled: true,
    updatedAt: '2026-02-28'
  },
  {
    key: 'fall.impact.high',
    domain: 'FALL',
    metric: 'impact_g',
    operator: '>',
    value: 2.5,
    durationSec: 0,
    occurrences: 1,
    severity: 'CRITICAL',
    enabled: true,
    updatedAt: '2026-02-25'
  },
  {
    key: 'inactivity.duration.long',
    domain: 'INACTIVITY',
    metric: 'no_motion_sec',
    operator: '>',
    value: 7200,
    durationSec: 0,
    occurrences: 1,
    severity: 'WARNING',
    enabled: true,
    updatedAt: '2026-02-20'
  },
  {
    key: 'env.temperature.high',
    domain: 'ENV',
    metric: 'temperature_c',
    operator: '>',
    value: 35,
    durationSec: 600,
    occurrences: 2,
    severity: 'WARNING',
    enabled: false,
    updatedAt: '2026-02-15'
  },
]

const severityConfig: Record<string, string> = {
  CRITICAL: 'badge-error',
  ALERT: 'badge-warning',
  WARNING: 'badge-info',
  INFO: 'badge-gray',
}

const domainConfig: Record<string, string> = {
  VITALS: 'badge-error',
  FALL: 'badge-warning',
  INACTIVITY: 'badge-info',
  ENV: 'badge-gray',
}

export default function Thresholds() {
  const [searchQuery, setSearchQuery] = useState('')
  const [domainFilter, setDomainFilter] = useState('all')
  const [severityFilter, setSeverityFilter] = useState('all')
  const [enabledFilter, setEnabledFilter] = useState('all')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selectedThreshold, setSelectedThreshold] = useState<typeof thresholds[0] | null>(null)

  const filteredThresholds = thresholds.filter(t => {
    const matchesSearch = t.key.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          t.metric.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesDomain = domainFilter === 'all' || t.domain === domainFilter
    const matchesSeverity = severityFilter === 'all' || t.severity === severityFilter
    const matchesEnabled = enabledFilter === 'all' || 
                           (enabledFilter === 'enabled' && t.enabled) ||
                           (enabledFilter === 'disabled' && !t.enabled)
    return matchesSearch && matchesDomain && matchesSeverity && matchesEnabled
  })

  const openEditDrawer = (threshold: typeof thresholds[0]) => {
    setSelectedThreshold(threshold)
    setDrawerOpen(true)
  }

  const openNewDrawer = () => {
    setSelectedThreshold(null)
    setDrawerOpen(true)
  }

  return (
    <div className="animate-fade-in">
      {/* 페이지 헤더 */}
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Thresholds</h1>
        <p className="text-gray-500 mt-1">Edit measurement thresholds and derived metric triggers</p>
      </div>

      {/* 컨트롤 바 */}
      <div className="flex items-center justify-between mb-6 gap-4 flex-wrap">
        <div className="flex items-center gap-3 flex-wrap">
          <select 
            value={domainFilter}
            onChange={(e) => setDomainFilter(e.target.value)}
            className="w-32"
          >
            <option value="all">All Domain</option>
            <option value="VITALS">VITALS</option>
            <option value="FALL">FALL</option>
            <option value="INACTIVITY">INACTIVITY</option>
            <option value="ENV">ENV</option>
          </select>

          <select 
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="w-32"
          >
            <option value="all">All Severity</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="ALERT">ALERT</option>
            <option value="WARNING">WARNING</option>
            <option value="INFO">INFO</option>
          </select>

          <select 
            value={enabledFilter}
            onChange={(e) => setEnabledFilter(e.target.value)}
            className="w-32"
          >
            <option value="all">All</option>
            <option value="enabled">Enabled</option>
            <option value="disabled">Disabled</option>
          </select>
          
          <div className="input-with-icon">
            <Search size={16} className="icon" />
            <input
              type="text"
              placeholder="Search key or metric..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ width: '200px' }}
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button className="btn btn-secondary btn-sm">
            <Upload size={16} />
            Import
          </button>
          <button className="btn btn-secondary btn-sm">
            <Download size={16} />
            Export
          </button>
          <button className="btn btn-primary" onClick={openNewDrawer}>
            <Plus size={16} />
            New Threshold
          </button>
        </div>
      </div>

      {/* 테이블 */}
      <div className="card">
        <div className="overflow-x-auto">
          <table>
            <thead>
              <tr>
                <th>Key</th>
                <th>Domain</th>
                <th>Metric</th>
                <th>Condition</th>
                <th>Duration/Occ</th>
                <th>Severity</th>
                <th>Enabled</th>
                <th>Updated</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filteredThresholds.map((threshold) => (
                <tr 
                  key={threshold.key}
                  className="cursor-pointer"
                  onClick={() => openEditDrawer(threshold)}
                >
                  <td>
                    <span className="font-mono text-sm text-primary">{threshold.key}</span>
                  </td>
                  <td>
                    <span className={`badge ${domainConfig[threshold.domain]}`}>
                      {threshold.domain}
                    </span>
                  </td>
                  <td className="font-mono text-sm">{threshold.metric}</td>
                  <td className="font-mono text-sm">
                    {threshold.operator} {threshold.value}
                  </td>
                  <td className="text-sm text-gray-500">
                    {threshold.durationSec > 0 ? `${threshold.durationSec}s` : '-'} / {threshold.occurrences}x
                  </td>
                  <td>
                    <span className={`badge ${severityConfig[threshold.severity]}`}>
                      {threshold.severity}
                    </span>
                  </td>
                  <td>
                    <div className={`status-dot ${threshold.enabled ? 'active' : 'inactive'}`}></div>
                  </td>
                  <td className="text-gray-500 text-sm">{threshold.updatedAt}</td>
                  <td>
                    <button 
                      className="btn btn-ghost btn-sm p-1"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <MoreVertical size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Drawer */}
      {drawerOpen && (
        <>
          <div className="drawer-overlay" onClick={() => setDrawerOpen(false)}></div>
          <div className="drawer animate-slide-in">
            <div className="drawer-header">
              <h3 className="font-semibold">
                {selectedThreshold ? 'Edit Threshold' : 'New Threshold'}
              </h3>
              <button 
                className="btn btn-ghost btn-sm p-1"
                onClick={() => setDrawerOpen(false)}
              >
                <X size={20} />
              </button>
            </div>
            
            <div className="drawer-body space-y-6">
              {/* Identity Section */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-3">Identity</h4>
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm text-gray-500 mb-1">Key</label>
                    <input 
                      type="text" 
                      defaultValue={selectedThreshold?.key || ''}
                      placeholder="e.g., vitals.spo2.low"
                      className="w-full font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-500 mb-1">Domain</label>
                    <select defaultValue={selectedThreshold?.domain || ''} className="w-full">
                      <option value="">Select domain</option>
                      <option value="VITALS">VITALS</option>
                      <option value="FALL">FALL</option>
                      <option value="INACTIVITY">INACTIVITY</option>
                      <option value="ENV">ENV</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-500 mb-1">Metric</label>
                    <select defaultValue={selectedThreshold?.metric || ''} className="w-full">
                      <option value="">Select metric</option>
                      <option value="spo2">spo2</option>
                      <option value="heart_rate">heart_rate</option>
                      <option value="impact_g">impact_g</option>
                      <option value="no_motion_sec">no_motion_sec</option>
                      <option value="temperature_c">temperature_c</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Condition Section */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-3">Condition</h4>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm text-gray-500 mb-1">Operator</label>
                    <select defaultValue={selectedThreshold?.operator || ''} className="w-full">
                      <option value="<">&lt;</option>
                      <option value="<=">&lt;=</option>
                      <option value=">">&gt;</option>
                      <option value=">=">&gt;=</option>
                      <option value="==">==</option>
                      <option value="between">between</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-500 mb-1">Value</label>
                    <input 
                      type="number" 
                      defaultValue={selectedThreshold?.value || ''}
                      className="w-full"
                    />
                  </div>
                </div>
              </div>

              {/* Aggregation Section */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-3">Aggregation</h4>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm text-gray-500 mb-1">Duration (sec)</label>
                    <input 
                      type="number" 
                      defaultValue={selectedThreshold?.durationSec || 0}
                      className="w-full"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-500 mb-1">Occurrences</label>
                    <input 
                      type="number" 
                      defaultValue={selectedThreshold?.occurrences || 1}
                      className="w-full"
                    />
                  </div>
                </div>
              </div>

              {/* Outcome Section */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-3">Outcome</h4>
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm text-gray-500 mb-1">Severity</label>
                    <select defaultValue={selectedThreshold?.severity || ''} className="w-full">
                      <option value="CRITICAL">CRITICAL</option>
                      <option value="ALERT">ALERT</option>
                      <option value="WARNING">WARNING</option>
                      <option value="INFO">INFO</option>
                    </select>
                  </div>
                  <div className="flex items-center justify-between py-2">
                    <span className="text-sm text-gray-700">Enabled</span>
                    <div className={`toggle ${selectedThreshold?.enabled !== false ? 'active' : ''}`}></div>
                  </div>
                </div>
              </div>

              {/* Validation Panel */}
              <div className="p-3 bg-success-50 rounded-lg border border-success-100">
                <div className="flex items-center gap-2 text-success text-sm">
                  <Gauge size={16} />
                  <span>Validation: OK</span>
                </div>
              </div>
            </div>

            <div className="drawer-footer">
              <button className="btn btn-secondary" onClick={() => setDrawerOpen(false)}>
                Cancel
              </button>
              <button className="btn btn-primary">
                <Save size={16} />
                Save
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
