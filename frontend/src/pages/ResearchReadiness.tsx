import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Button, ErrorMessage, Panel, SelectInput, StatusBadge, TextInput, WarningList } from '@/components/Primitives'
import { requestEnvelope, type RecordItem } from '@/lib/api'
import { formatHumanText, labelRecordType, labelTerm } from '@/lib/display'

type ReadinessCheck = {
  id: string
  status: string
  title: string
  detail: string
  severity?: string
  recommended_action?: ReadinessAction
}

type ReadinessAction = {
  action?: string
  endpoint?: string
  reason?: string
}

type ReadinessResult = {
  query: string
  claim: string
  stage: string
  state: string
  checks: ReadinessCheck[]
  blocking_gaps: ReadinessCheck[]
  warning_gaps: ReadinessCheck[]
  warnings: string[]
  round_trace?: {
    round?: RecordItem
    trace?: {
      unresolved_refs?: Array<Record<string, string>>
    }
  } | null
  recommended_next_actions: ReadinessAction[]
  safety: string
}

type ReadinessParams = {
  query: string
  claim: string
  roundId: string
  stage: string
}

const stageOptions = [
  { value: 'before_experiment', label: '实验前' },
  { value: 'before_review', label: '审查前' },
  { value: 'before_decision', label: '决策前' },
  { value: 'before_curation', label: '经验维护前' },
]

function formatStage(stage: string) {
  return stageOptions.find((option) => option.value === stage)?.label || labelTerm(stage)
}

function buildReadinessPath(params: ReadinessParams) {
  const search = new URLSearchParams({
    query: params.query,
    claim: params.claim,
    stage: params.stage,
  })
  if (params.roundId) {
    search.set('round_id', params.roundId)
  }
  return `/api/v1/research/readiness?${search.toString()}`
}

export function ResearchReadinessPage() {
  const [query, setQuery] = useState('')
  const [claim, setClaim] = useState('')
  const [roundId, setRoundId] = useState('')
  const [stage, setStage] = useState('before_decision')
  const [params, setParams] = useState<ReadinessParams | null>(null)

  const readiness = useQuery({
    queryKey: ['research-readiness', params],
    enabled: Boolean(params),
    queryFn: () => requestEnvelope<ReadinessResult>(buildReadinessPath(params as ReadinessParams)),
  })

  const result = readiness.data?.data

  return (
    <div className="grid-two">
      <Panel title="就绪检查">
        <form
          className="form"
          onSubmit={(event) => {
            event.preventDefault()
            setParams({ query, claim, roundId, stage })
          }}
        >
          <TextInput label="研究查询" value={query} onChange={setQuery} placeholder="例如：记忆回放" />
          <TextInput label="科研主张" value={claim} onChange={setClaim} placeholder="例如：回放提升延迟回忆" />
          <TextInput label="轮次标识" value={roundId} onChange={setRoundId} placeholder="可选：研究轮次标识" />
          <SelectInput label="检查阶段" value={stage} onChange={setStage} options={stageOptions} />
          <Button type="submit" disabled={!query}>检查</Button>
        </form>
        <p className="panel-copy">
          就绪检查只读取上下文、轮次追踪包、实验、成果、证据和决策引用，不执行实验、不调用模型、不创建工作流。
        </p>
        <ErrorMessage message={readiness.error?.message} />
      </Panel>

      <Panel title="检查结果">
        <WarningList warnings={readiness.data?.warnings} />
        <WarningList warnings={result?.warnings} />
        {!result ? <div className="empty">输入查询后运行就绪检查</div> : null}
        {result ? (
          <div className="record-list">
            <article className="record-row">
              <div>
                <div className="record-title">状态 {labelTerm(result.state)}</div>
                <div className="record-meta">阶段 {formatStage(result.stage)} · 查询 {formatHumanText(result.query)}</div>
              </div>
              <StatusBadge status={result.state === 'ready' ? 'completed' : result.state} />
            </article>

            <article className="record-row">
              <div>
                <div className="record-title">阻塞缺口</div>
                <div className="record-meta">
                  {result.blocking_gaps.length
                    ? result.blocking_gaps.map((gap) => `${formatHumanText(gap.title)}：${formatHumanText(gap.detail)}`).join('，')
                    : '无'}
                </div>
              </div>
            </article>

            <article className="record-row">
              <div>
                <div className="record-title">检查项</div>
                <div className="record-meta">
                  {result.checks.map((check) => `${formatHumanText(check.title)}：${labelTerm(check.status)}`).join('，')}
                </div>
              </div>
            </article>

            <article className="record-row">
              <div>
                <div className="record-title">未解析引用</div>
                <div className="record-meta">
                  {result.round_trace?.trace?.unresolved_refs?.length
                    ? result.round_trace.trace.unresolved_refs.map((ref) => `${labelTerm(ref.field)}：${labelRecordType(ref.type)}：${ref.id}：${formatHumanText(ref.reason)}`).join('，')
                    : '无'}
                </div>
              </div>
            </article>

            <article className="record-row">
              <div>
                <div className="record-title">建议动作</div>
                <div className="record-meta">
                  {result.recommended_next_actions.length
                    ? result.recommended_next_actions.map((action) => `${formatHumanText(action.action || '动作')}：${formatHumanText(action.reason || '未记录原因')}`).join('，')
                    : '暂无'}
                </div>
              </div>
            </article>
          </div>
        ) : null}
      </Panel>
    </div>
  )
}
