import { useState } from 'react'
import { 
  Search, 
  Plus, 
  Download,
  Upload,
  FileCode,
  Code,
  GitMerge,
  X,
  Save,
  AlertTriangle,
  Check
} from 'lucide-react'

// 더미 데이터
const rules = [
  {
    key: 'ems.fall_critical',
    domain: 'EMS',
    priority: 100,
    scope: 'cloud',
    enabled: true,
    description: '낙상 위험 시 즉시 119 호출',
    updatedAt: '2026-03-01',
    conditions: { type: 'event_type', value: 'fall', operator: '==' },
    action: { type: 'contact_ems', plan_name: 'critical_emergency' }
  },
  {
    key: 'verify.device_offline',
    domain: 'VERIFY',
    priority: 90,
    scope: 'cloud',
    enabled: true,
    description: '디바이스 오프라인 확인',
    updatedAt: '2026-02-28',
    conditions: { type: 'device_status', value: 'offline', operator: '==' },
    action: { type: 'open_or_merge_case', severity: 'ALERT' }
  },
  {
    key: 'escalation.no_response',
    domain: 'ESCALATION',
    priority: 80,
    scope: 'cloud',
    enabled: true,
    description: '응답 없음 시 다음 단계 에스컬레이션',
    updatedAt: '2026-02-25',
    conditions: { type: 'no_response', duration_sec: 300 },
    action: { type: 'escalate_next', plan_name: 'default_escalation' }
  },
  {
    key: 'voice.emergency_keyword',
    domain: 'VOICE',
    priority: 95,
    scope: 'edge',
    enabled: true,
    description: '응급 키워드 감지',
    updatedAt: '2026-02-20',
    conditions: { type: 'voice_keyword', keywords: ['살려줘', '도와줘', '응급'] },
    action: { type: 'create_alert', severity: 'CRITICAL' }
  },
  {
    key: 'ems.spo2_critical',
    domain: 'EMS',
    priority: 100,
    scope: 'cloud',
    enabled: false,
    description: 'SpO2 위험 수준 시 응급 호출',
    updatedAt: '2026-02-15',
    conditions: { type: 'measurement', metric: 'spo2', operator: '<', value: 85 },
    action: { type: 'contact_ems', plan_name: 'critical_emergency' }
  },
]

const domainConfig: Record<string, { label: string; class: string }> = {
  EMS: { label: 'EMS', class: 'badge-error' },
  VERIFY: { label: 'VERIFY', class: 'badge-info' },
  ESCALATION: { label: 'ESCALATION', class: 'badge-warning' },
  VOICE: { label: 'VOICE', class: 'badge-success' },
}

const scopeConfig: Record<string, { label: string; class: string }> = {
  edge: { label: 'Edge', class: 'badge-gray' },
  cloud: { label: 'Cloud', class: 'badge-primary' },
  both: { label: 'Both', class: 'badge-info' },
}

export default function Rules() {
  const [searchQuery, setSearchQuery] = useState('')
  const [domainFilter, setDomainFilter] = useState('all')
  const [scopeFilter, setScopeFilter] = useState('all')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selectedRule, setSelectedRule] = useState<typeof rules[0] | null>(null)
  const [editorMode, setEditorMode] = useState<'builder' | 'json'>('builder')

  const filteredRules = rules.filter(r => {
    const matchesSearch = r.key.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesDomain = domainFilter === 'all' || r.domain === domainFilter
    const matchesScope = scopeFilter === 'all' || r.scope === scopeFilter
    return matchesSearch && matchesDomain && matchesScope
  })

  const openEditDrawer = (rule: typeof rules[0]) => {
    setSelectedRule(rule)
    setDrawerOpen(true)
  }

  return (
    <div className="animate-fade-in">
      {/* 페이지 헤더 */}
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Rules</h1>
        <p className="text-gray-500 mt-1">Configure event processing and action rules</p>
      </div>

      {/* 컨트롤 바 */}
      <div className="flex items-center justify-between mb-6 gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <select 
            value={domainFilter}
            onChange={(e) => setDomainFilter(e.target.value)}
            className="w-40"
          >
            <option value="all">All Domain</option>
            <option value="EMS">EMS</option>
            <option value="VERIFY">VERIFY</option>
            <option value="ESCALATION">ESCALATION</option>
            <option value="VOICE">VOICE</option>
          </select>

          <select 
            value={scopeFilter}
            onChange={(e) => setScopeFilter(e.target.value)}
            className="w-32"
          >
            <option value="all">All Scope</option>
            <option value="edge">Edge</option>
            <option value="cloud">Cloud</option>
            <option value="both">Both</option>
          </select>
          
          <div className="input-with-icon">
            <Search size={16} className="icon" />
            <input
              type="text"
              placeholder="Search by key..."
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
          <button className="btn btn-primary" onClick={() => { setSelectedRule(null); setDrawerOpen(true); }}>
            <Plus size={16} />
            New Rule
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
                <th>Priority</th>
                <th>Scope</th>
                <th>Description</th>
                <th>Enabled</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {filteredRules.map((rule) => (
                <tr 
                  key={rule.key}
                  className="cursor-pointer"
                  onClick={() => openEditDrawer(rule)}
                >
                  <td>
                    <span className="font-mono text-sm text-primary">{rule.key}</span>
                  </td>
                  <td>
                    <span className={`badge ${domainConfig[rule.domain].class}`}>
                      {domainConfig[rule.domain].label}
                    </span>
                  </td>
                  <td className="font-mono text-sm">{rule.priority}</td>
                  <td>
                    <span className={`badge ${scopeConfig[rule.scope].class}`}>
                      {scopeConfig[rule.scope].label}
                    </span>
                  </td>
                  <td className="text-gray-600 text-sm">{rule.description}</td>
                  <td>
                    <div className={`status-dot ${rule.enabled ? 'active' : 'inactive'}`}></div>
                  </td>
                  <td className="text-gray-500 text-sm">{rule.updatedAt}</td>
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
          <div className="drawer animate-slide-in" style={{ width: '520px' }}>
            <div className="drawer-header">
              <h3 className="font-semibold">
                {selectedRule ? 'Edit Rule' : 'New Rule'}
              </h3>
              <button 
                className="btn btn-ghost btn-sm p-1"
                onClick={() => setDrawerOpen(false)}
              >
                <X size={20} />
              </button>
            </div>
            
            <div className="drawer-body space-y-6">
              {/* Rule Meta */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-3">Rule Meta</h4>
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm text-gray-500 mb-1">Key</label>
                    <input 
                      type="text" 
                      defaultValue={selectedRule?.key || ''}
                      placeholder="e.g., ems.fall_critical"
                      className="w-full font-mono"
                    />
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="block text-sm text-gray-500 mb-1">Domain</label>
                      <select defaultValue={selectedRule?.domain || ''} className="w-full">
                        <option value="EMS">EMS</option>
                        <option value="VERIFY">VERIFY</option>
                        <option value="ESCALATION">ESCALATION</option>
                        <option value="VOICE">VOICE</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm text-gray-500 mb-1">Priority</label>
                      <input 
                        type="number" 
                        defaultValue={selectedRule?.priority || 50}
                        className="w-full"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-500 mb-1">Scope</label>
                      <select defaultValue={selectedRule?.scope || 'cloud'} className="w-full">
                        <option value="edge">Edge</option>
                        <option value="cloud">Cloud</option>
                        <option value="both">Both</option>
                      </select>
                    </div>
                  </div>
                  <div className="flex items-center justify-between py-2">
                    <span className="text-sm text-gray-700">Enabled</span>
                    <div className={`toggle ${selectedRule?.enabled !== false ? 'active' : ''}`}></div>
                  </div>
                </div>
              </div>

              {/* Editor Mode Toggle */}
              <div className="flex items-center gap-2 p-1 bg-gray-100 rounded-lg w-fit">
                <button 
                  className={`px-3 py-1.5 text-sm font-medium rounded-md transition ${
                    editorMode === 'builder' ? 'bg-white shadow text-gray-900' : 'text-gray-500'
                  }`}
                  onClick={() => setEditorMode('builder')}
                >
                  <GitMerge size={14} className="inline mr-1" />
                  Builder
                </button>
                <button 
                  className={`px-3 py-1.5 text-sm font-medium rounded-md transition ${
                    editorMode === 'json' ? 'bg-white shadow text-gray-900' : 'text-gray-500'
                  }`}
                  onClick={() => setEditorMode('json')}
                >
                  <Code size={14} className="inline mr-1" />
                  JSON
                </button>
              </div>

              {editorMode === 'builder' ? (
                <>
                  {/* Condition Builder */}
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-3">Conditions</h4>
                    <div className="p-4 bg-gray-50 rounded-lg border">
                      <div className="flex items-center gap-2 mb-3">
                        <select className="text-sm py-1.5">
                          <option value="event_type">event_type</option>
                          <option value="measurement">measurement</option>
                          <option value="device_status">device_status</option>
                          <option value="no_response">no_response</option>
                          <option value="voice_keyword">voice_keyword</option>
                        </select>
                        <select className="text-sm py-1.5 w-20">
                          <option value="==">=</option>
                          <option value="<">&lt;</option>
                          <option value=">">&gt;</option>
                          <option value="contains">contains</option>
                        </select>
                        <input 
                          type="text"
                          placeholder="value"
                          className="flex-1 text-sm py-1.5"
                        />
                      </div>
                      <button className="text-sm text-primary hover:underline">
                        + Add condition (AND)
                      </button>
                    </div>
                  </div>

                  {/* Action Builder */}
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-3">Action</h4>
                    <div className="space-y-3">
                      <div>
                        <label className="block text-sm text-gray-500 mb-1">Action Type</label>
                        <select className="w-full">
                          <option value="open_or_merge_case">Open/Merge Case</option>
                          <option value="create_alert">Create Alert</option>
                          <option value="contact_ems">Contact EMS (119)</option>
                          <option value="escalate_next">Escalate to Next Stage</option>
                          <option value="send_notification">Send Notification</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm text-gray-500 mb-1">Plan Name</label>
                        <select className="w-full">
                          <option value="">Select plan...</option>
                          <option value="default_escalation">default_escalation</option>
                          <option value="critical_emergency">critical_emergency</option>
                          <option value="low_priority">low_priority</option>
                        </select>
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <>
                  {/* JSON Editor */}
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-3">Condition JSON</h4>
                    <textarea 
                      className="w-full h-32 font-mono text-sm p-3"
                      defaultValue={JSON.stringify(selectedRule?.conditions || {}, null, 2)}
                    />
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-3">Action JSON</h4>
                    <textarea 
                      className="w-full h-32 font-mono text-sm p-3"
                      defaultValue={JSON.stringify(selectedRule?.action || {}, null, 2)}
                    />
                  </div>
                </>
              )}

              {/* Reference Check */}
              <div className="p-3 bg-success-50 rounded-lg border border-success-100">
                <div className="flex items-center gap-2 text-success text-sm">
                  <Check size={16} />
                  <span>Referenced plan_name exists</span>
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
