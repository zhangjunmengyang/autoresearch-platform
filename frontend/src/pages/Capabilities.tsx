import { useQuery } from '@tanstack/react-query'
import { ErrorMessage, Panel, StatusBadge } from '@/components/Primitives'
import { getData } from '@/lib/api'
import { formatHumanText, formatScalar } from '@/lib/display'

type OnboardingBundle = {
  state: string
  openapi: string
  security: {
    auth_required: boolean
    auth_scheme: string
  }
  readiness: {
    state: string
    recommended_next_actions: Array<{ endpoint?: string; reason?: string; priority?: string }>
  }
  skill: {
    name: string
    path: string
    load_order: string[]
  }
  recommended_first_calls: string[]
  integrity: {
    external_reads: boolean
    external_writes: boolean
    executes_runtime: boolean
    returns_openapi_body: boolean
  }
  safety: string
}

function formatBool(value: boolean) {
  return value ? '是' : '否'
}

function formatAuthScheme(scheme: string) {
  if (scheme === 'bearer') return '令牌认证'
  if (scheme === 'disabled_for_local_development') return '本地开发未启用'
  return scheme || '未记录'
}

function formatCapabilityText(value: unknown) {
  return formatHumanText(value)
}

export function CapabilitiesPage() {
  const capabilities = useQuery({ queryKey: ['capabilities'], queryFn: () => getData<Array<Record<string, unknown>>>('/api/v1/capabilities') })
  const onboarding = useQuery({
    queryKey: ['agent-onboarding'],
    queryFn: () => getData<OnboardingBundle>('/api/v1/agent/onboarding'),
  })
  const onboardingData = onboarding.data

  return (
    <div className="stack">
      <Panel title="智能体接入自检">
        <ErrorMessage message={onboarding.error?.message} />
        {onboardingData ? (
          <div className="record-list compact">
            <article className="record-row">
              <div>
                <div className="record-title">接入状态</div>
                <div className="record-meta">接口合同 已生成</div>
                <div className="record-meta">认证 {formatAuthScheme(onboardingData.security.auth_scheme)} · 需要令牌 {formatBool(onboardingData.security.auth_required)}</div>
              </div>
              <StatusBadge status={onboardingData.state} />
            </article>
            <article className="record-row">
              <div>
                <div className="record-title">技能加载顺序</div>
                <div className="record-meta">自动研究使用流程</div>
                <div className="record-meta">共 {onboardingData.skill.load_order.length} 个加载步骤</div>
              </div>
              <StatusBadge status={onboardingData.readiness.state} />
            </article>
            <article className="record-row">
              <div>
                <div className="record-title">建议首批调用</div>
                <div className="record-meta">共 {onboardingData.recommended_first_calls.length} 个建议调用，按接口合同执行。</div>
              </div>
            </article>
            <article className="record-row">
              <div>
                <div className="record-title">只读边界</div>
                <div className="record-meta">
                  外部读取 {formatBool(onboardingData.integrity.external_reads)} · 外部写入 {formatBool(onboardingData.integrity.external_writes)} · 执行运行时 {formatBool(onboardingData.integrity.executes_runtime)}
                </div>
                <div className="record-meta">返回接口全文 {formatBool(onboardingData.integrity.returns_openapi_body)} · {formatCapabilityText(formatScalar(onboardingData.safety))}</div>
              </div>
            </article>
            {onboardingData.readiness.recommended_next_actions.length ? (
              <article className="record-row">
                <div>
                  <div className="record-title">接入建议动作</div>
                  {onboardingData.readiness.recommended_next_actions.map((action) => (
                    <div className="record-meta" key={`${action.endpoint}-${action.reason}`}>
                      {formatCapabilityText(action.reason || '未记录原因')}
                    </div>
                  ))}
                </div>
              </article>
            ) : null}
          </div>
        ) : <div className="empty">正在读取接入自检包</div>}
      </Panel>

      <Panel title="外部运行方能力目录">
        <ErrorMessage message={capabilities.error?.message} />
        <div className="capability-grid">
          {(capabilities.data || []).map((capability) => (
            <article className="capability" key={String(capability.id)}>
              <h2>{formatCapabilityText(capability.name)}</h2>
              <p>{formatCapabilityText(capability.when_to_use)}</p>
              <code>主接口见接口合同</code>
            </article>
          ))}
        </div>
      </Panel>
    </div>
  )
}
