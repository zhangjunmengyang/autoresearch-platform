import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button, ErrorMessage, Panel, RecordList, StatusBadge, TextArea, TextInput, WarningList } from '@/components/Primitives'
import { getListData, patchData, postData, requestEnvelope, type RecordItem } from '@/lib/api'
import { formatHumanText, formatRefs, labelRecordType, labelTerm } from '@/lib/display'

type RoundWorktree = {
  path?: string
  branch?: string
  base_ref?: string
}

type RoundRef = {
  type?: string
  sha?: string
  branch?: string
  id?: string
}

type CompleteRoundInput = {
  roundId: string
  roundBranch: string
}

type RoundAction = {
  action?: string
  endpoint?: string
  reason?: string
}

type UnresolvedRoundRef = {
  field?: string
  type?: string
  id?: string
  reason?: string
}

type RoundDetail = {
  round: RecordItem
  session?: RecordItem | null
  trace: {
    implementation_refs: RoundRef[]
    experiments: RecordItem[]
    artifacts: RecordItem[]
    benchmark_runs: RecordItem[]
    evidence_records: RecordItem[]
    decisions: RecordItem[]
    unresolved_refs: UnresolvedRoundRef[]
  }
  recommended_next_actions: RoundAction[]
  safety: string
}

export function ResearchRoundsPage() {
  const queryClient = useQueryClient()
  const [query, setQuery] = useState('')
  const [selectedRoundId, setSelectedRoundId] = useState('')
  const [title, setTitle] = useState('')
  const [proposal, setProposal] = useState('')
  const [sessionId, setSessionId] = useState('')
  const [worktreePath, setWorktreePath] = useState('')
  const [branch, setBranch] = useState('')
  const [baseRef, setBaseRef] = useState('主线')
  const [commitSha, setCommitSha] = useState('')
  const rounds = useQuery({
    queryKey: ['research-rounds', query],
    queryFn: () => getListData<RecordItem>(`/api/v1/research/rounds${query ? `?q=${encodeURIComponent(query)}` : ''}`),
  })
  const roundDetail = useQuery({
    queryKey: ['research-round-detail', selectedRoundId],
    enabled: Boolean(selectedRoundId),
    queryFn: () => requestEnvelope<RoundDetail>(`/api/v1/research/rounds/${selectedRoundId}`),
  })
  const create = useMutation({
    mutationFn: () => postData('/api/v1/research/rounds', {
      title,
      proposal,
      session_id: sessionId || undefined,
      worktree: {
        path: worktreePath,
        branch,
        base_ref: baseRef.trim() === '主线' ? 'main' : baseRef,
      },
      status: 'running',
      runtime: { kind: 'external-runtime', id: 'workbench' },
    }),
    onSuccess: () => {
      setTitle('')
      setProposal('')
      setSessionId('')
      setWorktreePath('')
      setBranch('')
      setBaseRef('主线')
      queryClient.invalidateQueries({ queryKey: ['research-rounds'] })
    },
  })
  const complete = useMutation({
    mutationFn: ({ roundId, roundBranch }: CompleteRoundInput) => patchData(`/api/v1/research/rounds/${roundId}`, {
      status: 'completed',
      implementation_refs: [{ type: 'commit', sha: commitSha, branch: roundBranch }],
      retrospective: { next: '登记实验、证据和决策引用' },
    }),
    onSuccess: () => {
      setCommitSha('')
      queryClient.invalidateQueries({ queryKey: ['research-rounds'] })
      queryClient.invalidateQueries({ queryKey: ['research-round-detail'] })
    },
  })

  const detail = roundDetail.data?.data

  return (
    <div className="grid-two">
      <Panel title="研究轮次">
        <form className="form" onSubmit={(event) => { event.preventDefault(); create.mutate() }}>
          <TextInput label="方案标题" value={title} onChange={setTitle} placeholder="例如：回放方案甲" />
          <TextArea label="方案说明" value={proposal} onChange={setProposal} placeholder="本轮要验证的唯一变化、预期收益和禁止范围" />
          <TextInput label="账本标识" value={sessionId} onChange={setSessionId} placeholder="可选：研究账本标识" />
          <TextInput label="工作树路径" value={worktreePath} onChange={setWorktreePath} placeholder="外部运行方工作树路径" />
          <TextInput label="分支" value={branch} onChange={setBranch} placeholder="外部代码分支" />
          <TextInput label="基线引用" value={baseRef} onChange={setBaseRef} placeholder="外部基线引用" />
          <Button type="submit" disabled={!title || !proposal}>登记轮次</Button>
        </form>
        <ErrorMessage message={create.error?.message} />
      </Panel>

      <Panel title="完成留痕">
        <form className="form" onSubmit={(event) => event.preventDefault()}>
          <TextInput label="提交引用" value={commitSha} onChange={setCommitSha} placeholder="提交哈希或外部代码引用" />
          <TextInput label="筛选" value={query} onChange={setQuery} placeholder="方案、分支、提交、实验或证据关键词" />
        </form>
        <p className="panel-copy">
          平台只保存工作树、分支、提交、实验、成果引用、证据和决策引用；创建工作树、提交代码和运行实验由外部运行方完成。
        </p>
        <ErrorMessage message={complete.error?.message} />
      </Panel>

      <Panel title="轮次列表">
        <div className="record-list">
          {(rounds.data?.items || []).map((round) => {
            const worktree = round.worktree as RoundWorktree | undefined
            const implementationRefs = Array.isArray(round.implementation_refs)
              ? round.implementation_refs as RoundRef[]
              : []
            const experimentRefs = Array.isArray(round.experiment_refs)
              ? round.experiment_refs as RoundRef[]
              : []
            const evidenceRefs = Array.isArray(round.evidence_refs)
              ? round.evidence_refs as RoundRef[]
              : []
            return (
              <article className="record-row record-row-actions" key={round.id}>
                <div>
                  <div className="record-title">{String(round.title || round.id)}</div>
                  <div className="record-meta">方案 {formatHumanText(round.proposal || '')}</div>
                  <div className="record-meta">工作树 {worktree?.path || '未记录'} · 分支 {worktree?.branch || '未记录'} · 基线 {worktree?.base_ref ? labelTerm(worktree.base_ref) : '未记录'}</div>
                  <div className="record-meta">提交 {formatRefs(implementationRefs)}</div>
                  <div className="record-meta">实验 {formatRefs(experimentRefs)} · 证据 {formatRefs(evidenceRefs)}</div>
                </div>
                <div className="row-actions">
                  <StatusBadge status={typeof round.status === 'string' ? round.status : undefined} />
                  <Button
                    disabled={!commitSha || round.status === 'completed'}
                    onClick={() => complete.mutate({ roundId: round.id, roundBranch: worktree?.branch || branch })}
                  >
                    完成
                  </Button>
                  <Button onClick={() => setSelectedRoundId(round.id)}>查看</Button>
                </div>
              </article>
            )
          })}
        </div>
        {!rounds.data?.items.length ? <RecordList items={[]} /> : null}
      </Panel>

      <Panel title="追踪包">
        {!selectedRoundId ? <div className="empty">请选择一个研究轮次</div> : null}
        <ErrorMessage message={roundDetail.error?.message} />
        <WarningList warnings={roundDetail.data?.warnings} />
        {detail ? (
          <div className="record-list">
            <article className="record-row">
              <div>
                <div className="record-title">{String(detail.round.title || detail.round.id)}</div>
                <div className="record-meta">轮次 {detail.round.id}</div>
                <div className="record-meta">账本 {detail.session?.id || '未关联'}</div>
              </div>
              <StatusBadge status={typeof detail.round.status === 'string' ? detail.round.status : undefined} />
            </article>

            <article className="record-row">
              <div>
                <div className="record-title">已解析引用</div>
                <div className="record-meta">实验 {detail.trace.experiments.length} · 成果引用 {detail.trace.artifacts.length} · 证据 {detail.trace.evidence_records.length} · 决策 {detail.trace.decisions.length}</div>
                <div className="record-meta">提交 {formatRefs(detail.trace.implementation_refs)}</div>
              </div>
            </article>

            <article className="record-row">
              <div>
                <div className="record-title">未解析引用</div>
                <div className="record-meta">
                  {detail.trace.unresolved_refs.length
                    ? detail.trace.unresolved_refs.map((ref) => `${labelTerm(ref.field)}：${labelRecordType(ref.type)}：${ref.id || '缺少标识'}：${formatHumanText(ref.reason || '未知原因')}`).join('，')
                    : '无'}
                </div>
              </div>
            </article>

            <article className="record-row">
              <div>
                <div className="record-title">建议动作</div>
                <div className="record-meta">
                  {detail.recommended_next_actions.length
                    ? detail.recommended_next_actions.map((action) => `${formatHumanText(action.action || '动作')}：${formatHumanText(action.reason || '未记录原因')}`).join('，')
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
