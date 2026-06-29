import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Panel } from '@/components/Primitives'
import { getData } from '@/lib/api'

type SystemStatus = {
  status: string
  store: string
  collections: Record<string, number>
}

const metrics = [
  { key: 'sources', label: '资料输入', path: '/sources' },
  { key: 'research_programs', label: '研究计划', path: '/research/methodology' },
  { key: 'research_questions', label: '研究问题', path: '/research/methodology' },
  { key: 'intake_items', label: '研究队列', path: '/research-queue' },
  { key: 'research_rounds', label: '研究轮次', path: '/research/rounds' },
  { key: 'sessions', label: '研究账本', path: '/sessions' },
  { key: 'events', label: '过程事件', path: '/research/audit' },
  { key: 'experiments', label: '实验记录', path: '/research/audit' },
  { key: 'evidence_records', label: '证据记录', path: '/evidence' },
  { key: 'artifacts', label: '成果引用', path: '/artifacts' },
  { key: 'benchmark_runs', label: '评测运行', path: '/benchmarks' },
  { key: 'reviews', label: '审查事件', path: '/reviews' },
  { key: 'decisions', label: '决策记录', path: '/decisions' },
  { key: 'experiences', label: '长期经验', path: '/knowledge/experiences' },
]

const workflow = [
  { label: '沉淀资料', path: '/sources' },
  { label: '提出假设', path: '/insights' },
  { label: '预注册协议', path: '/research/methodology' },
  { label: '进入队列', path: '/research-queue' },
  { label: '登记轮次', path: '/research/rounds' },
  { label: '记录账本', path: '/sessions' },
  { label: '审计过程', path: '/research/audit' },
  { label: '整理证据', path: '/evidence' },
  { label: '审查经验', path: '/reviews' },
  { label: '形成决策', path: '/decisions' },
]

export function DashboardPage() {
  const status = useQuery({ queryKey: ['status'], queryFn: () => getData<SystemStatus>('/api/v1/system/status') })
  const collections = status.data?.collections || {}

  return (
    <div className="stack">
      <Panel title="平台总览">
        <div className="dashboard-metrics">
          {metrics.map((metric) => (
            <Link className="metric-card" to={metric.path} key={metric.key}>
              <strong>{collections[metric.key] || 0}</strong>
              <span>{metric.label}</span>
            </Link>
          ))}
        </div>
      </Panel>
      <div className="grid-two">
        <Panel title="科研闭环">
          <div className="workflow-strip">
            {workflow.map((item) => (
              <Link to={item.path} key={item.path}>{item.label}</Link>
            ))}
          </div>
        </Panel>
        <Panel title="运行状态">
          <div className="detail-grid">
            <div><strong>{status.data?.status || 'unknown'}</strong><span>API 状态</span></div>
            <div><strong>{status.data?.store || 'unknown'}</strong><span>Store</span></div>
            <div><strong>{Object.keys(collections).length}</strong><span>集合数量</span></div>
          </div>
        </Panel>
      </div>
    </div>
  )
}
