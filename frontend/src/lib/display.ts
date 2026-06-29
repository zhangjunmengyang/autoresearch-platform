const keyLabels: Record<string, string> = {
  id: '标识',
  type: '类型',
  kind: '类型',
  title: '标题',
  summary: '摘要',
  score: '分数',
  scores: '分数',
  runner: '运行方',
  adapter: '适配器',
  runtime: '运行时',
  entrypoint: '入口',
  artifact_refs: '成果引用',
  evidence_refs: '证据引用',
  source_refs: '资料引用',
  provenance: '来源',
  payload: '载荷',
  branch: '分支',
  sha: '提交',
  status: '状态',
  name: '名称',
}

const typeLabels: Record<string, string> = {
  artifact: '成果引用',
  benchmark_run: '评测运行',
  benchmark: '评测套件',
  source: '资料',
  insight: '洞察',
  hypothesis: '假设',
  research_question: '研究问题',
  question: '研究问题',
  method_card: '方法卡',
  protocol: '预注册协议',
  session: '研究账本',
  research_session: '研究账本',
  research_round: '研究轮次',
  round: '研究轮次',
  event: '过程事件',
  experiment: '实验记录',
  review: '审查',
  decision: '决策',
  experience: '经验',
  commit: '提交',
}

export function labelKey(key: string) {
  return keyLabels[key] || key
}

export function labelRecordType(type?: string) {
  if (!type) return '记录'
  return typeLabels[type] || type
}

export function formatScalar(value: unknown, empty = '未记录') {
  if (value === null || value === undefined || value === '') return empty
  if (typeof value === 'boolean') return value ? '是' : '否'
  return String(value)
}

export function formatRefs(value: unknown, empty = '未记录') {
  if (!Array.isArray(value) || !value.length) return empty
  return value.map((ref) => {
    if (!ref || typeof ref !== 'object') return String(ref)
    const record = ref as Record<string, unknown>
    const type = labelRecordType(String(record.type || record.kind || '记录'))
    const id = record.id || record.record_id || record.sha || record.uri
    return `${type} ${formatScalar(id)}`
  }).join('，')
}

function formatNestedValue(value: unknown) {
  if (Array.isArray(value)) return formatRefs(value, `${value.length} 项`)
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>
    if (record.id || record.record_id || record.sha || record.uri) {
      return formatRefs([record])
    }
    const count = Object.keys(record).length
    return count ? `${count} 项` : '无'
  }
  return formatScalar(value)
}

export function formatKeyValueSummary(value: unknown, empty = '无') {
  if (!value) return empty
  if (Array.isArray(value)) return formatRefs(value, empty)
  if (typeof value !== 'object') return formatScalar(value, empty)
  const entries = Object.entries(value as Record<string, unknown>).filter(([, item]) => {
    return item !== null && item !== undefined && item !== ''
  })
  if (!entries.length) return empty
  return entries.map(([key, item]) => `${labelKey(key)} ${formatNestedValue(item)}`).join('，')
}
