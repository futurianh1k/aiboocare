import { useState } from 'react'
import { 
  Search, 
  Plus, 
  Download,
  GitBranch,
  Phone,
  MessageSquare,
  Mail,
  Bell,
  ChevronUp,
  ChevronDown,
  Trash2,
  GripVertical,
  Save,
  X,
  Copy
} from 'lucide-react'

// 더미 데이터
const plans = [
  {
    id: 'plan-001',
    name: 'default_escalation',
    eventGroup: 'ALL',
    minSeverity: 'ALERT',
    cooldownSec: 300,
    enabled: true,
    stages: [
      { no: 1, targetType: 'guardian1', timeoutSec: 300, retryCount: 2, channels: ['push', 'sms'], enabled: true },
      { no: 2, targetType: 'guardian2', timeoutSec: 300, retryCount: 2, channels: ['push', 'sms', 'voice'], enabled: true },
      { no: 3, targetType: 'caregiver', timeoutSec: 600, retryCount: 3, channels: ['push', 'sms', 'voice'], enabled: true },
      { no: 4, targetType: 'operations', timeoutSec: 900, retryCount: 3, channels: ['push', 'sms', 'voice', 'email'], enabled: true },
      { no: 5, targetType: 'ems', timeoutSec: 0, retryCount: 0, channels: ['voice'], enabled: true },
    ]
  },
  {
    id: 'plan-002',
    name: 'critical_emergency',
    eventGroup: 'FALL',
    minSeverity: 'CRITICAL',
    cooldownSec: 0,
    enabled: true,
    stages: [
      { no: 1, targetType: 'guardian1', timeoutSec: 60, retryCount: 1, channels: ['push', 'voice'], enabled: true },
      { no: 2, targetType: 'ems', timeoutSec: 0, retryCount: 0, channels: ['voice'], enabled: true },
    ]
  },
  {
    id: 'plan-003',
    name: 'low_priority',
    eventGroup: 'ENV',
    minSeverity: 'INFO',
    cooldownSec: 3600,
    enabled: true,
    stages: [
      { no: 1, targetType: 'guardian1', timeoutSec: 1800, retryCount: 1, channels: ['push'], enabled: true },
      { no: 2, targetType: 'operations', timeoutSec: 3600, retryCount: 1, channels: ['email'], enabled: true },
    ]
  },
]

const channelIcons: Record<string, any> = {
  push: Bell,
  sms: MessageSquare,
  voice: Phone,
  email: Mail,
}

const targetTypeLabels: Record<string, string> = {
  guardian1: '보호자 1',
  guardian2: '보호자 2',
  caregiver: '돌봄제공자',
  operations: '운영센터',
  ems: '119 응급',
}

export default function CallTree() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedPlan, setSelectedPlan] = useState<typeof plans[0] | null>(plans[0])

  const filteredPlans = plans.filter(p => 
    p.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="animate-fade-in">
      {/* 페이지 헤더 */}
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Call Tree (Escalation Plans)</h1>
        <p className="text-gray-500 mt-1">Configure escalation stages and notification channels</p>
      </div>

      {/* 컨트롤 바 */}
      <div className="flex items-center justify-between mb-6 gap-4">
        <div className="flex items-center gap-3">
          <div className="input-with-icon">
            <Search size={16} className="icon" />
            <input
              type="text"
              placeholder="Search plan name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ width: '250px' }}
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button className="btn btn-secondary">
            <Copy size={16} />
            Duplicate
          </button>
          <button className="btn btn-secondary">
            <Download size={16} />
            Export
          </button>
          <button className="btn btn-primary">
            <Plus size={16} />
            New Plan
          </button>
        </div>
      </div>

      {/* 콘텐츠 그리드 */}
      <div className="grid gap-6" style={{ gridTemplateColumns: '380px 1fr' }}>
        {/* 좌측: 플랜 목록 */}
        <div className="card">
          <div className="card-header">
            <h3 className="font-medium">Escalation Plans</h3>
          </div>
          <div className="divide-y">
            {filteredPlans.map((plan) => (
              <div 
                key={plan.id}
                onClick={() => setSelectedPlan(plan)}
                className={`p-4 cursor-pointer transition ${
                  selectedPlan?.id === plan.id ? 'bg-primary-50' : 'hover:bg-gray-50'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">{plan.name}</span>
                  <div className={`status-dot ${plan.enabled ? 'active' : 'inactive'}`}></div>
                </div>
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <span className="badge badge-gray">{plan.eventGroup}</span>
                  <span>Min: {plan.minSeverity}</span>
                  <span>Cooldown: {plan.cooldownSec}s</span>
                </div>
                <div className="mt-2 text-xs text-gray-400">
                  {plan.stages.length} stages
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 우측: 플랜 에디터 */}
        {selectedPlan ? (
          <div className="space-y-4">
            {/* Plan Settings */}
            <div className="card card-body">
              <h4 className="font-medium mb-4">Plan Settings</h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-500 mb-1">Name</label>
                  <input 
                    type="text" 
                    defaultValue={selectedPlan.name}
                    className="w-full font-mono"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-500 mb-1">Event Group</label>
                  <select defaultValue={selectedPlan.eventGroup} className="w-full">
                    <option value="ALL">ALL</option>
                    <option value="FALL">FALL</option>
                    <option value="VITALS">VITALS</option>
                    <option value="INACTIVITY">INACTIVITY</option>
                    <option value="ENV">ENV</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-500 mb-1">Min Severity</label>
                  <select defaultValue={selectedPlan.minSeverity} className="w-full">
                    <option value="CRITICAL">CRITICAL</option>
                    <option value="ALERT">ALERT</option>
                    <option value="WARNING">WARNING</option>
                    <option value="INFO">INFO</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-500 mb-1">Cooldown (sec)</label>
                  <input 
                    type="number" 
                    defaultValue={selectedPlan.cooldownSec}
                    className="w-full"
                  />
                </div>
              </div>
              <div className="flex items-center justify-between mt-4 pt-4 border-t">
                <span className="text-sm text-gray-700">Enabled</span>
                <div className={`toggle ${selectedPlan.enabled ? 'active' : ''}`}></div>
              </div>
            </div>

            {/* Stages */}
            <div className="card">
              <div className="card-header flex items-center justify-between">
                <h4 className="font-medium">Stages</h4>
                <button className="btn btn-secondary btn-sm">
                  <Plus size={14} />
                  Add Stage
                </button>
              </div>
              <div className="divide-y">
                {selectedPlan.stages.map((stage, index) => (
                  <div key={stage.no} className="p-4">
                    <div className="flex items-start gap-3">
                      <button className="p-1 text-gray-400 hover:text-gray-600 cursor-grab mt-1">
                        <GripVertical size={16} />
                      </button>
                      
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <span className="w-6 h-6 rounded-full bg-primary-100 text-primary-700 text-xs font-medium flex items-center justify-center">
                              {stage.no}
                            </span>
                            <span className="font-medium">{targetTypeLabels[stage.targetType]}</span>
                            {stage.targetType === 'ems' && (
                              <span className="badge badge-error text-xs">고정</span>
                            )}
                          </div>
                          <div className="flex items-center gap-1">
                            <div className={`status-dot ${stage.enabled ? 'active' : 'inactive'}`}></div>
                            <button className="btn btn-ghost btn-sm p-1">
                              <ChevronUp size={14} />
                            </button>
                            <button className="btn btn-ghost btn-sm p-1">
                              <ChevronDown size={14} />
                            </button>
                            {stage.targetType !== 'ems' && (
                              <button className="btn btn-ghost btn-sm p-1 text-error">
                                <Trash2 size={14} />
                              </button>
                            )}
                          </div>
                        </div>
                        
                        <div className="grid grid-cols-4 gap-3 text-sm">
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">Target Type</label>
                            <select 
                              defaultValue={stage.targetType} 
                              className="w-full text-sm py-1.5"
                              disabled={stage.targetType === 'ems'}
                            >
                              <option value="guardian1">보호자 1</option>
                              <option value="guardian2">보호자 2</option>
                              <option value="caregiver">돌봄제공자</option>
                              <option value="operations">운영센터</option>
                              <option value="ems">119 응급</option>
                            </select>
                          </div>
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">Timeout (sec)</label>
                            <input 
                              type="number" 
                              defaultValue={stage.timeoutSec}
                              className="w-full text-sm py-1.5"
                              disabled={stage.targetType === 'ems'}
                            />
                          </div>
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">Retry Count</label>
                            <input 
                              type="number" 
                              defaultValue={stage.retryCount}
                              className="w-full text-sm py-1.5"
                              disabled={stage.targetType === 'ems'}
                            />
                          </div>
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">Channels</label>
                            <div className="flex items-center gap-1">
                              {Object.entries(channelIcons).map(([channel, Icon]) => (
                                <button
                                  key={channel}
                                  className={`p-1.5 rounded ${
                                    stage.channels.includes(channel)
                                      ? 'bg-primary-100 text-primary-700'
                                      : 'bg-gray-100 text-gray-400'
                                  }`}
                                  title={channel}
                                >
                                  <Icon size={14} />
                                </button>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-3">
              <button className="btn btn-secondary">
                Validate Plan
              </button>
              <button className="btn btn-primary">
                <Save size={16} />
                Save Plan
              </button>
            </div>
          </div>
        ) : (
          <div className="card card-body empty-state">
            <GitBranch size={48} className="mb-4" />
            <p>Select a plan to edit</p>
          </div>
        )}
      </div>
    </div>
  )
}
