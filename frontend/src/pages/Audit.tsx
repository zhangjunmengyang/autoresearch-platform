import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { ErrorMessage, Panel, RecordList, StatusBadge, TextInput } from '@/components/Primitives'
import { getData, getListData, type RecordItem } from '@/lib/api'
import { formatHumanText, formatKeyValueSummary, labelTerm } from '@/lib/display'

type AuditExportBundle = {
  bundle_id: string
  generated_at: string
  filters: {
    query: string
    claim: string
    session_id: string
    round_id: string
    limit: number
  }
  manifest: {
    schema: string
    record_counts: Record<string, number>
    included_sections: string[]
    warnings: string[]
  }
  artifact_audit: {
    state: string
    total: number
    issue_counts: Record<string, number>
  }
  review_audit: {
    state: string
    total: number
    issue_counts: Record<string, number>
  }
  integrity: {
    external_reads: boolean
    external_writes: boolean
    included_artifact_refs: string[]
  }
  reproducibility: {
    schema: string
    state: string
    checklist: Array<{
      id: string
      label: string
      status: string
      severity: string
      evidence: string[]
      detail: string
    }>
    external_artifacts: Array<{
      id: string
      title?: string
      uri?: string
      sha256?: string
      storage?: string
      requires_external_verification: boolean
      platform_read: boolean
    }>
    handoff_steps: string[]
    safety: string
  }
  recommended_next_actions: Array<{
    action?: string
    endpoint?: string
    reason?: string
    priority?: string
  }>
  safety: string
}

const sectionLabels: Record<string, string> = {
  sources: '资料',
  insights: '洞察',
  hypotheses: '假设',
  research_questions: '问题',
  method_cards: '方法',
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

function formatCounts(counts: Record<string, number>) {
  const entries = Object.entries(counts).filter(([, count]) => count > 0)
  if (!entries.length) return '暂无匹配记录'
  return entries.map(([key, count]) => `${sectionLabels[key] || labelTerm(key)} ${count}`).join('，')
}

export function AuditPage() {
  const [query, setQuery] = useState('')
  const [claim, setClaim] = useState('')
  const [sessionId, setSessionId] = useState('')
  const [roundId, setRoundId] = useState('')
  const suffix = query ? `?q=${encodeURIComponent(query)}` : ''
  const events = useQuery({
    queryKey: ['research-events', query],
    queryFn: () => getListData<RecordItem>(`/api/v1/research/events${suffix}`),
  })
  const experiments = useQuery({
    queryKey: ['research-experiments', query],
    queryFn: () => getListData<RecordItem>(`/api/v1/research/experiments${suffix}`),
  })
  const exportPath = `/api/v1/research/audit/export?query=${encodeURIComponent(query.trim())}${claim.trim() ? `&claim=${encodeURIComponent(claim.trim())}` : ''}${sessionId.trim() ? `&session_id=${encodeURIComponent(sessionId.trim())}` : ''}${roundId.trim() ? `&round_id=${encodeURIComponent(roundId.trim())}` : ''}&limit=20`
  const exportBundle = useQuery({
    queryKey: ['research-audit-export', query, claim, sessionId, roundId],
    queryFn: () => getData<AuditExportBundle>(exportPath),
    enabled: query.trim().length > 0,
  })
  const bundle = exportBundle.data

  return (
    <div className="grid-two">
      <Panel title="审计筛选">
        <form className="form" onSubmit={(event) => event.preventDefault()}>
          <TextInput label="关键词" value={query} onChange={setQuery} placeholder="阻塞、实验假设、账本、结果摘要" />
          <TextInput label="证据主张" value={claim} onChange={setClaim} placeholder="可选：完整科研主张" />
          <TextInput label="账本标识" value={sessionId} onChange={setSessionId} placeholder="可选：研究账本标识" />
          <TextInput label="研究轮次" value={roundId} onChange={setRoundId} placeholder="可选：研究轮次标识" />
        </form>
        <div className="detail-grid">
          <div><strong>{events.data?.total || 0}</strong><span>过程事件</span></div>
          <div><strong>{experiments.data?.total || 0}</strong><span>实验记录</span></div>
          <div><strong>只读</strong><span>审计模式</span></div>
        </div>
      </Panel>
      <Panel title="说明">
        <p className="panel-copy">
          过程审计用于跨账本恢复失败尝试、阻塞原因、工具运行、外部指令和实验结果。这里不执行实验，也不修改外部运行状态。
        </p>
      </Panel>
      <Panel title="审计导出包">
        {bundle ? (
          <div className="record-list compact">
            <article className="record-row">
              <div>
                <div className="record-title">导出清单</div>
                <div className="record-meta">导出包 {bundle.bundle_id}</div>
                <div className="record-meta">结构合同 已生成</div>
                <div className="record-meta">范围 {formatCounts(bundle.manifest.record_counts)}</div>
                <div className="record-meta">成果引用 {bundle.integrity.included_artifact_refs.join('，') || '无'}</div>
              </div>
              <StatusBadge status={bundle.manifest.warnings.length ? 'degraded' : 'completed'} />
            </article>
            <article className="record-row">
              <div>
                <div className="record-title">质量门</div>
                <div className="record-meta">成果审计 {labelTerm(bundle.artifact_audit.state)} · 数量 {bundle.artifact_audit.total}</div>
                <div className="record-meta">审查审计 {labelTerm(bundle.review_audit.state)} · 数量 {bundle.review_audit.total}</div>
                <div className="record-meta">外部读取 {bundle.integrity.external_reads ? '有' : '无'} · 外部写入 {bundle.integrity.external_writes ? '有' : '无'}</div>
              </div>
              <StatusBadge status={bundle.artifact_audit.state === 'ready' && bundle.review_audit.state === 'ready' ? 'completed' : 'degraded'} />
            </article>
            <article className="record-row">
              <div>
                <div className="record-title">复现交接包</div>
                <div className="record-meta">结构合同 已生成</div>
                <div className="record-meta">外部成果 {bundle.reproducibility.external_artifacts.length} · 平台读取 {bundle.reproducibility.external_artifacts.some((artifact) => artifact.platform_read) ? '有' : '无'}</div>
                <div className="record-meta">安全边界 {formatHumanText(bundle.reproducibility.safety)}</div>
              </div>
              <StatusBadge status={bundle.reproducibility.state} />
            </article>
            <article className="record-row">
              <div>
                <div className="record-title">复现检查清单</div>
                {bundle.reproducibility.checklist.map((check) => (
                  <div className="record-meta" key={check.id}>
                    {formatHumanText(check.label)} · {labelTerm(check.status)} · {formatHumanText(check.detail)}
                  </div>
                ))}
              </div>
            </article>
            <article className="record-row">
              <div>
                <div className="record-title">外部成果验证</div>
                {bundle.reproducibility.external_artifacts.length ? bundle.reproducibility.external_artifacts.map((artifact) => (
                  <div className="record-meta" key={artifact.id}>
                    {artifact.title || artifact.id} · {artifact.uri || '无地址'} · {artifact.requires_external_verification ? '需外部验证' : '无需外部验证'}
                  </div>
                )) : <div className="record-meta">暂无外部成果引用</div>}
              </div>
            </article>
            <article className="record-row">
              <div>
                <div className="record-title">交接步骤</div>
                {bundle.reproducibility.handoff_steps.map((step) => (
                  <div className="record-meta" key={step}>{formatHumanText(step)}</div>
                ))}
              </div>
            </article>
            <article className="record-row">
              <div>
                <div className="record-title">建议动作</div>
                {bundle.recommended_next_actions.length ? bundle.recommended_next_actions.map((action) => (
                  <div className="record-meta" key={`${action.endpoint}-${action.reason}`}>
                    {formatHumanText(action.reason || action.action || '未记录原因')}
                  </div>
                )) : <div className="record-meta">暂无建议动作</div>}
              </div>
            </article>
          </div>
        ) : <div className="empty">输入关键词后生成只读审计导出包</div>}
        <ErrorMessage message={exportBundle.error?.message} />
      </Panel>
      <Panel title="过程事件">
        <div className="record-list compact">
          {(events.data?.items || []).map((event) => (
            <article className="record-row" key={event.id}>
              <div>
                <div className="record-title">{String(event.title || event.event_type || event.id)}</div>
                <div className="record-meta">类型 {labelTerm(String(event.event_type || '未记录'))}</div>
                <div className="record-meta">账本 {String(event.session_id || '未绑定')}</div>
                <div className="record-meta">载荷摘要 {formatKeyValueSummary(event.payload)}</div>
              </div>
            </article>
          ))}
        </div>
        {!events.data?.items.length ? <RecordList items={[]} /> : null}
      </Panel>
      <Panel title="实验记录">
        <div className="record-list compact">
          {(experiments.data?.items || []).map((experiment) => (
            <article className="record-row" key={experiment.id}>
              <div>
                <div className="record-title">{String(experiment.hypothesis || experiment.title || experiment.id)}</div>
                <div className="record-meta">账本 {String(experiment.session_id || '未绑定')}</div>
                <div className="record-meta">预期 {formatHumanText(experiment.expected_effect || '')}</div>
                <div className="record-meta">结果 {formatHumanText(experiment.result_summary || '')}</div>
              </div>
              <StatusBadge status={typeof experiment.status === 'string' ? experiment.status : undefined} />
            </article>
          ))}
        </div>
        {!experiments.data?.items.length ? <RecordList items={[]} /> : null}
      </Panel>
    </div>
  )
}
