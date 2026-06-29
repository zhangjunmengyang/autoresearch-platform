import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button, Panel, RecordList, TextArea, TextInput } from '@/components/Primitives'
import { getListData, postData, type RecordItem } from '@/lib/api'

export function InsightsPage() {
  const queryClient = useQueryClient()
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [hypothesis, setHypothesis] = useState('')
  const insights = useQuery({ queryKey: ['insights'], queryFn: () => getListData<RecordItem>('/api/v1/insights') })
  const hypotheses = useQuery({ queryKey: ['hypotheses'], queryFn: () => getListData<RecordItem>('/api/v1/hypotheses') })
  const createInsight = useMutation({
    mutationFn: () => postData('/api/v1/insights', { title, body, insight_type: 'finding' }),
    onSuccess: () => {
      setTitle('')
      setBody('')
      queryClient.invalidateQueries({ queryKey: ['insights'] })
    },
  })
  const createHypothesis = useMutation({
    mutationFn: () => postData('/api/v1/hypotheses', {
      title: hypothesis,
      hypothesis,
      expected_effect: '形成可度量改进',
      acceptance_criteria: { evidence_required: true },
      rejection_criteria: { no_signal_or_untraceable: true },
    }),
    onSuccess: () => {
      setHypothesis('')
      queryClient.invalidateQueries({ queryKey: ['hypotheses'] })
    },
  })

  return (
    <div className="grid-two">
      <Panel title="洞察">
        <form className="form" onSubmit={(event) => { event.preventDefault(); createInsight.mutate() }}>
          <TextInput label="标题" value={title} onChange={setTitle} />
          <TextArea label="内容" value={body} onChange={setBody} placeholder="从论文、资料或命令中提炼出的观点、缺口或机制解释" />
          <Button type="submit" disabled={!title || !body}>写入洞察</Button>
        </form>
      </Panel>
      <Panel title="假设">
        <form className="form" onSubmit={(event) => { event.preventDefault(); createHypothesis.mutate() }}>
          <TextArea label="假设" value={hypothesis} onChange={setHypothesis} placeholder="必须能被实验或评测验证" />
          <Button type="submit" disabled={!hypothesis}>写入假设</Button>
        </form>
      </Panel>
      <Panel title="洞察列表">
        <RecordList items={insights.data?.items} />
      </Panel>
      <Panel title="假设列表">
        <RecordList items={hypotheses.data?.items} />
      </Panel>
    </div>
  )
}
