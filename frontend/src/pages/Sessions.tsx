import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { useState } from 'react'
import { Button, ErrorMessage, Panel, RecordList, SelectInput, StatusBadge, TextArea, TextInput, WarningList } from '@/components/Primitives'
import { getData, getListData, postData, patchData, type RecordItem } from '@/lib/api'

type SessionDetail = {
  session: RecordItem
  events: RecordItem[]
  experiments: RecordItem[]
  artifacts: RecordItem[]
}

export function SessionsPage() {
  const queryClient = useQueryClient()
  const [title, setTitle] = useState('')
  const sessions = useQuery({ queryKey: ['sessions'], queryFn: () => getListData<RecordItem>('/api/v1/research/sessions') })
  const create = useMutation({
    mutationFn: () => postData('/api/v1/research/sessions', { title, memory_context: {}, information_gain: 'new session' }),
    onSuccess: () => {
      setTitle('')
      queryClient.invalidateQueries({ queryKey: ['sessions'] })
    },
  })
  const sessionWarnings = (sessions.data?.items || [])
    .filter((item) => item.status === 'blocked' || item.status === 'degraded')
    .map((item) => `账本 ${item.id} 当前为${item.status === 'blocked' ? '阻塞' : '降级'}状态`)

  return (
    <div className="grid-two">
      <Panel title="创建研究账本">
        <form className="form" onSubmit={(event) => { event.preventDefault(); create.mutate() }}>
          <TextInput label="标题" value={title} onChange={setTitle} placeholder="本轮研究账本" />
          <Button type="submit" disabled={!title}>创建账本</Button>
        </form>
        <ErrorMessage message={create.error?.message} />
      </Panel>
      <Panel title="研究账本列表">
        <WarningList warnings={sessionWarnings} />
        <div className="record-list">
          {(sessions.data?.items || []).map((item) => (
            <Link className="record-row" key={item.id} to={`/sessions/${item.id}`}>
              <div>
                <div className="record-title">{String(item.title)}</div>
                <div className="record-meta">{item.id}</div>
              </div>
              <StatusBadge status={typeof item.status === 'string' ? item.status : undefined} />
            </Link>
          ))}
        </div>
        {!sessions.data?.items.length ? <RecordList items={[]} /> : null}
      </Panel>
    </div>
  )
}

export function SessionDetailPage() {
  const { id = '' } = useParams()
  const queryClient = useQueryClient()
  const [eventTitle, setEventTitle] = useState('')
  const [eventType, setEventType] = useState('observation')
  const [experiment, setExperiment] = useState('')
  const [artifactTitle, setArtifactTitle] = useState('')
  const detail = useQuery({ queryKey: ['session', id], queryFn: () => getData<SessionDetail>(`/api/v1/research/sessions/${id}`), enabled: Boolean(id) })
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['session', id] })
  const addEvent = useMutation({
    mutationFn: () => postData(`/api/v1/research/sessions/${id}/events`, { event_type: eventType, title: eventTitle, payload: {} }),
    onSuccess: () => { setEventTitle(''); refresh() },
  })
  const addExperiment = useMutation({
    mutationFn: () => postData(`/api/v1/research/sessions/${id}/experiments`, {
      hypothesis: experiment,
      expected_effect: '指标改善',
      acceptance_criteria: { measurable: true },
      rejection_criteria: { no_traceable_evidence: true },
    }),
    onSuccess: () => { setExperiment(''); refresh() },
  })
  const addArtifact = useMutation({
    mutationFn: () => postData(`/api/v1/research/sessions/${id}/artifacts`, { artifact_type: 'report', title: artifactTitle, summary: 'frontend registered artifact' }),
    onSuccess: () => { setArtifactTitle(''); refresh() },
  })
  const close = useMutation({
    mutationFn: () => postData(`/api/v1/research/sessions/${id}/close`, {
      status: 'completed',
      retrospective: {
        failed_attempts: [],
        platform_gaps: [],
        next_agent_one_liner: '继续从本 session 的 artifact 和实验结论出发。',
      },
    }),
    onSuccess: refresh,
  })

  const firstExperiment = detail.data?.experiments[0]
  const degrade = useMutation({
    mutationFn: () => firstExperiment ? patchData(`/api/v1/research/sessions/${id}/experiments/${firstExperiment.id}`, { status: 'degraded', result_summary: 'frontend marked degraded' }) : Promise.resolve(null),
    onSuccess: refresh,
  })
  const detailWarnings = [
    ...(detail.data?.session.status === 'blocked' || detail.data?.session.status === 'degraded'
      ? [`账本当前为${detail.data.session.status === 'blocked' ? '阻塞' : '降级'}状态`]
      : []),
    ...(detail.data?.experiments || [])
      .filter((item) => item.status === 'blocked' || item.status === 'degraded')
      .map((item) => `实验 ${item.id} 当前为${item.status === 'blocked' ? '阻塞' : '降级'}状态`),
  ]
  const mutationError = addEvent.error?.message
    || addExperiment.error?.message
    || addArtifact.error?.message
    || close.error?.message
    || degrade.error?.message

  return (
    <div className="stack">
      <Panel title={detail.data?.session.title ? String(detail.data.session.title) : '研究账本'}>
        <div className="detail-grid">
          <div><strong>状态</strong><StatusBadge status={typeof detail.data?.session.status === 'string' ? detail.data.session.status : undefined} /></div>
          <div><strong>ID</strong><span>{id}</span></div>
          <div><strong>信息增量</strong><span>{String(detail.data?.session.information_gain || '')}</span></div>
        </div>
        <Button type="button" onClick={() => close.mutate()}>关闭账本</Button>
        <WarningList warnings={detailWarnings} />
        <ErrorMessage message={detail.error?.message || mutationError} />
      </Panel>
      <div className="grid-three">
        <Panel title="过程事件">
          <form className="form" onSubmit={(event) => { event.preventDefault(); addEvent.mutate() }}>
            <SelectInput
              label="类型"
              value={eventType}
              onChange={setEventType}
              options={[
                { value: 'observation', label: '观察' },
                { value: 'decision', label: '决策' },
                { value: 'tool_run', label: '工具运行' },
                { value: 'human_instruction', label: '外部指令' },
                { value: 'runtime_event', label: '外部 Runtime 事件' },
                { value: 'blocker', label: '阻塞' },
              ]}
            />
            <TextInput label="标题" value={eventTitle} onChange={setEventTitle} />
            <Button type="submit" disabled={!eventTitle}>追加</Button>
          </form>
        </Panel>
        <Panel title="实验登记">
          <form className="form" onSubmit={(event) => { event.preventDefault(); addExperiment.mutate() }}>
            <TextArea label="假设" value={experiment} onChange={setExperiment} />
            <Button type="submit" disabled={!experiment}>预注册</Button>
          </form>
          <Button type="button" disabled={!firstExperiment} onClick={() => degrade.mutate()}>标记首个实验降级</Button>
        </Panel>
        <Panel title="成果引用">
          <form className="form" onSubmit={(event) => { event.preventDefault(); addArtifact.mutate() }}>
            <TextInput label="标题" value={artifactTitle} onChange={setArtifactTitle} />
            <Button type="submit" disabled={!artifactTitle}>登记成果引用</Button>
          </form>
        </Panel>
      </div>
      <div className="grid-three">
        <Panel title="过程事件"><RecordList items={detail.data?.events} /></Panel>
        <Panel title="实验登记"><RecordList items={detail.data?.experiments} /></Panel>
        <Panel title="成果引用"><RecordList items={detail.data?.artifacts} /></Panel>
      </div>
    </div>
  )
}
