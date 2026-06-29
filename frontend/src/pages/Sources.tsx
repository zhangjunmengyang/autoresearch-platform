import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button, Panel, RecordList, SelectInput, TextArea, TextInput } from '@/components/Primitives'
import { getListData, postData, type RecordItem } from '@/lib/api'

const ideaKinds = [
  { value: 'paper', label: '论文' },
  { value: 'repo', label: '代码仓库' },
  { value: 'dataset', label: '数据集' },
  { value: 'benchmark_gap', label: '评测缺口' },
  { value: 'researcher_idea', label: '研究员想法' },
  { value: 'runtime_observation', label: '运行观察' },
  { value: 'failure_case', label: '历史失败' },
  { value: 'open_question', label: '开放问题' },
  { value: 'artifact_ref', label: '结果引用' },
]

export function SourcesPage() {
  const queryClient = useQueryClient()
  const [kind, setKind] = useState('paper')
  const [title, setTitle] = useState('')
  const [uri, setUri] = useState('')
  const [summary, setSummary] = useState('')
  const ideas = useQuery({ queryKey: ['ideas'], queryFn: () => getListData<RecordItem>('/api/v1/ideas') })
  const create = useMutation({
    mutationFn: () => postData('/api/v1/ideas', { kind, title, uri, summary }),
    onSuccess: () => {
      setTitle('')
      setUri('')
      setSummary('')
      queryClient.invalidateQueries({ queryKey: ['ideas'] })
    },
  })

  return (
    <div className="grid-two">
      <Panel title="Idea Pool">
        <form className="form" onSubmit={(event) => { event.preventDefault(); create.mutate() }}>
          <SelectInput label="来源类型" value={kind} onChange={setKind} options={ideaKinds} />
          <TextInput label="标题" value={title} onChange={setTitle} placeholder="论文、repo、评测缺口或研究员想法" />
          <TextInput label="URI" value={uri} onChange={setUri} placeholder="可选：论文、仓库、数据集或外部结果地址" />
          <TextArea label="摘要" value={summary} onChange={setSummary} placeholder="保留可追溯摘要，不粘贴大文件原文" />
          <Button type="submit" disabled={!title || create.isPending}>写入 Idea</Button>
        </form>
      </Panel>
      <Panel title="Idea 列表">
        <RecordList items={ideas.data?.items} />
      </Panel>
    </div>
  )
}
