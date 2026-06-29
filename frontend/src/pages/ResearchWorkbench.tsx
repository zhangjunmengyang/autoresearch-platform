import { Link } from 'react-router-dom'
import { Panel } from '@/components/Primitives'

const loopActions = [
  { path: '/sources', title: 'Idea Pool', copy: '管理论文、repo、benchmark gap、研究员想法和历史失败等假设来源。' },
  { path: '/insights', title: 'Hypothesis', copy: '把 idea 收敛成可验证假设。' },
  { path: '/research/methodology', title: 'Plan', copy: '登记最小实验计划、接受/拒绝标准和结果要求。' },
  { path: '/sessions', title: 'Experiment', copy: '记录外部 Runtime 的执行过程。' },
  { path: '/artifacts', title: 'Result', copy: '登记分数、日志、图表、报告等外部结果引用。' },
  { path: '/evidence', title: 'Review', copy: '复盘结果、证据和质量缺口。' },
  { path: '/decisions', title: 'Decision', copy: '写入 keep、discard、continue、blocked 等迭代判断。' },
  { path: '/knowledge/experiences', title: 'Lesson', copy: '沉淀可复用经验，指导下一轮 hypothesis 或 plan。' },
]

const auditActions = [
  { path: '/research/context', title: '上下文恢复', copy: '开题前查看已有资料、证据状态和风险。' },
  { path: '/research/readiness', title: '就绪检查', copy: '实验、审查、决策前检查阻塞缺口。' },
  { path: '/research/rounds', title: '轮次追踪', copy: '追踪方案、分支、commit、实验和证据引用。' },
  { path: '/research/audit', title: '审计导出', copy: '查看事件、实验和交接审计包。' },
  { path: '/benchmarks', title: '评测合同', copy: '登记 benchmark suite 与运行结果。' },
  { path: '/reviews', title: '审查质量门', copy: '记录自动 critic、外部 Runtime 或人工复核。' },
]

function LinkGrid({ items }: { items: Array<{ path: string; title: string; copy: string }> }) {
  return (
    <div className="link-grid">
      {items.map((item) => (
        <Link className="link-card" to={item.path} key={item.path}>
          <strong>{item.title}</strong>
          <span>{item.copy}</span>
        </Link>
      ))}
    </div>
  )
}

export function ResearchWorkbenchPage() {
  return (
    <div className="stack">
      <Panel title="AutoResearch 闭环">
        <LinkGrid items={loopActions} />
      </Panel>
      <Panel title="高级审计">
        <LinkGrid items={auditActions} />
      </Panel>
    </div>
  )
}
