import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button, ErrorMessage, Panel, RecordList, SelectInput, StatusBadge, TextInput, WarningList } from '@/components/Primitives'
import { getData, getListData, patchData, postData, type RecordItem } from '@/lib/api'
import { formatKeyValueSummary, formatRefs } from '@/lib/display'

type BenchmarkAuditIssue = {
  code: string
  severity: string
  message: string
}

type BenchmarkAuditItem = {
  id: string
  name: string
  domain: string
  status?: string
  state: string
  issues: BenchmarkAuditIssue[]
  contract_summary: {
    external_runner: string
    metric_keys: string[]
    input_keys: string[]
    output_keys: string[]
    artifact_requirement_count: number
  }
}

type BenchmarkAudit = {
  state: string
  issue_counts: Record<string, number>
  benchmark_ids_with_issues: string[]
  items: BenchmarkAuditItem[]
  recommended_next_actions: Array<{ endpoint: string; reason: string; priority: string }>
}

type BenchmarkRunComparisonIssue = {
  code: string
  severity: string
  message: string
}

type BenchmarkRunComparisonItem = {
  run_id: string
  benchmark_id: string
  status: string
  score?: number | null
  artifact_ref_count: number
  runner: string
  state: string
  issues: BenchmarkRunComparisonIssue[]
}

type BenchmarkRunComparison = {
  state: string
  benchmark_id: string
  metric: string
  direction: string
  total: number
  status_counts: Record<string, number>
  best_run?: BenchmarkRunComparisonItem | null
  score_range?: { min: number; max: number; delta: number } | null
  ranked_runs: BenchmarkRunComparisonItem[]
  items: BenchmarkRunComparisonItem[]
  issue_counts: Record<string, number>
  run_ids_with_issues: string[]
  recommended_next_actions: Array<{ endpoint: string; reason: string; priority: string }>
  safety: string
}

const issueLabels: Record<string, string> = {
  missing_external_runner: '缺少外部适配器',
  missing_metric_schema: '缺少指标合同',
  missing_input_contract: '缺少输入合同',
  missing_output_contract: '缺少输出合同',
  missing_artifact_requirements: '缺少成果要求',
}

const comparisonIssueLabels: Record<string, string> = {
  missing_metric_score: '缺少指标分数',
  missing_artifact_refs: '缺少成果引用',
  missing_runner_provenance: '缺少运行来源',
  non_completed_status: '非完成状态',
}

function formatIssueCounts(counts?: Record<string, number>, labels: Record<string, string> = issueLabels) {
  if (!counts || !Object.keys(counts).length) return '无缺口'
  return Object.entries(counts).map(([key, value]) => `${labels[key] || key} ${value}`).join('，')
}

function formatCountMap(counts?: Record<string, number>) {
  if (!counts || !Object.keys(counts).length) return '暂无'
  return Object.entries(counts).map(([key, value]) => `${key} ${value}`).join('，')
}

function formatScore(score?: number | null) {
  return typeof score === 'number' ? score.toLocaleString('zh-CN', { maximumFractionDigits: 6 }) : '暂无'
}

export function BenchmarksPage() {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [domain, setDomain] = useState('agent-memory')
  const [adapter, setAdapter] = useState('external-runtime-adapter')
  const [primaryMetric, setPrimaryMetric] = useState('score')
  const [benchmarkId, setBenchmarkId] = useState('')
  const benchmarks = useQuery({ queryKey: ['benchmarks'], queryFn: () => getListData<RecordItem>('/api/v1/benchmarks') })
  const runs = useQuery({ queryKey: ['benchmark-runs'], queryFn: () => getListData<RecordItem>('/api/v1/benchmark-runs') })
  const suiteAudit = useQuery({ queryKey: ['benchmarks-audit'], queryFn: () => getData<BenchmarkAudit>('/api/v1/benchmarks/audit') })
  const comparisonBenchmarkId = benchmarkId || benchmarks.data?.items[0]?.id || ''
  const runComparison = useQuery({
    queryKey: ['benchmark-run-comparison', comparisonBenchmarkId, primaryMetric],
    enabled: Boolean(comparisonBenchmarkId),
    queryFn: () => getData<BenchmarkRunComparison>(`/api/v1/benchmark-runs/compare?benchmark_id=${encodeURIComponent(comparisonBenchmarkId)}&metric=${encodeURIComponent(primaryMetric || 'score')}`),
  })
  const createBenchmark = useMutation({
    mutationFn: () => postData('/api/v1/benchmarks', {
      name,
      domain,
      metric_schema: { [primaryMetric || 'score']: { type: 'number', direction: 'higher_is_better' } },
      input_schema: { dataset_ref: 'artifact', config: 'object' },
      output_schema: { scores: 'object', artifact_refs: 'array', summary: 'string' },
      artifact_requirements: [
        { artifact_type: 'benchmark_result', required: true },
        { artifact_type: 'run_log', required: true },
      ],
      external_runner: { adapter, runtime: 'external', entrypoint: 'runtime-owned' },
    }),
    onSuccess: () => {
      setName('')
      queryClient.invalidateQueries({ queryKey: ['benchmarks'] })
      queryClient.invalidateQueries({ queryKey: ['benchmarks-audit'] })
    },
  })
  const createRun = useMutation({
    mutationFn: () => postData('/api/v1/benchmark-runs', { benchmark_id: benchmarkId || benchmarks.data?.items[0]?.id, status: 'running', runtime: { name: 'external-runtime' } }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['benchmark-runs'] })
      queryClient.invalidateQueries({ queryKey: ['benchmark-run-comparison'] })
    },
  })
  const completeRun = useMutation({
    mutationFn: (id: string) => patchData(`/api/v1/benchmark-runs/${id}`, {
      status: 'completed',
      scores: { [primaryMetric || 'score']: 0.8 },
      artifact_refs: [{ type: 'artifact', id: 'artifact_external_result_ref' }],
      provenance: { runner: 'frontend-demo' },
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['benchmark-runs'] })
      queryClient.invalidateQueries({ queryKey: ['benchmark-run-comparison'] })
    },
  })
  const runWarnings = (runs.data?.items || [])
    .filter((run) => run.status === 'blocked' || run.status === 'degraded')
    .map((run) => `运行 ${run.id} 当前为${run.status === 'blocked' ? '阻塞' : '降级'}状态`)

  return (
    <div className="grid-two">
      <Panel title="评测套件">
        <form className="form" onSubmit={(event) => { event.preventDefault(); createBenchmark.mutate() }}>
          <TextInput label="名称" value={name} onChange={setName} placeholder="长期记忆回忆 / 论文检索质量" />
          <TextInput label="外部适配器" value={adapter} onChange={setAdapter} placeholder="由外部 Runtime 拥有" />
          <TextInput label="主指标" value={primaryMetric} onChange={setPrimaryMetric} placeholder="score / recall / pass_rate" />
          <SelectInput
            label="领域"
            value={domain}
            onChange={setDomain}
            options={[
              { value: 'agent-memory', label: 'Agent 记忆' },
              { value: 'ai-for-science', label: 'AI for Science' },
              { value: 'algorithm', label: '算法研究' },
              { value: 'general', label: '通用' },
            ]}
          />
          <Button type="submit" disabled={!name || !adapter || !primaryMetric}>登记评测合同</Button>
        </form>
        <ErrorMessage message={createBenchmark.error?.message} />
      </Panel>
      <Panel title="评测合同审计">
        <ErrorMessage message={suiteAudit.error?.message} />
        {suiteAudit.data ? (
          <>
            <div className="record-list compact">
              <article className="record-row">
                <div>
                  <div className="record-title">整体状态</div>
                  <div className="record-meta">缺口 {formatIssueCounts(suiteAudit.data.issue_counts)}</div>
                  <div className="record-meta">需修复 {suiteAudit.data.benchmark_ids_with_issues.length}</div>
                </div>
                <StatusBadge status={suiteAudit.data.state} />
              </article>
              {suiteAudit.data.items.map((item) => (
                <article className="record-row" key={item.id}>
                  <div>
                    <div className="record-title">{item.name}</div>
                    <div className="record-meta">外部适配器 {item.contract_summary.external_runner || '未记录'}</div>
                    <div className="record-meta">输入合同 {item.contract_summary.input_keys.join('，') || '未记录'}</div>
                    <div className="record-meta">输出合同 {item.contract_summary.output_keys.join('，') || '未记录'}</div>
                    <div className="record-meta">指标 {item.contract_summary.metric_keys.join('，') || '未记录'} · 成果要求 {item.contract_summary.artifact_requirement_count}</div>
                    {item.issues.length ? <div className="record-meta">质量缺口 {item.issues.map((issue) => issueLabels[issue.code] || issue.message).join('；')}</div> : null}
                  </div>
                  <StatusBadge status={item.state} />
                </article>
              ))}
            </div>
            {suiteAudit.data.recommended_next_actions.length ? (
              <div className="record-list compact">
                {suiteAudit.data.recommended_next_actions.map((action) => (
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
          </>
        ) : null}
      </Panel>
      <Panel title="结果对比">
        <ErrorMessage message={runComparison.error?.message} />
        {runComparison.data ? (
          <>
            <div className="record-list compact">
              <article className="record-row">
                <div>
                  <div className="record-title">最佳运行</div>
                  <div className="record-meta">
                    {runComparison.data.best_run
                      ? `${runComparison.data.best_run.run_id} · ${runComparison.data.metric} ${formatScore(runComparison.data.best_run.score)}`
                      : '暂无可比运行'}
                  </div>
                  <div className="record-meta">方向 {runComparison.data.direction} · 总数 {runComparison.data.total}</div>
                </div>
                <StatusBadge status={runComparison.data.state} />
              </article>
              <article className="record-row">
                <div>
                  <div className="record-title">指标范围</div>
                  <div className="record-meta">
                    {runComparison.data.score_range
                      ? `最小 ${formatScore(runComparison.data.score_range.min)} · 最大 ${formatScore(runComparison.data.score_range.max)} · 差值 ${formatScore(runComparison.data.score_range.delta)}`
                      : '暂无可比指标'}
                  </div>
                  <div className="record-meta">状态分布 {formatCountMap(runComparison.data.status_counts)}</div>
                </div>
                <StatusBadge status="ready" />
              </article>
              <article className="record-row">
                <div>
                  <div className="record-title">证据准备缺口</div>
                  <div className="record-meta">{formatIssueCounts(runComparison.data.issue_counts, comparisonIssueLabels)}</div>
                  <div className="record-meta">需修复运行 {runComparison.data.run_ids_with_issues.join('，') || '无'}</div>
                </div>
                <StatusBadge status={runComparison.data.run_ids_with_issues.length ? 'degraded' : 'ready'} />
              </article>
              {runComparison.data.ranked_runs.slice(0, 5).map((run) => (
                <article className="record-row" key={run.run_id}>
                  <div>
                    <div className="record-title">{run.run_id}</div>
                    <div className="record-meta">分数 {formatScore(run.score)} · 运行方 {run.runner || '未记录'} · 成果引用 {run.artifact_ref_count}</div>
                    {run.issues.length ? <div className="record-meta">缺口 {run.issues.map((issue) => comparisonIssueLabels[issue.code] || issue.message).join('；')}</div> : null}
                  </div>
                  <StatusBadge status={run.state} />
                </article>
              ))}
            </div>
            {runComparison.data.recommended_next_actions.length ? (
              <div className="record-list compact">
                {runComparison.data.recommended_next_actions.map((action) => (
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
          </>
        ) : <div className="empty">选择评测套件后读取结果对比</div>}
      </Panel>
      <Panel title="运行记录">
        <form className="form" onSubmit={(event) => { event.preventDefault(); createRun.mutate() }}>
          <TextInput label="评测 ID" value={benchmarkId} onChange={setBenchmarkId} placeholder="为空时使用第一个套件" />
          <Button type="submit" disabled={!benchmarkId && !benchmarks.data?.items[0]}>创建运行记录</Button>
        </form>
        <WarningList warnings={runWarnings} />
        <ErrorMessage message={createRun.error?.message || completeRun.error?.message} />
        <div className="record-list compact">
          {(runs.data?.items || []).map((run) => (
            <article className="record-row record-row-actions" key={run.id}>
              <div>
                <div className="record-title">{run.id}</div>
                <div className="record-meta">分数 {formatKeyValueSummary(run.scores)}</div>
                <div className="record-meta">成果引用 {formatRefs(run.artifact_refs)}</div>
                <div className="record-meta">来源 {formatKeyValueSummary(run.provenance)}</div>
              </div>
              <StatusBadge status={typeof run.status === 'string' ? run.status : undefined} />
              <button onClick={() => completeRun.mutate(run.id)}>登记完成</button>
            </article>
          ))}
        </div>
      </Panel>
      <Panel title="评测套件"><RecordList items={benchmarks.data?.items} /></Panel>
      <Panel title="运行记录"><RecordList items={runs.data?.items} /></Panel>
    </div>
  )
}
