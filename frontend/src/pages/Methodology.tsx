import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button, ErrorMessage, Panel, RecordList, StatusBadge, TextArea, TextInput } from '@/components/Primitives'
import { getData, getListData, postData, type RecordItem } from '@/lib/api'

type DesignAuditItem = {
  id: string
  question?: string
  title?: string
  question_id?: string
  status?: string
  state: string
  issues: Array<{ code: string; severity: string; message: string }>
  contract_summary: Record<string, unknown>
}

type DesignAudit = {
  state: string
  issue_counts: Record<string, number>
  question_ids_with_issues: string[]
  hypothesis_ids_with_issues: string[]
  protocol_ids_with_issues: string[]
  questions: DesignAuditItem[]
  hypotheses: DesignAuditItem[]
  protocols: DesignAuditItem[]
  recommended_next_actions: Array<{ endpoint: string; reason: string; priority: string }>
}

type MethodTemplate = {
  id: string
  title: string
  when_to_use: string
  design_questions: string[]
  required_records: string[]
  protocol_defaults: {
    one_change?: string
    controls?: string[]
    acceptance_criteria?: Record<string, unknown>
    rejection_criteria?: Record<string, unknown>
  }
  artifact_requirements: string[]
  evidence_expectations: string[]
  review_gates: string[]
  next_endpoints: string[]
}

type MethodTemplates = {
  schema: string
  state: string
  templates: MethodTemplate[]
  recommended_next_actions: Array<{ endpoint: string; reason: string; priority: string }>
  safety: string
}

const issueLabels: Record<string, string> = {
  question_missing_success_criteria: '研究问题缺少成功标准',
  question_missing_rationale: '研究问题缺少立项理由',
  hypothesis_missing_expected_effect: '假设缺少预期效应',
  hypothesis_missing_acceptance_criteria: '假设缺少接受标准',
  hypothesis_missing_rejection_criteria: '假设缺少拒绝标准',
  hypothesis_missing_source_trace: '假设缺少来源链路',
  protocol_missing_controls: '协议缺少对照',
  protocol_missing_acceptance_criteria: '协议缺少接受标准',
  protocol_missing_rejection_criteria: '协议缺少拒绝标准',
  protocol_missing_artifact_requirements: '协议缺少成果要求',
  protocol_missing_method_link: '协议缺少方法卡关联',
  protocol_missing_hypothesis_link: '协议缺少假设关联',
}

const summaryLabels: Record<string, string> = {
  has_success_criteria: '有成功标准',
  has_rationale: '有立项理由',
  program_id: '计划编号',
  has_expected_effect: '有预期效应',
  has_acceptance_criteria: '有接受标准',
  has_rejection_criteria: '有拒绝标准',
  source_ref_count: '来源引用数',
  has_method_id: '已关联方法卡',
  has_hypothesis_id: '已关联假设',
  controls: '对照数量',
  artifact_requirements: '成果要求数量',
  one_change: '唯一变化',
}

const templateTitleLabels: Record<string, string> = {
  literature_synthesis: '文献综合',
  reproduction: '复现实验',
  ablation: '消融实验',
  benchmark_comparison: '评测对比',
  failure_analysis: '失败分析',
}

function formatIssueCounts(counts?: Record<string, number>) {
  if (!counts || !Object.keys(counts).length) return '无缺口'
  return Object.entries(counts).map(([key, value]) => `${issueLabels[key] || key} ${value}`).join('，')
}

function formatContractSummary(summary: Record<string, unknown>) {
  const entries = Object.entries(summary)
  if (!entries.length) return '无'
  return entries.map(([key, value]) => {
    const label = summaryLabels[key] || key
    if (typeof value === 'boolean') return `${label}：${value ? '是' : '否'}`
    if (value === '') return `${label}：未填写`
    return `${label}：${String(value)}`
  }).join('，')
}

function formatList(values?: string[]) {
  return values?.length ? values.join('，') : '无'
}

function renderAuditItem(item: DesignAuditItem, fallbackTitle: string) {
  const summary = item.contract_summary || {}
  return (
    <article className="record-row" key={item.id}>
      <div>
        <div className="record-title">{item.title || item.question || item.question_id || fallbackTitle}</div>
        <div className="record-meta">{item.id}</div>
        <div className="record-meta">合同 {formatContractSummary(summary)}</div>
        {item.issues.length ? <div className="record-meta">质量缺口 {item.issues.map((issue) => issueLabels[issue.code] || issue.message).join('；')}</div> : null}
      </div>
      <StatusBadge status={item.state} />
    </article>
  )
}

export function MethodologyPage() {
  const queryClient = useQueryClient()
  const [programTitle, setProgramTitle] = useState('')
  const [programGoal, setProgramGoal] = useState('')
  const [programId, setProgramId] = useState('')
  const [question, setQuestion] = useState('')
  const [methodName, setMethodName] = useState('')
  const [failureModes, setFailureModes] = useState('')
  const [questionId, setQuestionId] = useState('')
  const [methodId, setMethodId] = useState('')
  const [oneChange, setOneChange] = useState('')
  const [designQuery, setDesignQuery] = useState('')
  const [planTitle, setPlanTitle] = useState('')
  const [planHypothesisId, setPlanHypothesisId] = useState('')
  const [planObjective, setPlanObjective] = useState('')
  const [planOneChange, setPlanOneChange] = useState('')
  const [planValidationMethod, setPlanValidationMethod] = useState('benchmark_comparison')
  const [planResultRequirements, setPlanResultRequirements] = useState('score_report\nbadcase_summary')

  const plans = useQuery({ queryKey: ['plans'], queryFn: () => getListData<RecordItem>('/api/v1/plans') })
  const programs = useQuery({ queryKey: ['research-programs'], queryFn: () => getListData<RecordItem>('/api/v1/research/programs') })
  const questions = useQuery({ queryKey: ['research-questions'], queryFn: () => getListData<RecordItem>('/api/v1/research/questions') })
  const methods = useQuery({ queryKey: ['method-cards'], queryFn: () => getListData<RecordItem>('/api/v1/research/method-cards') })
  const protocols = useQuery({ queryKey: ['protocols'], queryFn: () => getListData<RecordItem>('/api/v1/research/protocols') })
  const methodTemplates = useQuery({ queryKey: ['research-method-templates'], queryFn: () => getData<MethodTemplates>('/api/v1/research/method-templates') })
  const designAudit = useQuery({
    queryKey: ['research-design-audit', designQuery],
    queryFn: () => getData<DesignAudit>(`/api/v1/research/design/audit${designQuery.trim() ? `?q=${encodeURIComponent(designQuery.trim())}` : ''}`),
  })

  const createProgram = useMutation({
    mutationFn: () => postData('/api/v1/research/programs', { title: programTitle, goal: programGoal }),
    onSuccess: () => {
      setProgramTitle('')
      setProgramGoal('')
      queryClient.invalidateQueries({ queryKey: ['research-programs'] })
    },
  })
  const createPlan = useMutation({
    mutationFn: () => postData('/api/v1/plans', {
      title: planTitle,
      hypothesis_id: planHypothesisId || undefined,
      objective: planObjective,
      one_change: planOneChange,
      validation_method: planValidationMethod,
      controls: ['当前基线'],
      acceptance_criteria: { measurable_improvement: true },
      rejection_criteria: { no_traceable_result: true },
      result_requirements: planResultRequirements.split('\n').map((item) => item.trim()).filter(Boolean),
    }),
    onSuccess: () => {
      setPlanTitle('')
      setPlanHypothesisId('')
      setPlanObjective('')
      setPlanOneChange('')
      queryClient.invalidateQueries({ queryKey: ['plans'] })
      queryClient.invalidateQueries({ queryKey: ['protocols'] })
    },
  })
  const createQuestion = useMutation({
    mutationFn: () => postData('/api/v1/research/questions', {
      program_id: programId || undefined,
      question,
      success_criteria: { evidence_required: true },
    }),
    onSuccess: () => {
      setQuestion('')
      queryClient.invalidateQueries({ queryKey: ['research-questions'] })
    },
  })
  const createMethod = useMutation({
    mutationFn: () => postData('/api/v1/research/method-cards', {
      name: methodName,
      domain: 'general',
      failure_modes: failureModes.split('\n').map((item) => item.trim()).filter(Boolean),
      required_artifacts: ['benchmark_result', 'run_log'],
    }),
    onSuccess: () => {
      setMethodName('')
      setFailureModes('')
      queryClient.invalidateQueries({ queryKey: ['method-cards'] })
    },
  })
  const createProtocol = useMutation({
    mutationFn: () => postData('/api/v1/research/protocols', {
      question_id: questionId,
      method_id: methodId || undefined,
      one_change: oneChange,
      controls: ['当前基线'],
      acceptance_criteria: { measurable_improvement: true },
      rejection_criteria: { no_traceable_evidence: true },
      artifact_requirements: ['artifact_ref'],
    }),
    onSuccess: () => {
      setQuestionId('')
      setMethodId('')
      setOneChange('')
      queryClient.invalidateQueries({ queryKey: ['protocols'] })
    },
  })

  const mutationError = createProgram.error?.message
    || createPlan.error?.message
    || createQuestion.error?.message
    || createMethod.error?.message
    || createProtocol.error?.message

  function applyTemplate(template: MethodTemplate) {
    setMethodName(templateTitleLabels[template.id] || template.title)
    setFailureModes([
      ...template.design_questions.map((question) => `待回答：${question}`),
      ...template.review_gates.map((gate) => `审查门：${gate}`),
    ].join('\n'))
    setOneChange(template.protocol_defaults.one_change || '')
  }

  return (
    <div className="grid-two">
      <Panel title="Plan">
        <form className="form" onSubmit={(event) => { event.preventDefault(); createPlan.mutate() }}>
          <TextInput label="标题" value={planTitle} onChange={setPlanTitle} placeholder="本轮最小实验计划" />
          <TextInput label="Hypothesis ID" value={planHypothesisId} onChange={setPlanHypothesisId} placeholder="可选：hypothesis_..." />
          <TextArea label="目标" value={planObjective} onChange={setPlanObjective} placeholder="要验证的机制、分数或现象" />
          <TextArea label="唯一变化" value={planOneChange} onChange={setPlanOneChange} placeholder="本轮只改变什么" />
          <TextInput label="验证方式" value={planValidationMethod} onChange={setPlanValidationMethod} placeholder="benchmark_comparison / ablation / reproduction" />
          <TextArea label="结果要求" value={planResultRequirements} onChange={setPlanResultRequirements} placeholder="每行一个结果要求" />
          <Button type="submit" disabled={!planTitle || !planOneChange}>写入 Plan</Button>
        </form>
      </Panel>
      <Panel title="方法模板">
        <ErrorMessage message={methodTemplates.error?.message} />
        {methodTemplates.data ? (
          <div className="record-list compact">
            <article className="record-row">
              <div>
                <div className="record-title">自动化科研模板目录</div>
                <div className="record-meta">只读模板，不执行实验，不创建工作流。用于生成方法卡、协议和审计前检查。</div>
              </div>
              <StatusBadge status={methodTemplates.data.state} />
            </article>
            {methodTemplates.data.templates.map((template) => (
              <article className="record-row" key={template.id}>
                <div>
                  <div className="record-title">{templateTitleLabels[template.id] || template.title}</div>
                  <div className="record-meta">{template.when_to_use}</div>
                  <div className="record-meta">需要记录：{formatList(template.required_records)}</div>
                  <div className="record-meta">成果要求：{formatList(template.artifact_requirements)}</div>
                  <div className="record-meta">证据期望：{formatList(template.evidence_expectations)}</div>
                </div>
                <Button onClick={() => applyTemplate(template)}>套用</Button>
              </article>
            ))}
            {methodTemplates.data.recommended_next_actions.map((action) => (
              <article className="record-row" key={`${action.endpoint}-${action.reason}`}>
                <div>
                  <div className="record-title">{action.endpoint}</div>
                  <div className="record-meta">{action.reason}</div>
                </div>
                <StatusBadge status={action.priority === 'high' ? 'blocked' : 'planned'} />
              </article>
            ))}
          </div>
        ) : null}
      </Panel>
      <Panel title="高级计划对象">
        <form className="form" onSubmit={(event) => { event.preventDefault(); createProgram.mutate() }}>
          <TextInput label="标题" value={programTitle} onChange={setProgramTitle} placeholder="长期研究方向" />
          <TextArea label="目标" value={programGoal} onChange={setProgramGoal} placeholder="要解决的科学或工程问题" />
          <Button type="submit" disabled={!programTitle || !programGoal}>登记计划</Button>
        </form>
      </Panel>
      <Panel title="研究问题">
        <form className="form" onSubmit={(event) => { event.preventDefault(); createQuestion.mutate() }}>
          <TextInput label="计划 ID" value={programId} onChange={setProgramId} placeholder="可选，program_" />
          <TextArea label="问题" value={question} onChange={setQuestion} placeholder="必须能转成假设、协议和证据" />
          <Button type="submit" disabled={!question}>登记问题</Button>
        </form>
      </Panel>
      <Panel title="方法卡">
        <form className="form" onSubmit={(event) => { event.preventDefault(); createMethod.mutate() }}>
          <TextInput label="名称" value={methodName} onChange={setMethodName} placeholder="评测、消融、复现实验或审查方法" />
          <TextArea label="失败模式" value={failureModes} onChange={setFailureModes} placeholder="每行一个失败模式" />
          <Button type="submit" disabled={!methodName}>登记方法</Button>
        </form>
      </Panel>
      <Panel title="预注册协议">
        <form className="form" onSubmit={(event) => { event.preventDefault(); createProtocol.mutate() }}>
          <TextInput label="问题 ID" value={questionId} onChange={setQuestionId} placeholder="question_" />
          <TextInput label="方法 ID" value={methodId} onChange={setMethodId} placeholder="可选，method_" />
          <TextArea label="唯一变化" value={oneChange} onChange={setOneChange} placeholder="本轮只改变什么" />
          <Button type="submit" disabled={!questionId || !oneChange}>登记协议</Button>
        </form>
        <ErrorMessage message={mutationError} />
      </Panel>
      <Panel title="研究设计审计">
        <form className="form" onSubmit={(event) => event.preventDefault()}>
          <TextInput label="审计关键词" value={designQuery} onChange={setDesignQuery} placeholder="记忆、假设、协议或领域" />
        </form>
        <ErrorMessage message={designAudit.error?.message} />
        {designAudit.data ? (
          <div className="record-list compact">
            <article className="record-row">
              <div>
                <div className="record-title">预注册质量门</div>
                <div className="record-meta">缺口 {formatIssueCounts(designAudit.data.issue_counts)}</div>
                <div className="record-meta">问题 {designAudit.data.question_ids_with_issues.length} · 假设 {designAudit.data.hypothesis_ids_with_issues.length} · 协议 {designAudit.data.protocol_ids_with_issues.length}</div>
              </div>
              <StatusBadge status={designAudit.data.state} />
            </article>
            <article className="record-row">
              <div>
                <div className="record-title">可回答问题</div>
                <div className="record-meta">要求立项理由与成功标准，用于判断问题何时被回答。</div>
              </div>
            </article>
            {designAudit.data.questions.map((item) => renderAuditItem(item, '研究问题'))}
            <article className="record-row">
              <div>
                <div className="record-title">可证伪假设</div>
                <div className="record-meta">要求预期效应、接受标准和拒绝标准。</div>
              </div>
            </article>
            {designAudit.data.hypotheses.map((item) => renderAuditItem(item, '研究假设'))}
            <article className="record-row">
              <div>
                <div className="record-title">协议执行边界</div>
                <div className="record-meta">要求唯一变化、对照、接受/拒绝标准和成果要求；平台仍不执行协议。</div>
              </div>
            </article>
            {designAudit.data.protocols.map((item) => renderAuditItem(item, '预注册协议'))}
            {designAudit.data.recommended_next_actions.map((action) => (
              <article className="record-row" key={`${action.endpoint}-${action.reason}`}>
                <div>
                  <div className="record-title">{action.endpoint}</div>
                  <div className="record-meta">{action.reason}</div>
                </div>
                <StatusBadge status={action.priority === 'high' ? 'blocked' : 'planned'} />
              </article>
            ))}
          </div>
        ) : null}
      </Panel>
      <Panel title="Plan 列表"><RecordList items={plans.data?.items} /></Panel>
      <Panel title="高级计划列表"><RecordList items={programs.data?.items} /></Panel>
      <Panel title="问题列表"><RecordList items={questions.data?.items} /></Panel>
      <Panel title="方法列表"><RecordList items={methods.data?.items} /></Panel>
      <Panel title="协议列表"><RecordList items={protocols.data?.items} /></Panel>
    </div>
  )
}
