import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button, ErrorMessage, Panel, SelectInput, StatusBadge, TextArea, TextInput } from '@/components/Primitives'
import { getListData, postData, type RecordItem } from '@/lib/api'
import { formatHumanText, labelRecordType } from '@/lib/display'

const subjectTypes = [
  { value: 'hypothesis', label: '假设' },
  { value: 'experiment', label: '实验' },
  { value: 'benchmark_run', label: '评测运行' },
  { value: 'review', label: '审查' },
  { value: 'artifact', label: '成果引用' },
  { value: 'experience', label: '长期经验' },
]

const evidenceTypes = [
  { value: 'review', label: '审查' },
  { value: 'benchmark_run', label: '评测运行' },
  { value: 'experiment', label: '实验' },
  { value: 'artifact', label: '成果引用' },
  { value: 'source', label: '资料' },
  { value: 'session', label: '账本' },
]

const decisionOptions = [
  { value: 'accept', label: '接受' },
  { value: 'reject', label: '拒绝' },
  { value: 'continue', label: '继续' },
  { value: 'block', label: '阻塞' },
  { value: 'supersede', label: '替代' },
  { value: 'archive', label: '归档' },
]

const decisionLabels: Record<string, string> = {
  accept: '接受',
  reject: '拒绝',
  continue: '继续',
  block: '阻塞',
  supersede: '替代',
  archive: '归档',
}

export function DecisionsPage() {
  const queryClient = useQueryClient()
  const [subjectType, setSubjectType] = useState('hypothesis')
  const [subjectId, setSubjectId] = useState('')
  const [decision, setDecision] = useState('continue')
  const [rationale, setRationale] = useState('')
  const [evidenceType, setEvidenceType] = useState('review')
  const [evidenceId, setEvidenceId] = useState('')
  const [nextStep, setNextStep] = useState('')
  const decisions = useQuery({ queryKey: ['decisions'], queryFn: () => getListData<RecordItem>('/api/v1/decisions') })
  const create = useMutation({
    mutationFn: () => postData('/api/v1/decisions', {
      subject: { type: subjectType, id: subjectId },
      decision,
      rationale,
      evidence_refs: [{ type: evidenceType, id: evidenceId }],
      next_steps: nextStep ? [nextStep] : [],
      decided_by: { kind: 'external-runtime', id: 'workbench' },
    }),
    onSuccess: () => {
      setSubjectId('')
      setRationale('')
      setEvidenceId('')
      setNextStep('')
      queryClient.invalidateQueries({ queryKey: ['decisions'] })
    },
  })

  return (
    <div className="grid-two">
      <Panel title="创建决策">
        <form className="form" onSubmit={(event) => { event.preventDefault(); create.mutate() }}>
          <SelectInput label="对象类型" value={subjectType} onChange={setSubjectType} options={subjectTypes} />
          <TextInput label="对象标识" value={subjectId} onChange={setSubjectId} placeholder="假设、实验或评测运行记录标识" />
          <SelectInput label="决策" value={decision} onChange={setDecision} options={decisionOptions} />
          <TextArea label="判断依据" value={rationale} onChange={setRationale} placeholder="说明证据、取舍、风险和后续动作" />
          <SelectInput label="证据类型" value={evidenceType} onChange={setEvidenceType} options={evidenceTypes} />
          <TextInput label="证据标识" value={evidenceId} onChange={setEvidenceId} placeholder="审查、评测运行或成果记录标识" />
          <TextInput label="下一步" value={nextStep} onChange={setNextStep} placeholder="可选：继续复现、补充对照、归档主题" />
          <Button type="submit" disabled={!subjectId || !rationale || !evidenceId}>写入决策</Button>
        </form>
        <ErrorMessage message={create.error?.message} />
      </Panel>
      <Panel title="决策列表">
        <div className="record-list">
          {(decisions.data?.items || []).map((decisionRecord) => {
            const subject = decisionRecord.subject as { type?: string; id?: string } | undefined
            const evidenceRefs = Array.isArray(decisionRecord.evidence_refs)
              ? decisionRecord.evidence_refs as Array<{ type?: string; id?: string }>
              : []
            const nextSteps = Array.isArray(decisionRecord.next_steps)
              ? decisionRecord.next_steps as string[]
              : []
            return (
              <article className="record-row" key={decisionRecord.id}>
                <div>
                  <div className="record-title">{subject?.type ? labelRecordType(subject.type) : '对象'} · {subject?.id || decisionRecord.id}</div>
                  <div className="record-meta">决策 {decisionLabels[String(decisionRecord.decision)] || String(decisionRecord.decision || '')}</div>
                  <div className="record-meta">依据 {formatHumanText(decisionRecord.rationale || '')}</div>
                  <div className="record-meta">证据 {evidenceRefs.map((ref) => `${labelRecordType(ref.type)}：${ref.id || ''}`).join('，') || '未记录'}</div>
                  {nextSteps.length ? <div className="record-meta">下一步 {nextSteps.map((step) => formatHumanText(step)).join('，')}</div> : null}
                </div>
                <StatusBadge status={typeof decisionRecord.status === 'string' ? decisionRecord.status : undefined} />
              </article>
            )
          })}
        </div>
        {!decisions.data?.items.length ? <div className="empty">暂无记录</div> : null}
      </Panel>
    </div>
  )
}
