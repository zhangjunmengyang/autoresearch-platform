import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Panel, StatusBadge } from '@/components/Primitives'
import { getData, getListData, type RecordItem } from '@/lib/api'

type SystemStatus = {
  status: string
  store: string
  collections: Record<string, number>
}

type MethodLoop = {
  stages: Array<{
    id: string
    label: string
    count: number
  }>
  safety: {
    executes_runtime: boolean
    reads_external_artifacts: boolean
    stores_large_payloads: boolean
  }
}

const stageNames = [
  { label: 'Ideation', ids: ['idea_pool', 'hypothesis'] },
  { label: 'Planning', ids: ['plan'] },
  { label: 'Experimentation', ids: ['experiment'] },
  { label: 'Writing', ids: ['result'] },
  { label: 'Review', ids: ['review'] },
  { label: 'Decision', ids: ['decision', 'lesson'] },
]

const diagnostics = [
  { path: '/research/context', title: 'Research Context 上下文', copy: '恢复已有事实、风险和相关经验。' },
  { path: '/research/readiness', title: 'Readiness 状态门', copy: '查看进入实验、审查、决策前的阻塞点。' },
  { path: '/research/audit', title: 'Audit Export 审计包', copy: '导出交接、复现和开源审查需要的只读包。' },
  { path: '/capabilities', title: 'Capabilities 能力', copy: '查看外部 Runtime 可发现的 OpenAPI 能力。' },
  { path: '/status', title: 'System 状态', copy: '查看部署、认证、存储和安全边界。' },
]

const activeStatuses = new Set(['planned', 'queued', 'claimed', 'running'])
const riskStatuses = new Set(['blocked', 'degraded', 'failed', 'rejected'])

function latestFirst(items: RecordItem[]) {
  return [...items].sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || '')))
}

function safeNoFlag(value?: boolean) {
  return value === false ? '是' : '未知'
}

export function ResearchWorkbenchPage() {
  const status = useQuery({ queryKey: ['workbench-status'], queryFn: () => getData<SystemStatus>('/api/v1/system/status') })
  const methodLoop = useQuery({ queryKey: ['workbench-method-loop'], queryFn: () => getData<MethodLoop>('/api/v1/method-loop') })
  const sessions = useQuery({ queryKey: ['workbench-sessions'], queryFn: () => getListData<RecordItem>('/api/v1/research/sessions') })
  const rounds = useQuery({ queryKey: ['workbench-rounds'], queryFn: () => getListData<RecordItem>('/api/v1/research/rounds') })
  const outputs = useQuery({ queryKey: ['workbench-results'], queryFn: () => getListData<RecordItem>('/api/v1/results') })

  const collections = status.data?.collections || {}
  const safety = methodLoop.data?.safety
  const runItems = latestFirst([...(sessions.data?.items || []), ...(rounds.data?.items || [])])
  const activeRuns = runItems.filter((item) => activeStatuses.has(String(item.status || ''))).length
  const riskRuns = runItems.filter((item) => riskStatuses.has(String(item.status || ''))).length
  const stageCount = (ids: string[]) => {
    const stages = methodLoop.data?.stages || []
    return ids.reduce((total, id) => total + (stages.find((stage) => stage.id === id)?.count || 0), 0)
  }

  return (
    <div className="stack">
      <Panel title="FARS DEPLOYMENTS">
        <div className="detail-grid">
          <div><strong>{status.data?.status || 'unknown'}</strong><span>API 状态</span></div>
          <div><strong>{status.data?.store || 'unknown'}</strong><span>存储后端</span></div>
          <div><strong>{collections.sessions || 0}</strong><span>Runtime Sessions</span></div>
        </div>
        <div className="runtime-contract">
          <div>
            <strong>Runtime boundary</strong>
            <span>REST/OpenAPI 接收事实、引用和状态；执行留在平台外。</span>
          </div>
          <div>
            <strong>Safety flags</strong>
            <div className="runtime-flags">
              <span>不执行 Runtime: {safeNoFlag(safety?.executes_runtime)}</span>
              <span>不读取外部 artifact: {safeNoFlag(safety?.reads_external_artifacts)}</span>
              <span>不保存大 payload: {safeNoFlag(safety?.stores_large_payloads)}</span>
            </div>
          </div>
        </div>
      </Panel>

      <div className="grid-two">
        <Panel title="RESEARCH RUNS">
          <div className="detail-grid">
            <div><strong>{runItems.length}</strong><span>已观察运行</span></div>
            <div><strong>{activeRuns}</strong><span>活跃或计划中</span></div>
            <div><strong>{riskRuns}</strong><span>阻塞 / 降级 / 失败</span></div>
          </div>
          <div className="record-list compact">
            {runItems.slice(0, 8).map((run) => (
              <article className="record-row" key={run.id}>
                <div>
                  <div className="record-title">{String(run.title || run.proposal || run.id)}</div>
                  <div className="record-meta">{String(run.id)} · {String(run.updated_at || run.created_at || 'time unknown')}</div>
                </div>
                <StatusBadge status={typeof run.status === 'string' ? run.status : undefined} />
              </article>
            ))}
          </div>
          {!runItems.length ? <div className="empty">暂无 research run。</div> : null}
        </Panel>

        <Panel title="OUTPUTS">
          <div className="detail-grid">
            <div><strong>{outputs.data?.total || 0}</strong><span>结果引用</span></div>
            <div><strong>{collections.benchmark_runs || 0}</strong><span>benchmark run 数</span></div>
            <div><strong>{collections.experiences || 0}</strong><span>经验数</span></div>
          </div>
          <div className="record-list compact">
            {(outputs.data?.items || []).slice(0, 5).map((output) => (
              <article className="record-row" key={output.id}>
                <div>
                  <div className="record-title">{String(output.title || output.artifact_type || output.id)}</div>
                  <div className="record-meta">{String(output.uri || output.summary || '外部引用')}</div>
                </div>
                <StatusBadge status={typeof output.status === 'string' ? output.status : undefined} />
              </article>
            ))}
          </div>
          {!outputs.data?.items.length ? <div className="empty">暂无 output 引用。</div> : null}
        </Panel>
      </div>

      <Panel title="PIPELINE SNAPSHOT">
        <div className="pipeline-lane">
          {stageNames.map((stage) => (
            <div className="pipeline-stage" key={stage.label}>
              <strong>{stage.label}</strong>
              <span>{stageCount(stage.ids)}</span>
              <small>{stage.ids.join(' / ')}</small>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="RUNTIME CONTRACT">
        <div className="link-grid diagnostics-grid">
          {diagnostics.map((item) => (
            <Link className="link-card" to={item.path} key={item.path}>
              <strong>{item.title}</strong>
              <span>{item.copy}</span>
            </Link>
          ))}
        </div>
      </Panel>
    </div>
  )
}
