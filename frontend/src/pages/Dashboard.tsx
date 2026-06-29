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
  loop: string
  safety: {
    executes_runtime: boolean
    reads_external_artifacts: boolean
    stores_large_payloads: boolean
  }
}

type BenchmarkRun = RecordItem & {
  benchmark_id?: string
  scores?: Record<string, unknown>
}

const runtimeStats = [
  {
    label: 'FARS DEPLOYMENTS',
    path: '/status',
    countKeys: ['sessions', 'research_rounds'],
    copy: 'AI Runtime 的接入和运行实例。',
  },
  {
    label: 'RESEARCH RUNS',
    path: '/research',
    countKeys: ['sessions', 'research_rounds', 'experiments'],
    copy: '从计划到实验的研究运行。',
  },
  {
    label: 'OUTPUTS',
    path: '/artifacts',
    countKeys: ['artifacts', 'benchmark_runs'],
    copy: '报告、图表、分数和外部结果引用。',
  },
  {
    label: 'REVIEW / DECISION',
    path: '/research',
    countKeys: ['evidence_records', 'reviews', 'decisions'],
    copy: '质量门、结论和下一轮方向。',
  },
]

const stageCards = [
  { label: 'Ideation', countKeys: ['sources', 'insights', 'hypotheses'], copy: '想法和假设' },
  { label: 'Planning', countKeys: ['research_questions', 'protocols'], copy: '计划和协议' },
  { label: 'Experimentation', countKeys: ['sessions', 'research_rounds', 'experiments', 'benchmark_runs'], copy: '运行和 benchmark' },
  { label: 'Writing', countKeys: ['artifacts'], copy: '论文、报告、日志' },
  { label: 'Review', countKeys: ['evidence_records', 'reviews'], copy: '证据和审查' },
  { label: 'Decision', countKeys: ['decisions', 'experiences'], copy: '决策和经验' },
]

const activeStatuses = new Set(['planned', 'queued', 'claimed', 'running'])
const riskStatuses = new Set(['blocked', 'degraded', 'failed', 'rejected'])

function firstNumericScore(scores?: Record<string, unknown>) {
  for (const [metric, value] of Object.entries(scores || {})) {
    const score = typeof value === 'number' ? value : Number(value)
    if (Number.isFinite(score)) return { metric, score }
  }
  return null
}

function scoreWidth(score: number) {
  const normalized = score <= 1 ? score * 100 : score
  return `${Math.max(4, Math.min(100, normalized))}%`
}

export function DashboardPage() {
  const status = useQuery({ queryKey: ['status'], queryFn: () => getData<SystemStatus>('/api/v1/system/status') })
  const methodLoop = useQuery({ queryKey: ['method-loop'], queryFn: () => getData<MethodLoop>('/api/v1/method-loop') })
  const sessions = useQuery({ queryKey: ['dashboard-sessions'], queryFn: () => getListData<RecordItem>('/api/v1/research/sessions') })
  const rounds = useQuery({ queryKey: ['dashboard-rounds'], queryFn: () => getListData<RecordItem>('/api/v1/research/rounds') })
  const benchmarkRuns = useQuery({ queryKey: ['dashboard-benchmark-runs'], queryFn: () => getListData<BenchmarkRun>('/api/v1/benchmark-runs') })

  const collections = status.data?.collections || {}
  const countFor = (keys: string[]) => keys.reduce((total, key) => total + (collections[key] || 0), 0)
  const runItems = [...(sessions.data?.items || []), ...(rounds.data?.items || [])]
  const activeRuns = runItems.filter((item) => activeStatuses.has(String(item.status || ''))).length
  const riskRuns = runItems.filter((item) => riskStatuses.has(String(item.status || ''))).length
  const completedRuns = runItems.filter((item) => item.status === 'completed').length
  const scoredRuns = (benchmarkRuns.data?.items || [])
    .map((run) => ({ run, score: firstNumericScore(run.scores) }))
    .filter((item): item is { run: BenchmarkRun; score: { metric: string; score: number } } => Boolean(item.score))
    .slice(0, 6)

  return (
    <div className="stack">
      <section className="console-hero">
        <div>
          <h2>FARS Runtime Console</h2>
          <p>
            Ideation、Planning、Experimentation、Writing、Review 和 Decision 在这里保持可见。
            Runtime 负责执行，平台只保存状态、引用和质量门。
          </p>
        </div>
        <div className="console-health">
          <div>
            <span>API</span>
            <StatusBadge status={status.data?.status === 'ok' ? 'ready' : status.data?.status} />
          </div>
          <div>
            <span>Store</span>
            <strong>{status.data?.store || 'unknown'}</strong>
          </div>
          <div>
            <span>Loop</span>
            <strong>{methodLoop.data?.safety?.executes_runtime === false ? 'control-plane' : 'unknown'}</strong>
          </div>
        </div>
      </section>

      <Panel title="FARS DEPLOYMENTS">
        <div className="dashboard-metrics">
          {runtimeStats.map((stat) => (
            <Link className="metric-card" to={stat.path} key={stat.label}>
              <strong>{countFor(stat.countKeys)}</strong>
              <span>{stat.label}</span>
              <small>{stat.copy}</small>
            </Link>
          ))}
        </div>
      </Panel>

      <div className="grid-two">
        <Panel title="RESEARCH RUNS">
          <div className="detail-grid">
            <div><strong>{runItems.length}</strong><span>运行总数</span></div>
            <div><strong>{activeRuns}</strong><span>活跃或计划中</span></div>
            <div><strong>{riskRuns}</strong><span>阻塞 / 降级 / 失败</span></div>
          </div>
          <div className="record-list compact">
            {runItems.slice(0, 5).map((run) => (
              <article className="record-row" key={run.id}>
                <div>
                  <div className="record-title">{String(run.title || run.proposal || run.id)}</div>
                  <div className="record-meta">{String(run.id)} · {String(run.created_at || 'time unknown')}</div>
                </div>
                <StatusBadge status={typeof run.status === 'string' ? run.status : undefined} />
              </article>
            ))}
          </div>
          {!runItems.length ? <div className="empty">暂无 research run。</div> : null}
        </Panel>

        <Panel title="SCORE PROGRESS">
          <div className="detail-grid">
            <div><strong>{benchmarkRuns.data?.total || 0}</strong><span>benchmark run 数</span></div>
            <div><strong>{scoredRuns.length}</strong><span>有数值分数</span></div>
            <div><strong>{completedRuns}</strong><span>已完成运行</span></div>
          </div>
          <div className="score-list">
            {scoredRuns.map(({ run, score }) => (
              <article className="score-row" key={run.id}>
                <div>
                  <strong>{String(run.benchmark_id || run.id)}</strong>
                  <span>{score.metric}: {score.score}</span>
                </div>
                <div className="score-bar" aria-label={`${score.metric} ${score.score}`}>
                  <span style={{ width: scoreWidth(score.score) }} />
                </div>
              </article>
            ))}
          </div>
          {!scoredRuns.length ? <div className="empty">等待外部 Runtime 回传 benchmark 结果。</div> : null}
        </Panel>
      </div>

      <Panel title="PIPELINE">
        <div className="pipeline-lane">
          {stageCards.map((stage) => (
            <div className="pipeline-stage" key={stage.label}>
              <strong>{stage.label}</strong>
              <span>{countFor(stage.countKeys)}</span>
              <small>{stage.copy}</small>
            </div>
          ))}
        </div>
        <p className="panel-copy">{methodLoop.data?.loop || 'Idea Pool -> Hypothesis -> Plan -> Experiment -> Result -> Review -> Decision -> Lesson'}</p>
      </Panel>
    </div>
  )
}
