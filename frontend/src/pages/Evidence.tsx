import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button, ErrorMessage, Panel, SelectInput, StatusBadge, TextArea, TextInput } from '@/components/Primitives'
import { getData, getListData, postData, type RecordItem } from '@/lib/api'
import { formatHumanText, labelRecordType, labelTerm } from '@/lib/display'

type EvidenceSummary = {
  claim: string
  total: number
  state: string
  recommended_next_action: string
  stances: Record<string, number>
  confidence: Record<string, number>
  evidence_ids: string[]
  limitations: string[]
  coverage?: {
    evidence_kinds?: Record<string, number>
    evidence_ref_types?: Record<string, number>
    sessions?: string[]
    subjects?: string[]
  }
  quality_gaps?: Array<{
    code?: string
    severity?: string
    message?: string
    evidence_ids?: string[]
  }>
  replication_plan?: Array<{
    action?: string
    endpoint?: string
    reason?: string
    priority?: string
  }>
}

const subjectTypes = [
  { value: 'hypothesis', label: '假设' },
  { value: 'experiment', label: '实验' },
  { value: 'benchmark_run', label: '评测运行' },
  { value: 'artifact', label: '成果引用' },
  { value: 'source', label: '资料' },
  { value: 'experience', label: '长期经验' },
]

const evidenceKinds = [
  { value: 'benchmark_run', label: '评测运行' },
  { value: 'experiment', label: '实验' },
  { value: 'artifact', label: '成果引用' },
  { value: 'source', label: '资料' },
  { value: 'review', label: '审查' },
  { value: 'replication', label: '复现' },
  { value: 'human_assessment', label: '外部评估' },
]

const stances = [
  { value: 'supports', label: '支持' },
  { value: 'contradicts', label: '反证' },
  { value: 'mixed', label: '混合' },
  { value: 'inconclusive', label: '不确定' },
  { value: 'replicates', label: '复现通过' },
  { value: 'fails_to_replicate', label: '复现失败' },
]

const confidenceOptions = [
  { value: 'high', label: '高' },
  { value: 'medium', label: '中' },
  { value: 'low', label: '低' },
  { value: 'unknown', label: '未记录' },
]

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

const stateLabels: Record<string, string> = {
  insufficient: '证据不足',
  contested: '存在冲突',
  contradicted: '已被反证',
  needs_replication: '需要复现',
  supported: '已有支持',
}

const actionLabels: Record<string, string> = {
  create_evidence_record: '写入证据记录',
  investigate_conflict: '排查冲突证据',
  open_review: '进入审查',
  register_replication: '登记复现实验',
  collect_more_evidence: '继续收集证据',
}

const qualityGapLabels: Record<string, string> = {
  missing_replication: '缺少复现',
  conflicting_evidence: '证据冲突',
  single_session_evidence: '单轮证据',
  missing_subject_binding: '对象未绑定',
  missing_limitations: '缺少限制说明',
  medium_or_low_confidence: '置信度不足',
}

const severityLabels: Record<string, string> = {
  high: '高',
  medium: '中',
  low: '低',
}

const replicationActionLabels: Record<string, string> = {
  register_independent_replication: '登记独立复现',
  write_replication_evidence: '写入复现证据',
  collect_cross_session_evidence: '补跨轮次证据',
  open_conflict_review: '开启冲突审查',
}

function formatCountMap(values?: Record<string, number>, labels?: Record<string, string>) {
  const entries = Object.entries(values || {})
  if (!entries.length) return '未记录'
  return entries.map(([key, value]) => `${labels?.[key] || labelRecordType(key)} ${value}`).join('，')
}

export function EvidencePage() {
  const queryClient = useQueryClient()
  const [claim, setClaim] = useState('')
  const [summaryClaim, setSummaryClaim] = useState('')
  const [subjectType, setSubjectType] = useState('hypothesis')
  const [subjectId, setSubjectId] = useState('')
  const [stance, setStance] = useState('supports')
  const [evidenceKind, setEvidenceKind] = useState('benchmark_run')
  const [evidenceId, setEvidenceId] = useState('')
  const [summary, setSummary] = useState('')
  const [limitation, setLimitation] = useState('')
  const [confidence, setConfidence] = useState('medium')
  const evidence = useQuery({ queryKey: ['evidence-records'], queryFn: () => getListData<RecordItem>('/api/v1/evidence-records') })
  const evidenceSummary = useQuery({
    queryKey: ['evidence-summary', summaryClaim],
    queryFn: () => getData<EvidenceSummary>(`/api/v1/evidence-records/summary?claim=${encodeURIComponent(summaryClaim.trim())}`),
    enabled: summaryClaim.trim().length > 0,
  })
  const create = useMutation({
    mutationFn: () => postData('/api/v1/evidence-records', {
      claim,
      subject: subjectId ? { type: subjectType, id: subjectId } : {},
      stance,
      evidence_kind: evidenceKind,
      summary,
      evidence_refs: [{ type: evidenceKind, id: evidenceId }],
      quality: { confidence },
      limitations: limitation ? [limitation] : [],
      reproducibility: { status: stance === 'replicates' || stance === 'fails_to_replicate' ? stance : 'not_tested' },
      recorded_by: { kind: 'external-runtime', id: 'workbench' },
    }),
    onSuccess: () => {
      setSummaryClaim(claim)
      setClaim('')
      setSubjectId('')
      setEvidenceId('')
      setSummary('')
      setLimitation('')
      queryClient.invalidateQueries({ queryKey: ['evidence-records'] })
      queryClient.invalidateQueries({ queryKey: ['evidence-summary'] })
    },
  })
  const summaryData = evidenceSummary.data

  return (
    <div className="grid-two">
      <Panel title="创建证据">
        <form className="form" onSubmit={(event) => { event.preventDefault(); create.mutate() }}>
          <TextInput label="主张" value={claim} onChange={setClaim} placeholder="要支持、反证或复现的科研主张" />
          <SelectInput label="对象类型" value={subjectType} onChange={setSubjectType} options={subjectTypes} />
          <TextInput label="对象标识" value={subjectId} onChange={setSubjectId} placeholder="假设、实验或资料记录标识" />
          <SelectInput label="证据立场" value={stance} onChange={setStance} options={stances} />
          <SelectInput label="证据类型" value={evidenceKind} onChange={setEvidenceKind} options={evidenceKinds} />
          <TextInput label="证据标识" value={evidenceId} onChange={setEvidenceId} placeholder="评测运行、成果或资料记录标识" />
          <SelectInput label="置信度" value={confidence} onChange={setConfidence} options={confidenceOptions} />
          <TextArea label="摘要" value={summary} onChange={setSummary} placeholder="证据如何支持或反驳主张，以及关键结果" />
          <TextInput label="限制" value={limitation} onChange={setLimitation} placeholder="可选：样本量、数据泄漏、外部效度等限制" />
          <Button type="submit" disabled={!claim || !evidenceId || !summary}>写入证据</Button>
        </form>
        <ErrorMessage message={create.error?.message} />
      </Panel>
      <Panel title="证据概览">
        <div className="form">
          <TextInput label="主张查询" value={summaryClaim} onChange={setSummaryClaim} placeholder="输入完整科研主张，按已入库证据聚合" />
          {summaryClaim.trim() && summaryData ? (
            <div className="record-list compact">
              <article className="record-row">
                <div>
                  <div className="record-title">{stateLabels[summaryData.state] || labelTerm(summaryData.state)}</div>
                  <div className="record-meta">证据数量 {summaryData.total}</div>
                  <div className="record-meta">建议动作 {actionLabels[summaryData.recommended_next_action] || formatHumanText(summaryData.recommended_next_action)}</div>
                </div>
                <StatusBadge status={summaryData.state === 'supported' ? 'completed' : summaryData.state === 'contested' ? 'degraded' : 'blocked'} />
              </article>
              <article className="record-row">
                <div>
                  <div className="record-title">立场计数</div>
                  <div className="record-meta">
                    {Object.entries(summaryData.stances).map(([key, value]) => `${stanceLabels[key] || labelTerm(key)} ${value}`).join('，')}
                  </div>
                  <div className="record-meta">
                    置信度 {Object.entries(summaryData.confidence).map(([key, value]) => `${confidenceLabels[key] || labelTerm(key)} ${value}`).join('，') || '未记录'}
                  </div>
                </div>
              </article>
              <article className="record-row">
                <div>
                  <div className="record-title">证据引用</div>
                  <div className="record-meta">{summaryData.evidence_ids.join('，') || '暂无证据'}</div>
                  {summaryData.limitations.length ? <div className="record-meta">限制 {summaryData.limitations.join('，')}</div> : null}
                </div>
              </article>
              <article className="record-row">
                <div>
                  <div className="record-title">覆盖范围</div>
                  <div className="record-meta">证据类型 {formatCountMap(summaryData.coverage?.evidence_kinds)}</div>
                  <div className="record-meta">引用类型 {formatCountMap(summaryData.coverage?.evidence_ref_types)}</div>
                  <div className="record-meta">账本 {summaryData.coverage?.sessions?.join('，') || '未记录'}</div>
                  <div className="record-meta">对象 {summaryData.coverage?.subjects?.join('，') || '未绑定'}</div>
                </div>
              </article>
              <article className="record-row">
                <div>
                  <div className="record-title">质量缺口</div>
                  {summaryData.quality_gaps?.length ? summaryData.quality_gaps.map((gap) => (
                    <div className="record-meta" key={`${gap.code || 'gap'}-${gap.severity || ''}`}>
                      {qualityGapLabels[String(gap.code)] || labelTerm(gap.code)} · 严重度 {severityLabels[String(gap.severity)] || labelTerm(gap.severity)} · {formatHumanText(gap.message || '')}
                      {gap.evidence_ids?.length ? ` · 证据 ${gap.evidence_ids.join('，')}` : ''}
                    </div>
                  )) : <div className="record-meta">暂无质量缺口</div>}
                </div>
              </article>
              <article className="record-row">
                <div>
                  <div className="record-title">复现计划</div>
                  {summaryData.replication_plan?.length ? summaryData.replication_plan.map((item) => (
                    <div className="record-meta" key={`${item.action || 'action'}-${item.endpoint || ''}`}>
                      {replicationActionLabels[String(item.action)] || formatHumanText(item.action || '动作')} · {formatHumanText(item.reason || '')}
                    </div>
                  )) : <div className="record-meta">暂无复现建议</div>}
                </div>
              </article>
            </div>
          ) : <div className="empty">输入主张后查看聚合</div>}
        </div>
        <ErrorMessage message={evidenceSummary.error?.message} />
      </Panel>
      <Panel title="证据列表">
        <div className="record-list">
          {(evidence.data?.items || []).map((evidenceRecord) => {
            const subject = evidenceRecord.subject as { type?: string; id?: string } | undefined
            const evidenceRefs = Array.isArray(evidenceRecord.evidence_refs)
              ? evidenceRecord.evidence_refs as Array<{ type?: string; id?: string }>
              : []
            const quality = evidenceRecord.quality as { confidence?: string } | undefined
            const limitations = Array.isArray(evidenceRecord.limitations)
              ? evidenceRecord.limitations as string[]
              : []
            return (
              <article className="record-row" key={evidenceRecord.id}>
                <div>
                  <div className="record-title">{String(evidenceRecord.claim || evidenceRecord.id)}</div>
                  <div className="record-meta">立场 {stanceLabels[String(evidenceRecord.stance)] || labelTerm(String(evidenceRecord.stance || ''))}</div>
                  <div className="record-meta">对象 {subject?.type ? labelRecordType(subject.type) : '未绑定'} · {subject?.id || '未记录'}</div>
                  <div className="record-meta">证据 {evidenceRefs.map((ref) => `${labelRecordType(ref.type)}：${ref.id || ''}`).join('，') || '未记录'}</div>
                  <div className="record-meta">置信度 {confidenceLabels[String(quality?.confidence)] || '未记录'}</div>
                  <div className="record-meta">摘要 {formatHumanText(evidenceRecord.summary || '')}</div>
                  {limitations.length ? <div className="record-meta">限制 {limitations.map((item) => formatHumanText(item)).join('，')}</div> : null}
                </div>
                <StatusBadge status={typeof evidenceRecord.status === 'string' ? evidenceRecord.status : undefined} />
              </article>
            )
          })}
        </div>
        {!evidence.data?.items.length ? <div className="empty">暂无记录</div> : null}
      </Panel>
    </div>
  )
}
