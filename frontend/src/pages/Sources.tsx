import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button, Panel, RecordList, SelectInput, TextArea, TextInput } from '@/components/Primitives'
import { getListData, postData, type RecordItem } from '@/lib/api'

const sourceKinds = [
  { value: 'paper', label: '论文' },
  { value: 'url', label: '网页' },
  { value: 'dataset', label: '数据集' },
  { value: 'repo', label: '代码仓库' },
  { value: 'note', label: '笔记' },
  { value: 'artifact_ref', label: '成果引用' },
  { value: 'human_command', label: '外部目标' },
  { value: 'runtime_input', label: '外部 Runtime 输入' },
]

export function SourcesPage() {
  const queryClient = useQueryClient()
  const [kind, setKind] = useState('paper')
  const [title, setTitle] = useState('')
  const [uri, setUri] = useState('')
  const [summary, setSummary] = useState('')
  const sources = useQuery({ queryKey: ['sources'], queryFn: () => getListData<RecordItem>('/api/v1/sources') })
  const create = useMutation({
    mutationFn: () => postData('/api/v1/sources', { kind, title, uri, summary }),
    onSuccess: () => {
      setTitle('')
      setUri('')
      setSummary('')
      queryClient.invalidateQueries({ queryKey: ['sources'] })
    },
  })

  return (
    <div className="grid-two">
      <Panel title="新增输入">
        <form className="form" onSubmit={(event) => { event.preventDefault(); create.mutate() }}>
          <SelectInput label="类型" value={kind} onChange={setKind} options={sourceKinds} />
          <TextInput label="标题" value={title} onChange={setTitle} placeholder="论文、资料、目标或外部输入名称" />
          <TextInput label="URI" value={uri} onChange={setUri} placeholder="网址、仓库路径或成果引用" />
          <TextArea label="摘要" value={summary} onChange={setSummary} placeholder="保留可追溯摘要，不粘贴大文件原文" />
          <Button type="submit" disabled={!title || create.isPending}>写入资料</Button>
        </form>
      </Panel>
      <Panel title="输入列表">
        <RecordList items={sources.data?.items} />
      </Panel>
    </div>
  )
}
