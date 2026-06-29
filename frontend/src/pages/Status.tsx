import { useQuery } from '@tanstack/react-query'
import { ErrorMessage, Panel, StatusBadge, WarningList } from '@/components/Primitives'
import { getData, requestEnvelope } from '@/lib/api'

type ReadinessAction = {
  endpoint?: string
  reason?: string
  priority?: string
}

type ReadinessCheck = {
  id: string
  status: string
  title: string
  detail: string
  recommended_action?: ReadinessAction
}

type SystemReadiness = {
  state: string
  checks: ReadinessCheck[]
  store: Record<string, unknown>
  schema_contract: Record<string, unknown>
  recommended_next_actions: ReadinessAction[]
  safety: string
}

type SecurityStatus = {
  auth_required: boolean
  auth_scheme: string
  protected_scope: string
  public_endpoints: string[]
  audit: {
    writes: boolean
    denied_requests: boolean
    body_storage: boolean
    collection: string
  }
  safety: string
}

function formatBool(value: unknown) {
  return value ? '是' : '否'
}

function countCollections(store: Record<string, unknown>) {
  const collections = store.collections
  if (!collections || typeof collections !== 'object') return '未记录'
  const total = Object.values(collections as Record<string, unknown>).reduce<number>((sum, value) => {
    return sum + (typeof value === 'number' ? value : 0)
  }, 0)
  return String(total)
}

function formatSafety(safety: string) {
  if (safety === 'read_only_deployment_readiness_no_external_access') {
    return '只读检查，不访问外部运行时或成果引用地址。'
  }
  return safety
}

function formatPayloadModel(model: unknown) {
  if (model === 'jsonb_payload_tables') return '结构化载荷表'
  return String(model || '未记录')
}

function formatAuthScheme(scheme: string) {
  if (scheme === 'bearer') return '令牌认证'
  if (scheme === 'disabled_for_local_development') return '本地开发未启用'
  return scheme
}

export function StatusPage() {
  const status = useQuery({ queryKey: ['status'], queryFn: () => getData<Record<string, unknown>>('/api/v1/system/status') })
  const readiness = useQuery({
    queryKey: ['system-readiness'],
    queryFn: () => requestEnvelope<SystemReadiness>('/api/v1/system/readiness'),
  })
  const security = useQuery({
    queryKey: ['system-security'],
    queryFn: () => getData<SecurityStatus>('/api/v1/system/security'),
  })
  const readinessData = readiness.data?.data
  const securityData = security.data

  return (
    <div className="grid-two">
      <Panel title="部署就绪">
        <WarningList warnings={readiness.data?.warnings} />
        <ErrorMessage message={readiness.error?.message} />
        {readinessData ? (
          <div className="record-list">
            <article className="record-row">
              <div>
                <div className="record-title">整体状态</div>
                <div className="record-meta">安全边界 {formatSafety(readinessData.safety)}</div>
              </div>
              <StatusBadge status={readinessData.state} />
            </article>
            <article className="record-row">
              <div>
                <div className="record-title">存储</div>
                <div className="record-meta">类型 {String(readinessData.store.store || '未记录')}</div>
                <div className="record-meta">路径 {String(readinessData.store.path || '未记录')}</div>
                <div className="record-meta">当前记录数 {countCollections(readinessData.store)}</div>
              </div>
            </article>
            <article className="record-row">
              <div>
                <div className="record-title">数据库结构合同</div>
                <div className="record-meta">迁移 {String(readinessData.schema_contract.migration || '未记录')}</div>
                <div className="record-meta">平台文本 ID {formatBool(readinessData.schema_contract.uses_platform_text_ids)}</div>
                <div className="record-meta">排除旧模块 {formatBool(readinessData.schema_contract.forbids_legacy_tables)}</div>
                <div className="record-meta">载荷模型 {formatPayloadModel(readinessData.schema_contract.payload_model)}</div>
              </div>
            </article>
          </div>
        ) : <div className="empty">正在读取部署就绪状态</div>}
      </Panel>

      <Panel title="检查项">
        {readinessData?.checks.length ? (
          <div className="record-list compact">
            {readinessData.checks.map((check) => (
              <article className="record-row" key={check.id}>
                <div>
                  <div className="record-title">{check.title}</div>
                  <div className="record-meta">{check.detail}</div>
                  {check.recommended_action ? (
                    <div className="record-meta">
                      {check.recommended_action.endpoint || '未记录'} · {check.recommended_action.reason || ''}
                    </div>
                  ) : null}
                </div>
                <StatusBadge status={check.status} />
              </article>
            ))}
          </div>
        ) : <div className="empty">暂无检查项</div>}
      </Panel>

      <Panel title="建议动作">
        {readinessData?.recommended_next_actions.length ? (
          <div className="record-list compact">
            {readinessData.recommended_next_actions.map((action) => (
              <article className="record-row" key={`${action.endpoint}-${action.reason}`}>
                <div>
                <div className="record-title">{action.endpoint || '未记录接口'}</div>
                  <div className="record-meta">{action.reason || '未记录原因'}</div>
                </div>
                <StatusBadge status={action.priority === 'high' ? 'blocked' : 'degraded'} />
              </article>
            ))}
          </div>
        ) : <div className="empty">暂无建议动作</div>}
      </Panel>

      <Panel title="认证与审计">
        <ErrorMessage message={security.error?.message} />
        {securityData ? (
          <div className="record-list compact">
            <article className="record-row">
              <div>
                <div className="record-title">访问控制</div>
                <div className="record-meta">认证方式 {formatAuthScheme(securityData.auth_scheme)}</div>
                <div className="record-meta">保护范围 {securityData.protected_scope}</div>
              </div>
              <StatusBadge status={securityData.auth_required ? 'ready' : 'degraded'} />
            </article>
            <article className="record-row">
              <div>
                <div className="record-title">审计策略</div>
                <div className="record-meta">写操作 {formatBool(securityData.audit.writes)} · 拒绝请求 {formatBool(securityData.audit.denied_requests)}</div>
                <div className="record-meta">保存请求正文 {formatBool(securityData.audit.body_storage)} · 集合 {securityData.audit.collection}</div>
              </div>
            </article>
            <article className="record-row">
              <div>
                <div className="record-title">公开入口</div>
                <div className="record-meta">{securityData.public_endpoints.join('，')}</div>
              </div>
            </article>
          </div>
        ) : <div className="empty">正在读取安全状态</div>}
      </Panel>

      <Panel title="系统状态">
        <ErrorMessage message={status.error?.message} />
        <pre className="json-preview">{JSON.stringify(status.data, null, 2)}</pre>
      </Panel>
    </div>
  )
}
