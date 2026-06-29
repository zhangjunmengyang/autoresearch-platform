import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Panel, StatusBadge } from '@/components/Primitives'
import { getData, getListData, type RecordItem } from '@/lib/api'
import { formatTimestamp, labelTerm } from '@/lib/display'

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
    label: '自动研究部署',
    path: '/status',
    countKeys: ['sessions', 'research_rounds'],
    copy: '智能运行方的接入和运行实例。',
  },
  {
    label: '研究运行',
    path: '/research',
    countKeys: ['sessions', 'research_rounds', 'experiments'],
    copy: '从计划到实验的研究运行。',
  },
  {
    label: '成果',
    path: '/artifacts',
    countKeys: ['artifacts', 'benchmark_runs'],
    copy: '报告、图表、分数和外部结果引用。',
  },
  {
    label: '审查与决策',
    path: '/research',
    countKeys: ['evidence_records', 'reviews', 'decisions'],
    copy: '质量门、结论和下一轮方向。',
  },
]

const stageCards = [
  { label: '构想', countKeys: ['sources', 'insights', 'hypotheses'], copy: '想法和假设' },
  { label: '计划', countKeys: ['research_questions', 'protocols'], copy: '计划和协议' },
  { label: '实验', countKeys: ['sessions', 'research_rounds', 'experiments', 'benchmark_runs'], copy: '运行和评测' },
  { label: '写作', countKeys: ['artifacts'], copy: '论文、报告、日志' },
  { label: '审查', countKeys: ['evidence_records', 'reviews'], copy: '证据和审查' },
  { label: '决策', countKeys: ['decisions', 'experiences'], copy: '决策和经验' },
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

function formatStoreName(store?: string) {
  if (store === 'json') return '本地文件'
  if (store === 'postgres') return '关系数据库'
  return store || '未知'
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
          <h2>全自动研究运行看板</h2>
          <p>
            构想、计划、实验、写作、审查和决策在这里保持可见。
            智能运行方负责执行，平台只保存状态、引用和质量门。
          </p>
        </div>
        <div className="console-health">
          <div>
            <span>接口</span>
            <StatusBadge status={status.data?.status === 'ok' ? 'ready' : status.data?.status} />
          </div>
          <div>
            <span>存储</span>
            <strong>{formatStoreName(status.data?.store)}</strong>
          </div>
          <div>
            <span>边界</span>
            <strong>{methodLoop.data?.safety?.executes_runtime === false ? '控制面' : '未知'}</strong>
          </div>
        </div>
      </section>

      <Panel title="自动研究部署">
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
        <Panel title="研究运行">
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
                  <div className="record-meta">{String(run.id)} · {formatTimestamp(run.created_at)}</div>
                </div>
                <StatusBadge status={typeof run.status === 'string' ? run.status : undefined} />
              </article>
            ))}
          </div>
          {!runItems.length ? <div className="empty">暂无研究运行。</div> : null}
        </Panel>

        <Panel title="分数进展">
          <div className="detail-grid">
            <div><strong>{benchmarkRuns.data?.total || 0}</strong><span>评测运行数</span></div>
            <div><strong>{scoredRuns.length}</strong><span>有数值分数</span></div>
            <div><strong>{completedRuns}</strong><span>已完成运行</span></div>
          </div>
          <div className="score-list">
            {scoredRuns.map(({ run, score }) => (
              <article className="score-row" key={run.id}>
                <div>
                  <strong>{String(run.benchmark_id || run.id)}</strong>
                  <span>{labelTerm(score.metric)}：{score.score}</span>
                </div>
                <div className="score-bar" aria-label={`${score.metric} ${score.score}`}>
                  <span style={{ width: scoreWidth(score.score) }} />
                </div>
              </article>
            ))}
          </div>
          {!scoredRuns.length ? <div className="empty">等待外部运行方回传评测结果。</div> : null}
        </Panel>
      </div>

      <Panel title="研究流水线">
        <div className="pipeline-lane">
          {stageCards.map((stage) => (
            <div className="pipeline-stage" key={stage.label}>
              <strong>{stage.label}</strong>
              <span>{countFor(stage.countKeys)}</span>
              <small>{stage.copy}</small>
            </div>
          ))}
        </div>
        <p className="panel-copy">{'想法池 -> 假设 -> 计划 -> 实验 -> 结果 -> 审查 -> 决策 -> 经验'}</p>
      </Panel>
    </div>
  )
}
