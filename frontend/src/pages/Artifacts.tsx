import { useQuery } from '@tanstack/react-query'
import { ErrorMessage, Panel, RecordList, StatusBadge, TextInput } from '@/components/Primitives'
import { getData, getListData, type RecordItem } from '@/lib/api'
import { useState } from 'react'

type ArtifactIssue = {
  code?: string
  severity?: string
  message?: string
  safety?: string
}

type ArtifactAuditItem = {
  artifact_id?: string
  title?: string
  artifact_type?: string
  session_id?: string
  uri?: string
  storage?: string
  state?: string
  issues?: ArtifactIssue[]
}

type ArtifactAudit = {
  state: string
  total: number
  issue_counts: Record<string, number>
  artifact_ids_with_issues: string[]
  items: ArtifactAuditItem[]
  recommended_next_actions: Array<{
    endpoint?: string
    reason?: string
    priority?: string
  }>
  safety: string
}

const issueLabels: Record<string, string> = {
  missing_uri: '缺少 URI',
  missing_hash: '缺少 Hash',
  missing_size: '缺少大小',
  missing_summary: '缺少摘要',
  missing_storage: '缺少存储',
  inline_payload_risk: '疑似内联内容',
}

const severityLabels: Record<string, string> = {
  high: '高',
  medium: '中',
  low: '低',
}

function formatIssueCounts(counts: Record<string, number>) {
  const entries = Object.entries(counts)
  if (!entries.length) return '暂无缺口'
  return entries.map(([code, count]) => `${issueLabels[code] || code} ${count}`).join('，')
}

export function ArtifactsPage() {
  const [query, setQuery] = useState('')
  const [sessionId, setSessionId] = useState('')
  const results = useQuery({
    queryKey: ['results', query],
    queryFn: () => getListData<RecordItem>(`/api/v1/results${query ? `?q=${encodeURIComponent(query)}` : ''}`),
  })
  const audit = useQuery({
    queryKey: ['artifact-audit', query, sessionId],
    queryFn: () => {
      const params = new URLSearchParams()
      if (query.trim()) params.set('q', query.trim())
      if (sessionId.trim()) params.set('session_id', sessionId.trim())
      const suffix = params.toString()
      return getData<ArtifactAudit>(`/api/v1/artifacts/audit${suffix ? `?${suffix}` : ''}`)
    },
  })
  const auditData = audit.data

  return (
    <div className="grid-two">
      <Panel title="Result 索引">
        <form className="form" onSubmit={(event) => event.preventDefault()}>
          <TextInput label="筛选" value={query} onChange={setQuery} placeholder="地址、标题、摘要、账本或存储位置" />
          <TextInput label="账本标识" value={sessionId} onChange={setSessionId} placeholder="可选：只审计某个账本" />
        </form>
        <div className="record-list compact">
          {(results.data?.items || []).map((result) => (
            <article className="record-row" key={result.id}>
              <div>
                <div className="record-title">{String(result.title || result.artifact_type || result.id)}</div>
                <div className="record-meta">类型 {String(result.artifact_type || '未记录')}</div>
                <div className="record-meta">账本 {String(result.session_id || '未绑定')}</div>
                <div className="record-meta">地址 {String(result.uri || '未填写')}</div>
                <div className="record-meta">存储 {String(result.storage || '外部')} · 哈希 {String(result.sha256 || '未填写')}</div>
                <div className="record-meta">摘要 {String(result.summary || '')}</div>
              </div>
            </article>
          ))}
        </div>
        {!results.data?.items.length ? <RecordList items={[]} /> : null}
      </Panel>
      <Panel title="审计状态">
        {auditData ? (
          <div className="record-list compact">
            <article className="record-row">
              <div>
                <div className="record-title">元数据缺口</div>
                <div className="record-meta">成果数量 {auditData.total}</div>
                <div className="record-meta">{formatIssueCounts(auditData.issue_counts)}</div>
                <div className="record-meta">问题成果 {auditData.artifact_ids_with_issues.join('，') || '无'}</div>
              </div>
              <StatusBadge status={auditData.state === 'ready' ? 'completed' : auditData.state} />
            </article>
            {(auditData.items || []).filter((item) => item.issues?.length).map((item) => (
              <article className="record-row" key={item.artifact_id || item.title}>
                <div>
                  <div className="record-title">{item.title || item.artifact_id}</div>
                  <div className="record-meta">成果 {item.artifact_id || '未记录'} · 账本 {item.session_id || '未绑定'}</div>
                  <div className="record-meta">地址 {item.uri || '未填写'} · 存储 {item.storage || '未记录'}</div>
                  {(item.issues || []).map((issue) => (
                    <div className="record-meta" key={`${item.artifact_id}-${issue.code}`}>
                      {issueLabels[String(issue.code)] || issue.code || '缺口'} · 严重度 {severityLabels[String(issue.severity)] || issue.severity || '未记录'} · {issue.message || ''}
                    </div>
                  ))}
                </div>
                <StatusBadge status={item.state === 'ready' ? 'completed' : item.state} />
              </article>
            ))}
            <article className="record-row">
              <div>
                <div className="record-title">建议动作</div>
                {auditData.recommended_next_actions.length ? auditData.recommended_next_actions.map((action) => (
                  <div className="record-meta" key={`${action.endpoint}-${action.reason}`}>
                    {action.endpoint || '未记录'} · {action.reason || ''}
                  </div>
                )) : <div className="record-meta">暂无建议动作</div>}
              </div>
            </article>
          </div>
        ) : <div className="empty">正在读取审计状态</div>}
        <ErrorMessage message={audit.error?.message} />
      </Panel>
      <Panel title="索引说明">
        <div className="detail-grid">
          <div><strong>{results.data?.total || 0}</strong><span>匹配数量</span></div>
          <div><strong>{results.data?.limit || 50}</strong><span>分页大小</span></div>
          <div><strong>{results.data?.sort || '-created_at'}</strong><span>排序</span></div>
        </div>
        <p className="panel-copy">
          Result 只保存外部对象的地址、哈希、媒体类型、存储位置和摘要。原始数据、报告全文、媒体、检查点和大型评测输出应留在外部存储。
        </p>
      </Panel>
    </div>
  )
}
