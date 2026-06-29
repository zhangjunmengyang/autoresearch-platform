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
  runtime: '运行方',
  entrypoint: '入口',
  artifact_refs: '成果引用',
  evidence_refs: '证据引用',
  source_refs: '资料引用',
  provenance: '来源',
  payload: '载荷',
  branch: '分支',
  sha: '提交哈希',
  uri: '地址',
  url: '地址',
  mime: '媒体类型',
  hash: '哈希',
  session_id: '账本标识',
  round_id: '轮次标识',
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

const termLabels: Record<string, string> = {
  artifact_ref: '成果引用',
  artifact_refs: '成果引用',
  benchmark_result: '评测结果',
  benchmark_results: '评测结果',
  benchmark_run: '评测运行',
  benchmark_suite: '评测套件',
  evidence_record: '证据记录',
  research_question: '研究问题',
  research_round: '研究轮次',
  method_card: '方法卡',
  protocol: '协议',
  decision: '决策',
  badcase_summary: '失败样本摘要',
  score_report: '分数报告',
  run_log: '运行日志',
  source_registry: '资料索引',
  synthesis_note: '综合笔记',
  baseline_artifact: '基线成果',
  reproduction_artifact: '复现成果',
  result_artifact: '结果成果',
  environment_manifest: '环境清单',
  config_diff: '配置差异',
  failure_log: '失败日志',
  diagnostic_summary: '诊断摘要',
  fix_result: '修复结果',
  dataset_ref: '数据集引用',
  source_ref: '资料引用',
  evidence_ref: '证据引用',
  current_baseline: '当前基线',
  benchmark_comparison: '评测对比',
  score: '分数',
  recall: '召回率',
  pass_rate: '通过率',
  config: '配置',
  scores: '分数',
  summary: '摘要',
  object: '对象',
  array: '数组',
  string: '文本',
  external_runner: '外部运行方',
  external: '外部',
  report: '报告',
  chart: '图表',
  log: '日志',
  paper: '论文',
  dataset: '数据集',
  checkpoint: '检查点',
  code_repo: '代码仓库',
  benchmark_gap: '评测缺口',
  researcher_note: '研究员想法',
  runtime_observation: '运行观察',
  main: '主线',
  created_at: '创建时间',
  updated_at: '更新时间',
  before_experiment: '实验前',
  before_review: '审查前',
  before_decision: '决策前',
  before_curation: '经验维护前',
  observation: '观察',
  tool_run: '工具运行',
  human_instruction: '外部指令',
  runtime_event: '外部运行事件',
  read_only_deployment_readiness_no_external_access: '只读部署检查，不访问外部运行方。',
  read_only_onboarding_no_execution_no_external_access: '只读接入检查，不执行任务，不访问外部运行方。',
  read_only_methodology_templates_no_execution: '只读方法模板，不执行实验。',
  ablation: '消融实验',
  reproduction: '复现实验',
  failure_analysis: '失败分析',
  literature_synthesis: '文献综合',
  not_tested: '未测试',
  inconclusive: '不确定',
  higher_is_better: '越高越好',
  lower_is_better: '越低越好',
  ready: '就绪',
  pass: '通过',
  warn: '警告',
  ok: '正常',
  json: '本地文件',
  postgres: '关系数据库',
}

const textReplacements: Array<[RegExp, string]> = [
  [/\b(GET|POST|PATCH|DELETE) \/api\/v1\/[^\s，。；]*/g, '对应接口'],
  [/Idea Pool -> Hypothesis -> Plan -> Experiment -> Result -> Review -> Decision -> Lesson -> Next Hypothesis/g, '想法池 -> 假设 -> 计划 -> 实验 -> 结果 -> 审查 -> 决策 -> 经验 -> 下一轮假设'],
  [/Idea Pool -> Hypothesis -> Plan -> Experiment -> Result -> Review -> Decision -> Lesson/g, '想法池 -> 假设 -> 计划 -> 实验 -> 结果 -> 审查 -> 决策 -> 经验'],
  [/read_only_deployment_readiness_no_external_access/g, '只读部署检查，不访问外部运行方。'],
  [/read_only_onboarding_no_execution_no_external_access/g, '只读接入检查，不执行任务，不访问外部运行方。'],
  [/read_only_methodology_templates_no_execution/g, '只读方法模板，不执行实验。'],
  [/\bAutoResearch\b/g, '自动研究'],
  [/\bauto-research\b/g, '自动研究使用流程'],
  [/\bexternal-runtime-adapter\b/g, '外部运行方适配器'],
  [/\bexternal-runtime\b/g, '外部运行方'],
  [/\bruntime-owned\b/g, '外部运行方自有入口'],
  [/\bfrontend-demo\b/g, '前端演示'],
  [/\bagent-memory\b/g, '智能体记忆'],
  [/\bai-for-science\b/g, '智能科研'],
  [/\bAI for Science\b/g, '智能科研'],
  [/\bOpenAPI metadata\b/g, '开放接口元数据'],
  [/\bOpenAPI\b/g, '开放接口'],
  [/\bREST\b/g, '标准接口'],
  [/\bExternal Runtime\b/g, '外部运行方'],
  [/\bexternal Runtime\b/g, '外部运行方'],
  [/\bRuntime\b/g, '运行方'],
  [/\bruntime\b/g, '运行方'],
  [/\bagent loop\b/g, '智能体循环'],
  [/\bAgent\b/g, '智能体'],
  [/\bagent\b/g, '智能体'],
  [/\bSkill\b/g, '技能'],
  [/\bskill\b/g, '技能'],
  [/\bIdea Pool\b/g, '想法池'],
  [/\bHypothesis\b/g, '假设'],
  [/\bPlan\b/g, '计划'],
  [/\bExperiment\b/g, '实验'],
  [/\bResult\b/g, '结果'],
  [/\bReview\b/g, '审查'],
  [/\bDecision\b/g, '决策'],
  [/\bLesson\b/g, '经验'],
  [/\bNext Hypothesis\b/g, '下一轮假设'],
  [/\bbenchmark gap\b/g, '评测缺口'],
  [/\bbenchmark\b/g, '评测'],
  [/\bBenchmark\b/g, '评测'],
  [/\bartifact URI\b/g, '成果地址'],
  [/\bartifact\b/g, '成果'],
  [/\bArtifact\b/g, '成果'],
  [/\bstore\b/g, '存储'],
  [/\bschema\b/g, '结构'],
  [/\bmetadata\b/g, '元数据'],
  [/\bcollection\b/g, '记录集'],
  [/\bJSON\b/g, '本地文件'],
  [/\bjson\b/g, '本地文件'],
  [/\bPostgreSQL\b/g, '关系数据库'],
  [/\bAlembic\b/g, '数据库迁移'],
  [/\bPDF\b/g, '文档'],
  [/\bURI\b/g, '地址'],
  [/\bURL\b/g, '地址'],
  [/\bMIME\b/g, '媒体类型'],
  [/\bID\b/g, '标识'],
  [/\bhash\b/g, '哈希'],
  [/\brepo\b/g, '代码仓库'],
  [/\bprompt\b/g, '提示词'],
  [/\bworkflow DAG\b/g, '工作流图'],
  [/\bworkflow\b/g, '工作流'],
  [/\bbacking records\b/g, '底层记录'],
  [/\bsource\/insight\b/g, '资料与洞察'],
  [/\bevidence-backed\b/g, '有证据支撑的'],
  [/\bRAG\b/g, '检索增强'],
  [/\badapter\b/g, '适配器'],
  [/\bsuite\b/g, '套件'],
  [/\brun\b/g, '运行'],
  [/\bcritic\b/g, '审查器'],
  [/\breview audit\b/g, '审查审计'],
  [/\breview\b/g, '审查'],
  [/\bdecision record\b/g, '决策记录'],
  [/\bclaim\b/g, '主张'],
  [/\bevidence_refs\b/g, '证据引用'],
  [/\bsummary\b/g, '摘要'],
  [/\bpreview\/apply\b/g, '预览和应用'],
  [/\bcuration\b/g, '显式维护'],
  [/\bclose session\b/g, '关闭账本'],
  [/\bledger\b/g, '账本'],
  [/\bsession\b/g, '账本'],
  [/\bworktree\b/g, '工作树'],
  [/\bbranch\b/g, '分支'],
  [/\bcommit\b/g, '提交'],
  [/\bbadcase\b/g, '失败样本'],
  [/\bsource\b/g, '资料'],
  [/\binsight\b/g, '洞察'],
  [/\bhypothesis\b/g, '假设'],
  [/\bresearch question\b/g, '研究问题'],
  [/\bmethod card\b/g, '方法卡'],
  [/\bprotocol_defaults\b/g, '协议默认值'],
  [/\bprotocol\b/g, '协议'],
  [/\bbaseline\b/g, '基线'],
  [/\breproduction\b/g, '复现'],
  [/\bresult\b/g, '结果'],
  [/\benvironment\b/g, '环境'],
  [/\bmanifest\b/g, '清单'],
  [/\bfails_to_replicate\b/g, '复现失败'],
  [/\bfails to replicate\b/g, '复现失败'],
  [/\breplicates\b/g, '复现通过'],
  [/\bround\b/g, '轮次'],
  [/\bconfig\b/g, '配置'],
  [/\bdiff\b/g, '差异'],
  [/\baudit\b/g, '审计'],
  [/\bcompleted\b/g, '已完成'],
  [/\brefs\b/g, '引用'],
  [/\bprovenance\.runner\b/g, '运行来源'],
  [/\bprovenance\b/g, '来源'],
  [/\bfailed\b/g, '失败'],
  [/\bdegraded\b/g, '降级'],
  [/\bevent\b/g, '事件'],
  [/\bexperiment\b/g, '实验'],
  [/\bfailure\b/g, '失败'],
  [/\blog\b/g, '日志'],
  [/\bdiagnostic\b/g, '诊断'],
  [/\bfix\b/g, '修复'],
  [/\bcontradicts\b/g, '反证'],
  [/\binconclusive\b/g, '不确定'],
  [/\bkeep\b/g, '保留'],
  [/\bdiscard\b/g, '丢弃'],
  [/\bcontinue\b/g, '继续'],
  [/\bretry\b/g, '重试'],
  [/\bblocked\b/g, '阻塞'],
  [/\barchived\b/g, '归档'],
  [/运行时/g, '运行方'],
]

export function labelKey(key: string) {
  return keyLabels[key] || key
}

export function labelRecordType(type?: string) {
  if (!type) return '记录'
  return typeLabels[type] || type
}

export function labelTerm(value?: string) {
  if (!value) return '未记录'
  return termLabels[value] || formatHumanText(value.replace(/_/g, ' '))
}

export function formatHumanText(value: unknown, empty = '未记录') {
  if (value === null || value === undefined || value === '') return empty
  return textReplacements.reduce((text, [pattern, replacement]) => {
    return text.replace(pattern, replacement)
  }, String(value))
}

export function formatScalar(value: unknown, empty = '未记录') {
  if (value === null || value === undefined || value === '') return empty
  if (typeof value === 'boolean') return value ? '是' : '否'
  if (typeof value === 'string') return formatHumanText(value)
  return String(value)
}

export function formatTimestamp(value: unknown) {
  if (!value) return '时间未知'
  const date = new Date(String(value))
  if (Number.isNaN(date.getTime())) return '时间已记录'
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
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
