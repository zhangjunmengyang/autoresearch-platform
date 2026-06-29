import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button, ErrorMessage, Panel, SelectInput, StatusBadge, TextArea, TextInput } from '@/components/Primitives'
import { getData, getListData, postData, type RecordItem } from '@/lib/api'
import { formatHumanText, labelRecordType, labelTerm } from '@/lib/display'

type ReviewAuditIssue = {
  code?: string
  severity?: string
  message?: string
}

type ReviewAuditItem = {
  review_id?: string
  subject?: { type?: string; id?: string }
  reviewer?: { kind?: string; id?: string }
  verdict?: string
  status?: string
  state?: string
  issues?: ReviewAuditIssue[]
}

type ReviewAudit = {
  state: string
  total: number
  issue_counts: Record<string, number>
  review_ids_with_issues: string[]
  items: ReviewAuditItem[]
  recommended_next_actions: Array<{
    endpoint?: string
    reason?: string
    priority?: string
  }>
}

const subjectTypes = [
  { value: 'insight', label: '洞察' },
  { value: 'experiment', label: '实验' },
  { value: 'benchmark_run', label: '评测运行' },
  { value: 'experience', label: '长期经验' },
  { value: 'artifact', label: '成果引用' },
]

const verdicts = [
  { value: 'completed', label: '通过' },
  { value: 'degraded', label: '降级' },
  { value: 'blocked', label: '阻塞' },
  { value: 'rejected', label: '拒绝' },
]

const evidenceTypes = [
  { value: 'evidence_record', label: '证据记录' },
  { value: 'benchmark_run', label: '评测运行' },
  { value: 'artifact', label: '成果引用' },
  { value: 'experiment', label: '实验' },
]

const issueLabels: Record<string, string> = {
  missing_subject: '缺少对象',
  missing_reviewer: '缺少审查者',
  missing_comments: '缺少说明',
  missing_evidence_refs: '缺少证据引用',
  missing_score_or_concerns: '缺少分数或风险',
  completed_with_high_concerns: '通过但有高风险',
}

const severityLabels: Record<string, string> = {
  high: '高',
  medium: '中',
  low: '低',
}

function formatIssueCounts(counts: Record<string, number>) {
  const entries = Object.entries(counts)
  if (!entries.length) return '暂无质量缺口'
  return entries.map(([code, count]) => `${issueLabels[code] || labelTerm(code)} ${count}`).join('，')
}

export function ReviewsPage() {
  const queryClient = useQueryClient()
  const [query, setQuery] = useState('')
  const [subjectType, setSubjectType] = useState('benchmark_run')
  const [subjectId, setSubjectId] = useState('')
  const [evidenceType, setEvidenceType] = useState('evidence_record')
  const [evidenceId, setEvidenceId] = useState('')
  const [reviewer, setReviewer] = useState('自动审查器')
  const [verdict, setVerdict] = useState('completed')
  const [score, setScore] = useState('80')
  const [comments, setComments] = useState('')
  const reviews = useQuery({
    queryKey: ['reviews', query],
    queryFn: () => getListData<RecordItem>(`/api/v1/reviews${query ? `?q=${encodeURIComponent(query)}` : ''}`),
  })
  const audit = useQuery({
    queryKey: ['review-audit', query],
    queryFn: () => getData<ReviewAudit>(`/api/v1/reviews/audit${query ? `?q=${encodeURIComponent(query)}` : ''}`),
  })
  const create = useMutation({
    mutationFn: () => postData('/api/v1/reviews', {
      subject: { type: subjectType, id: subjectId },
      reviewer: { kind: 'critic', id: reviewer },
      verdict,
      score: score ? Number(score) : undefined,
      comments,
      evidence_refs: [{ type: evidenceType, id: evidenceId }],
    }),
    onSuccess: () => {
      setQuery(evidenceId || subjectId)
      setSubjectId('')
      setEvidenceId('')
      setComments('')
      queryClient.invalidateQueries({ queryKey: ['reviews'] })
      queryClient.invalidateQueries({ queryKey: ['review-audit'] })
    },
  })
  const auditData = audit.data

  return (
    <div className="grid-two">
      <Panel title="创建审查">
        <form className="form" onSubmit={(event) => { event.preventDefault(); create.mutate() }}>
          <SelectInput label="对象类型" value={subjectType} onChange={setSubjectType} options={subjectTypes} />
          <TextInput label="对象标识" value={subjectId} onChange={setSubjectId} placeholder="评测运行、实验或经验记录标识" />
          <SelectInput label="证据类型" value={evidenceType} onChange={setEvidenceType} options={evidenceTypes} />
          <TextInput label="证据标识" value={evidenceId} onChange={setEvidenceId} placeholder="证据、评测运行或成果记录标识" />
          <TextInput label="审查者" value={reviewer} onChange={setReviewer} placeholder="自动审查器或外部运行方名称" />
          <SelectInput label="结论" value={verdict} onChange={setVerdict} options={verdicts} />
          <TextInput label="分数" value={score} onChange={setScore} placeholder="0-100，可选" />
          <TextArea label="说明" value={comments} onChange={setComments} placeholder="证据是否充分、是否可复现、是否需要降级" />
          <Button type="submit" disabled={!subjectId || !evidenceId || !reviewer || !comments}>写入审查</Button>
        </form>
        <ErrorMessage message={create.error?.message} />
      </Panel>
      <Panel title="审查质量门">
        <div className="form">
          <TextInput label="审计查询" value={query} onChange={setQuery} placeholder="审查、证据、对象或审查者关键词" />
          {auditData ? (
            <div className="record-list compact">
              <article className="record-row">
                <div>
                  <div className="record-title">质量缺口</div>
                  <div className="record-meta">审查数量 {auditData.total}</div>
                  <div className="record-meta">{formatIssueCounts(auditData.issue_counts)}</div>
                  <div className="record-meta">问题审查 {auditData.review_ids_with_issues.join('，') || '无'}</div>
                </div>
                <StatusBadge status={auditData.state === 'ready' ? 'completed' : auditData.state} />
              </article>
              {(auditData.items || []).filter((item) => item.issues?.length).map((item) => (
                <article className="record-row" key={item.review_id}>
                  <div>
                    <div className="record-title">{item.subject?.type ? labelRecordType(item.subject.type) : '对象'} · {item.subject?.id || item.review_id}</div>
                    <div className="record-meta">审查 {item.review_id || '未记录'} · 审查者 {item.reviewer?.id || labelTerm(item.reviewer?.kind)}</div>
                    {(item.issues || []).map((issue) => (
                      <div className="record-meta" key={`${item.review_id}-${issue.code}`}>
                        {issueLabels[String(issue.code)] || labelTerm(issue.code)} · 严重度 {severityLabels[String(issue.severity)] || labelTerm(issue.severity)} · {formatHumanText(issue.message || '')}
                      </div>
                    ))}
                  </div>
                  <StatusBadge status={item.state === 'ready' ? 'completed' : item.state} />
                </article>
              ))}
              <article className="record-row">
                <div>
                  <div className="record-title">建议动作</div>
                  {auditData.recommended_next_actions.length ? auditData.recommended_next_actions.map((action) => (
                    <div className="record-meta" key={`${action.endpoint}-${action.reason}`}>
                      {formatHumanText(action.reason || '未记录原因')}
                    </div>
                  )) : <div className="record-meta">暂无建议动作</div>}
                </div>
              </article>
            </div>
          ) : <div className="empty">正在读取审查质量门</div>}
        </div>
        <ErrorMessage message={audit.error?.message} />
      </Panel>
      <Panel title="审查列表">
        <div className="record-list">
          {(reviews.data?.items || []).map((review) => {
            const subject = review.subject as { type?: string; id?: string } | undefined
            const reviewerInfo = review.reviewer as { id?: string; kind?: string } | undefined
            const evidenceRefs = Array.isArray(review.evidence_refs)
              ? review.evidence_refs as Array<{ type?: string; id?: string }>
              : []
            return (
              <article className="record-row" key={review.id}>
                <div>
                  <div className="record-title">{subject?.type ? labelRecordType(subject.type) : '对象'} · {subject?.id || review.id}</div>
                  <div className="record-meta">审查者 {reviewerInfo?.id || labelTerm(reviewerInfo?.kind)}</div>
                  <div className="record-meta">证据 {evidenceRefs.map((ref) => `${labelRecordType(ref.type)}：${ref.id || ''}`).join('，') || '未记录'}</div>
                  <div className="record-meta">分数 {String(review.score ?? '未记录')}</div>
                  <div className="record-meta">说明 {formatHumanText(review.comments || '')}</div>
                </div>
                <StatusBadge status={typeof review.status === 'string' ? review.status : typeof review.verdict === 'string' ? review.verdict : undefined} />
              </article>
            )
          })}
        </div>
        {!reviews.data?.items.length ? <div className="empty">暂无记录</div> : null}
      </Panel>
    </div>
  )
}
