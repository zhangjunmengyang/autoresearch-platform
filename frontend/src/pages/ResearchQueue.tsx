import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button, Panel, RecordList, StatusBadge, TextArea, TextInput } from '@/components/Primitives'
import { getListData, postData, type RecordItem } from '@/lib/api'

export function ResearchQueuePage() {
  const queryClient = useQueryClient()
  const [title, setTitle] = useState('')
  const [rationale, setRationale] = useState('')
  const intake = useQuery({ queryKey: ['intake'], queryFn: () => getListData<RecordItem>('/api/v1/research/intake') })
  const create = useMutation({
    mutationFn: () => postData('/api/v1/research/intake', { title, rationale, human_constraints: [] }),
    onSuccess: () => {
      setTitle('')
      setRationale('')
      queryClient.invalidateQueries({ queryKey: ['intake'] })
    },
  })
  const claim = useMutation({
    mutationFn: (id: string) => postData(`/api/v1/research/intake/${id}/claim?operator=frontend`, {}),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['intake'] }),
  })
  const start = useMutation({
    mutationFn: (id: string) => postData(`/api/v1/research/intake/${id}/start-session`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['intake'] })
      queryClient.invalidateQueries({ queryKey: ['sessions'] })
    },
  })

  return (
    <div className="grid-two">
      <Panel title="创建任务">
        <form className="form" onSubmit={(event) => { event.preventDefault(); create.mutate() }}>
          <TextInput label="标题" value={title} onChange={setTitle} placeholder="要研究或验证的问题" />
          <TextArea label="理由" value={rationale} onChange={setRationale} placeholder="信息增量、约束或期望证据" />
          <Button type="submit" disabled={!title}>写入队列</Button>
        </form>
      </Panel>
      <Panel title="队列">
        <div className="record-list">
          {(intake.data?.items || []).map((item) => (
            <article className="record-row record-row-actions" key={item.id}>
              <div>
                <div className="record-title">{String(item.title)}</div>
                <div className="record-meta">{item.id}</div>
              </div>
              <StatusBadge status={typeof item.status === 'string' ? item.status : undefined} />
              <div className="row-actions">
                <button onClick={() => claim.mutate(item.id)}>领取</button>
                <button onClick={() => start.mutate(item.id)}>启动</button>
              </div>
            </article>
          ))}
        </div>
        {!intake.data?.items.length ? <RecordList items={[]} /> : null}
      </Panel>
    </div>
  )
}
