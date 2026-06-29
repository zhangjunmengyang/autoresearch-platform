import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button, Panel, RecordList, TextArea, TextInput } from '@/components/Primitives'
import { getListData, postData, type RecordItem } from '@/lib/api'

export function InsightsPage() {
  const queryClient = useQueryClient()
  const [title, setTitle] = useState('')
  const [hypothesis, setHypothesis] = useState('')
  const [expectedEffect, setExpectedEffect] = useState('')
  const [ideaId, setIdeaId] = useState('')
  const hypotheses = useQuery({ queryKey: ['hypotheses'], queryFn: () => getListData<RecordItem>('/api/v1/hypotheses') })
  const createHypothesis = useMutation({
    mutationFn: () => postData('/api/v1/hypotheses', {
      title,
      hypothesis,
      expected_effect: expectedEffect || '形成可度量改进',
      acceptance_criteria: { evidence_required: true },
      rejection_criteria: { no_signal_or_untraceable: true },
      source_refs: ideaId ? [{ type: 'source', id: ideaId }] : [],
    }),
    onSuccess: () => {
      setTitle('')
      setHypothesis('')
      setExpectedEffect('')
      setIdeaId('')
      queryClient.invalidateQueries({ queryKey: ['hypotheses'] })
    },
  })

  return (
    <div className="grid-two">
      <Panel title="Hypothesis">
        <form className="form" onSubmit={(event) => { event.preventDefault(); createHypothesis.mutate() }}>
          <TextInput label="标题" value={title} onChange={setTitle} placeholder="本轮要验证的假设名称" />
          <TextArea label="假设" value={hypothesis} onChange={setHypothesis} placeholder="必须能被实验或评测验证" />
          <TextArea label="预期效应" value={expectedEffect} onChange={setExpectedEffect} placeholder="指标、现象或能力应如何变化" />
          <TextInput label="Idea ID" value={ideaId} onChange={setIdeaId} placeholder="可选：idea_..." />
          <Button type="submit" disabled={!title || !hypothesis}>写入 Hypothesis</Button>
        </form>
      </Panel>
      <Panel title="Hypothesis 列表">
        <RecordList items={hypotheses.data?.items} />
      </Panel>
    </div>
  )
}
