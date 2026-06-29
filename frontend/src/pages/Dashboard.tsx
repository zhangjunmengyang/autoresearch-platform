import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Panel } from '@/components/Primitives'
import { getData } from '@/lib/api'

type SystemStatus = {
  status: string
  store: string
  collections: Record<string, number>
}

const loopCards = [
  { label: 'Idea Pool', subtitle: '想法来源', path: '/sources', countKeys: ['sources', 'insights'] },
  { label: 'Hypothesis', subtitle: '可验证假设', path: '/insights', countKeys: ['hypotheses'] },
  { label: 'Plan', subtitle: '最小实验计划', path: '/research/methodology', countKeys: ['research_questions', 'protocols'] },
  { label: 'Experiment', subtitle: '外部运行', path: '/sessions', countKeys: ['sessions', 'research_rounds', 'experiments'] },
  { label: 'Result', subtitle: '结果引用', path: '/artifacts', countKeys: ['artifacts', 'benchmark_runs'] },
  { label: 'Review', subtitle: '复盘审查', path: '/evidence', countKeys: ['evidence_records', 'reviews'] },
  { label: 'Decision', subtitle: '迭代判断', path: '/decisions', countKeys: ['decisions'] },
  { label: 'Lesson', subtitle: '可复用经验', path: '/knowledge/experiences', countKeys: ['experiences'] },
]

export function DashboardPage() {
  const status = useQuery({ queryKey: ['status'], queryFn: () => getData<SystemStatus>('/api/v1/system/status') })
  const collections = status.data?.collections || {}
  const countFor = (keys: string[]) => keys.reduce((total, key) => total + (collections[key] || 0), 0)

  return (
    <div className="stack">
      <Panel title="方法论闭环">
        <div className="dashboard-metrics">
          {loopCards.map((card) => (
            <Link className="metric-card" to={card.path} key={card.label}>
              <strong>{countFor(card.countKeys)}</strong>
              <span>{card.label}</span>
              <small>{card.subtitle}</small>
            </Link>
          ))}
        </div>
      </Panel>
      <div className="grid-two">
        <Panel title="主路径">
          <div className="workflow-strip">
            {loopCards.map((item) => (
              <Link to={item.path} key={item.label}>{item.label}</Link>
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
