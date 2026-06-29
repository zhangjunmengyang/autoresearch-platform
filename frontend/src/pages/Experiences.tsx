import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button, ErrorMessage, Panel, RecordList, SelectInput, StatusBadge, TextArea, TextInput, WarningList } from '@/components/Primitives'
import { getListData, postData, type RecordItem } from '@/lib/api'

type SourceTraceItem = {
  type?: string
  id?: string
  collection?: string
  status?: string
  summary?: string
  reason?: string
}

type GovernanceGap = {
  code?: string
  severity?: string
  message?: string
  refs?: SourceTraceItem[]
}

type RecommendedAction = {
  action?: string
  endpoint?: string
  reason?: string
}

type PreviewResult = {
  accepted: boolean
  warnings: string[]
  source_trace?: {
    resolved?: SourceTraceItem[]
    unresolved?: SourceTraceItem[]
    coverage?: Record<string, number>
  }
  governance_gaps?: GovernanceGap[]
  recommended_next_actions?: RecommendedAction[]
  safety?: string
}

const sourceRefTypes = [
  { value: 'session', label: '研究账本' },
  { value: 'artifact', label: '成果引用' },
  { value: 'benchmark_run', label: '评测运行' },
  { value: 'evidence_record', label: '证据记录' },
  { value: 'review', label: '审查记录' },
  { value: 'decision', label: '决策记录' },
  { value: 'source', label: '资料输入' },
]

const gapLabels: Record<string, string> = {
  missing_source_refs: '缺少来源引用',
  unresolved_source_refs: '未解析来源引用',
  weak_curation_sources: '来源强度偏弱',
}

const severityLabels: Record<string, string> = {
  blocking: '阻塞',
  warning: '提醒',
}

export function ExperiencesPage() {
  const queryClient = useQueryClient()
  const [query, setQuery] = useState('')
  const [title, setTitle] = useState('')
  const [problem, setProblem] = useState('')
  const [sourceRefType, setSourceRefType] = useState('session')
  const [sourceRefId, setSourceRefId] = useState('')
  const experiences = useQuery({ queryKey: ['experiences'], queryFn: () => getListData<RecordItem>('/api/v1/experiences') })
  const search = useMutation({
    mutationFn: () => postData<{ items: RecordItem[]; total: number }>('/api/v1/experiences/query', { query, limit: 20 }),
  })
  const sourceRefs = () => (sourceRefId ? [{ type: sourceRefType, id: sourceRefId }] : [])
  const preview = useMutation({
    mutationFn: () => postData<PreviewResult>('/api/v1/experiences/curation/preview', {
        runtime: { name: 'frontend', operator: 'human' },
        experience: { title, problem, topics: ['general'] },
        source_refs: sourceRefs(),
        human_readable: true,
    }),
  })
  const apply = useMutation({
    mutationFn: () => postData('/api/v1/experiences/curation/apply', {
      runtime: { name: 'frontend', operator: 'human' },
      experience: { title, problem, topics: ['general'] },
      source_refs: sourceRefs(),
      human_readable: true,
    }),
    onSuccess: () => {
      setTitle('')
      setProblem('')
      setSourceRefId('')
      queryClient.invalidateQueries({ queryKey: ['experiences'] })
    },
  })
  const previewData = preview.data
  const resolvedSources = previewData?.source_trace?.resolved || []
  const unresolvedSources = previewData?.source_trace?.unresolved || []
  const governanceGaps = previewData?.governance_gaps || []
  const recommendedActions = previewData?.recommended_next_actions || []

  return (
    <div className="grid-two">
      <Panel title="查询经验">
        <form className="form" onSubmit={(event) => { event.preventDefault(); search.mutate() }}>
          <TextInput label="关键词" value={query} onChange={setQuery} placeholder="记忆 / 评测 / 方法缺口" />
          <Button type="submit">查询</Button>
        </form>
        <ErrorMessage message={search.error?.message} />
        <RecordList items={search.data?.items} />
      </Panel>
      <Panel title="显式经验维护">
        <form className="form" onSubmit={(event) => { event.preventDefault(); apply.mutate() }}>
          <TextInput label="标题" value={title} onChange={setTitle} />
          <TextArea label="问题和经验" value={problem} onChange={setProblem} />
          <SelectInput label="证据类型" value={sourceRefType} onChange={setSourceRefType} options={sourceRefTypes} />
          <TextInput label="证据 ID" value={sourceRefId} onChange={setSourceRefId} placeholder="session_ / artifact_ / benchrun_" />
          <Button type="button" disabled={!title} onClick={() => preview.mutate()}>预检</Button>
          <Button type="submit" disabled={!title || !problem || !sourceRefId}>写入</Button>
        </form>
        <WarningList warnings={preview.data?.warnings} />
        <ErrorMessage message={preview.error?.message || apply.error?.message} />
        {previewData ? (
          <div className="record-list compact">
            <article className="record-row">
              <div>
                <div className="record-title">来源追踪</div>
                <div className="record-meta">已解析 {resolvedSources.length} · 未解析 {unresolvedSources.length}</div>
                <div className="record-meta">
                  覆盖 {Object.entries(previewData.source_trace?.coverage || {}).map(([type, count]) => `${type} ${count}`).join('，') || '暂无'}
                </div>
              </div>
              <StatusBadge status={previewData.accepted ? 'completed' : 'blocked'} />
            </article>
            {resolvedSources.map((source) => (
              <article className="record-row" key={`${source.type}-${source.id}`}>
                <div>
                  <div className="record-title">{source.type || '来源'} · {source.id || '未记录'}</div>
                  <div className="record-meta">集合 {source.collection || '未记录'} · 状态 {source.status || '未记录'}</div>
                  <div className="record-meta">摘要 {source.summary || '未记录'}</div>
                </div>
              </article>
            ))}
            {unresolvedSources.map((source) => (
              <article className="record-row" key={`${source.type}-${source.id}-${source.reason}`}>
                <div>
                  <div className="record-title">{source.type || '来源'} · {source.id || '未记录'}</div>
                  <div className="record-meta">未解析原因 {source.reason || '未记录'}</div>
                </div>
                <StatusBadge status="blocked" />
              </article>
            ))}
            <article className="record-row">
              <div>
                <div className="record-title">治理缺口</div>
                {governanceGaps.length ? governanceGaps.map((gap) => (
                  <div className="record-meta" key={`${gap.code}-${gap.severity}`}>
                    {gapLabels[String(gap.code)] || gap.code || '缺口'} · {severityLabels[String(gap.severity)] || gap.severity || '未记录'} · {gap.message || ''}
                  </div>
                )) : <div className="record-meta">暂无治理缺口</div>}
              </div>
            </article>
            <article className="record-row">
              <div>
                <div className="record-title">建议动作</div>
                {recommendedActions.length ? recommendedActions.map((action) => (
                  <div className="record-meta" key={`${action.action}-${action.endpoint}`}>
                    {action.endpoint || '未记录'} · {action.reason || action.action || ''}
                  </div>
                )) : <div className="record-meta">暂无建议动作</div>}
              </div>
            </article>
          </div>
        ) : null}
      </Panel>
      <Panel title="经验列表"><RecordList items={experiences.data?.items} /></Panel>
    </div>
  )
}
