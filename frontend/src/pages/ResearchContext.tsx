import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { ErrorMessage, Panel, StatusBadge, TextInput } from '@/components/Primitives'
import { getData, type RecordItem } from '@/lib/api'
import { formatHumanText, labelTerm } from '@/lib/display'

type ContextAction = {
  endpoint: string
  reason: string
  priority: string
}

type RiskFlag = {
  collection: string
  id: string
  kind: string
  status: string
  title: string
}

type EvidenceSummary = {
  state: string
  recommended_next_action: string
  total: number
  stances: Record<string, number>
  confidence: Record<string, number>
}

type ResearchContext = {
  query: string
  claim: string
  state: string
  counts: Record<string, number>
  sections: Record<string, RecordItem[]>
  evidence_summary: EvidenceSummary
  risk_flags: RiskFlag[]
  recommended_next_actions: ContextAction[]
  safety: string
}

const stateLabels: Record<string, string> = {
  needs_recovery: '需要恢复',
  contested: '存在冲突',
  needs_replication: '需要复现',
  insufficient: '证据不足',
  needs_next_step: '需要推进',
  ready_for_review: '可进入审查',
}

const sectionLabels: Record<string, string> = {
  sources: '资料',
  insights: '洞察',
  hypotheses: '假设',
  research_questions: '问题',
  method_cards: '方法卡',
  protocols: '协议',
  intake_items: '队列',
  sessions: '账本',
  research_rounds: '轮次',
  events: '事件',
  experiments: '实验',
  artifacts: '成果',
  benchmark_runs: '评测',
  evidence_records: '证据',
  reviews: '审查',
  decisions: '决策',
  experiences: '经验',
}

const stanceLabels: Record<string, string> = {
  supports: '支持',
  contradicts: '反证',
  mixed: '混合',
  inconclusive: '不确定',
  replicates: '复现通过',
  fails_to_replicate: '复现失败',
}

const confidenceLabels: Record<string, string> = {
  high: '高',
  medium: '中',
  low: '低',
  unknown: '未记录',
}

function statusForContext(state?: string) {
  if (state === 'ready_for_review') return 'completed'
  if (state === 'needs_recovery' || state === 'contested') return 'degraded'
  return 'blocked'
}

function recordTitle(item: RecordItem) {
  return formatHumanText(item.title || item.name || item.hypothesis || item.question || item.id)
}

export function ResearchContextPage() {
  const [query, setQuery] = useState('回放')
  const [claim, setClaim] = useState('')
  const path = `/api/v1/research/context?query=${encodeURIComponent(query.trim())}${claim.trim() ? `&claim=${encodeURIComponent(claim.trim())}` : ''}&limit=8`
  const context = useQuery({
    queryKey: ['research-context', query, claim],
    queryFn: () => getData<ResearchContext>(path),
    enabled: query.trim().length > 0,
  })
  const data = context.data
  const counts = data?.counts || {}
  const visibleSections = Object.entries(data?.sections || {}).filter(([, items]) => items.length > 0)

  return (
    <div className="grid-two">
      <Panel title="恢复上下文">
        <form className="form" onSubmit={(event) => event.preventDefault()}>
          <TextInput label="关键词" value={query} onChange={setQuery} placeholder="研究主题、方法、成果、阻塞或实验关键词" />
          <TextInput label="证据主张" value={claim} onChange={setClaim} placeholder="可选：完整科研主张，用于证据概览" />
        </form>
        <div className="detail-grid">
          <div><strong>{data?.state ? stateLabels[data.state] || labelTerm(data.state) : '待查询'}</strong><span>上下文状态</span></div>
          <div><strong>{data?.risk_flags.length || 0}</strong><span>风险数量</span></div>
          <div><strong>{data?.recommended_next_actions.length || 0}</strong><span>建议动作</span></div>
        </div>
        <ErrorMessage message={context.error?.message} />
      </Panel>

      <Panel title="建议动作">
        <div className="record-list">
          {(data?.recommended_next_actions || []).map((action) => (
            <article className="record-row" key={`${action.endpoint}-${action.reason}`}>
              <div>
                <div className="record-title">建议动作</div>
                <div className="record-meta">{formatHumanText(action.reason || '未记录原因')}</div>
              </div>
              <StatusBadge status={action.priority === 'high' ? 'blocked' : 'planned'} />
            </article>
          ))}
        </div>
        {!data?.recommended_next_actions.length ? <div className="empty">暂无建议动作</div> : null}
      </Panel>

      <Panel title="事实计数">
        <div className="detail-grid">
          {Object.entries(sectionLabels).map(([key, label]) => (
            <div key={key}><strong>{counts[key] || 0}</strong><span>{label}</span></div>
          ))}
        </div>
      </Panel>

      <Panel title="证据概览">
        {data ? (
          <div className="record-list">
            <article className="record-row">
              <div>
                <div className="record-title">{stateLabels[data.evidence_summary.state] || labelTerm(data.evidence_summary.state)}</div>
                <div className="record-meta">证据数量 {data.evidence_summary.total}</div>
                <div className="record-meta">
                  {Object.entries(data.evidence_summary.stances).map(([key, value]) => `${stanceLabels[key] || labelTerm(key)} ${value}`).join('，')}
                </div>
                <div className="record-meta">
                  置信度 {Object.entries(data.evidence_summary.confidence).map(([key, value]) => `${confidenceLabels[key] || labelTerm(key)} ${value}`).join('，') || '未记录'}
                </div>
              </div>
              <StatusBadge status={statusForContext(data.evidence_summary.state)} />
            </article>
          </div>
        ) : <div className="empty">输入关键词后查看证据状态</div>}
      </Panel>

      <Panel title="风险标记">
        <div className="record-list">
          {(data?.risk_flags || []).map((flag) => (
            <article className="record-row" key={`${flag.collection}-${flag.id}`}>
              <div>
                <div className="record-title">{formatHumanText(flag.title)}</div>
                <div className="record-meta">{sectionLabels[flag.collection] || labelTerm(flag.collection)} · {labelTerm(flag.kind)} · {flag.id}</div>
              </div>
              <StatusBadge status={flag.status} />
            </article>
          ))}
        </div>
        {!data?.risk_flags.length ? <div className="empty">暂无阻塞或降级记录</div> : null}
      </Panel>

      <Panel title="匹配记录">
        <div className="record-list">
          {visibleSections.slice(0, 8).map(([section, items]) => (
            <article className="record-row" key={section}>
              <div>
                <div className="record-title">{sectionLabels[section] || labelTerm(section)}</div>
                <div className="record-meta">
                  {items.slice(0, 3).map((item) => `${recordTitle(item)} (${item.id})`).join('，')}
                </div>
              </div>
              <StatusBadge status="completed" />
            </article>
          ))}
        </div>
        {!visibleSections.length ? <div className="empty">暂无匹配记录</div> : null}
      </Panel>
    </div>
  )
}
