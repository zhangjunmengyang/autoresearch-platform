import { readFileSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'
import assert from 'node:assert/strict'

const root = resolve(import.meta.dirname)
const app = readFileSync(resolve(root, 'App.tsx'), 'utf8')
const api = readFileSync(resolve(root, 'lib/api.ts'), 'utf8')
const pageConfig = readFileSync(resolve(root, 'lib/page-config.ts'), 'utf8')
const appShell = readFileSync(resolve(root, 'components/AppShell.tsx'), 'utf8')
const primitives = readFileSync(resolve(root, 'components/Primitives.tsx'), 'utf8')
const globals = readFileSync(resolve(root, 'styles/globals.css'), 'utf8')
const dashboardPage = readFileSync(resolve(root, 'pages/Dashboard.tsx'), 'utf8')
const experiencesPage = readFileSync(resolve(root, 'pages/Experiences.tsx'), 'utf8')
const reviewsPage = readFileSync(resolve(root, 'pages/Reviews.tsx'), 'utf8')
const evidencePage = readFileSync(resolve(root, 'pages/Evidence.tsx'), 'utf8')
const artifactsPage = readFileSync(resolve(root, 'pages/Artifacts.tsx'), 'utf8')
const auditPage = readFileSync(resolve(root, 'pages/Audit.tsx'), 'utf8')
const researchWorkbenchPage = readFileSync(resolve(root, 'pages/ResearchWorkbench.tsx'), 'utf8')
const researchContextPage = readFileSync(resolve(root, 'pages/ResearchContext.tsx'), 'utf8')
const researchReadinessPage = readFileSync(resolve(root, 'pages/ResearchReadiness.tsx'), 'utf8')
const researchRoundsPage = readFileSync(resolve(root, 'pages/ResearchRounds.tsx'), 'utf8')
const statusPage = readFileSync(resolve(root, 'pages/Status.tsx'), 'utf8')
const benchmarksPage = readFileSync(resolve(root, 'pages/Benchmarks.tsx'), 'utf8')
const methodologyPage = readFileSync(resolve(root, 'pages/Methodology.tsx'), 'utf8')
const capabilitiesPage = readFileSync(resolve(root, 'pages/Capabilities.tsx'), 'utf8')
const pages = readdirSync(resolve(root, 'pages')).join('\n')
const pageSource = readdirSync(resolve(root, 'pages'))
  .filter((file) => file.endsWith('.tsx'))
  .map((file) => readFileSync(resolve(root, 'pages', file), 'utf8'))
  .join('\n')

for (const route of [
  '/dashboard',
  '/sources',
  '/insights',
  '/research',
  '/research/methodology',
  '/research-queue',
  '/research/context',
  '/research/readiness',
  '/research/rounds',
  '/sessions',
  '/sessions/:id',
  '/research/audit',
  '/evidence',
  '/artifacts',
  '/benchmarks',
  '/reviews',
  '/decisions',
  '/knowledge/experiences',
  '/capabilities',
  '/status',
]) {
  assert(app.includes(`path="${route}"`) || app.includes(`to="${route}"`), `missing route ${route}`)
}

const allowedNavPaths = new Set([
  '/dashboard',
  '/sources',
  '/insights',
  '/research',
  '/research/methodology',
  '/research-queue',
  '/research/context',
  '/research/readiness',
  '/research/rounds',
  '/sessions',
  '/research/audit',
  '/evidence',
  '/artifacts',
  '/benchmarks',
  '/reviews',
  '/decisions',
  '/knowledge/experiences',
  '/capabilities',
  '/status',
])

const navPaths = [...pageConfig.matchAll(/path: '([^']+)'/g)].map((match) => match[1])
for (const navPath of navPaths) {
  assert(allowedNavPaths.has(navPath), `unknown navigation path ${navPath}`)
}

for (const label of ['总览看板', 'Idea Pool 想法池', 'Hypothesis 假设', 'Plan / Experiment 计划实验', 'Experiment 账本', 'Review / Decision 复盘决策', 'Lesson 经验', '能力目录', '系统状态']) {
  assert(pageConfig.includes(label), `missing nav label ${label}`)
}

const researchGroup = pageConfig.match(/title: '研究',[\s\S]*?title: '知识'/)?.[0] || ''
const researchNavLabels = [...researchGroup.matchAll(/label: '([^']+)'/g)].map((match) => match[1])
assert.deepEqual(researchNavLabels, ['Plan / Experiment 计划实验', 'Experiment 账本', 'Review / Decision 复盘决策'], 'research navigation should stay compact')
for (const hiddenResearchLabel of ['科研方法论', '研究队列', '研究上下文', '就绪检查', '研究轮次', '过程审计', '成果引用', '评测登记', '审查事件', '决策记录']) {
  assert(!researchNavLabels.includes(hiddenResearchLabel), `low-frequency research entry leaked into main nav: ${hiddenResearchLabel}`)
}

for (const retainedPath of ['/sources', '/insights', '/research/methodology', '/sessions', '/artifacts', '/evidence', '/decisions', '/knowledge/experiences', '/research/context', '/research/readiness', '/research/rounds', '/research/audit', '/benchmarks', '/reviews']) {
  assert(researchWorkbenchPage.includes(retainedPath), `research workbench should link to ${retainedPath}`)
}

for (const loopLabel of ['Idea Pool', 'Hypothesis', 'Plan', 'Experiment', 'Result', 'Review', 'Decision', 'Lesson']) {
  assert(dashboardPage.includes(loopLabel), `dashboard missing loop label ${loopLabel}`)
  assert(researchWorkbenchPage.includes(loopLabel), `research workbench missing loop label ${loopLabel}`)
}

const navLabels = [...pageConfig.matchAll(/label: '([^']+)'/g)].map((match) => match[1])
for (const label of navLabels) {
  assert(/[\u4e00-\u9fff]/.test(label), `navigation label is not Chinese: ${label}`)
}

for (const forbidden of ['market', 'trading', 'factor', 'strategy', 'DCA', 'Binance']) {
  assert(!pageConfig.toLowerCase().includes(forbidden.toLowerCase()), `legacy nav leaked: ${forbidden}`)
}

for (const forbidden of ['/knowledge/graph', '科研图谱', '/api/v1/graph', '/api/v1/research/lineage', '研究血缘']) {
  assert(!app.includes(forbidden), `graph route leaked into app: ${forbidden}`)
  assert(!pageConfig.includes(forbidden), `graph nav leaked: ${forbidden}`)
  assert(!pageSource.includes(forbidden), `graph page source leaked: ${forbidden}`)
}

assert(!pages.includes('Graph.tsx'), 'graph page should not be part of the core workbench')

for (const required of ['Dashboard.tsx', 'Audit.tsx', 'Artifacts.tsx', 'Benchmarks.tsx', 'Decisions.tsx', 'Evidence.tsx', 'Experiences.tsx', 'Methodology.tsx', 'ResearchContext.tsx', 'ResearchReadiness.tsx', 'ResearchRounds.tsx', 'ResearchWorkbench.tsx', 'Reviews.tsx']) {
  assert(pages.includes(required), `missing page ${required}`)
}

assert(api.includes('getListData'), 'missing list endpoint helper')
assert(api.includes('requestEnvelope'), 'missing API envelope helper')
assert(primitives.includes('WarningList'), 'missing WarningList')
assert(primitives.includes('ErrorMessage'), 'missing ErrorMessage')
assert(!pageSource.includes('getData<RecordItem[]>'), 'list page still reads raw array data')
assert(experiencesPage.includes('preview.data?.warnings'), 'experience preview warnings are not rendered')
assert(experiencesPage.includes('来源追踪'), 'experience preview does not render source trace')
assert(experiencesPage.includes('治理缺口'), 'experience preview does not render governance gaps')
assert(experiencesPage.includes('建议动作'), 'experience preview does not render recommended next actions')
assert(reviewsPage.includes('review.subject'), 'reviews page does not render reviewed subject')
assert(artifactsPage.includes('/api/v1/results'), 'result page does not query canonical results endpoint')
assert(artifactsPage.includes('/api/v1/artifacts/audit'), 'artifacts page does not query artifact audit')
assert(artifactsPage.includes('审计状态'), 'artifacts page does not render artifact audit state')
assert(artifactsPage.includes('元数据缺口'), 'artifacts page does not render artifact metadata issues')
assert(artifactsPage.includes('建议动作'), 'artifacts page does not render artifact audit recommended actions')
assert(auditPage.includes('/api/v1/research/audit/export'), 'audit page does not query audit export bundle')
assert(auditPage.includes('审计导出包'), 'audit page does not render audit export bundle')
assert(auditPage.includes('导出清单'), 'audit page does not render export manifest')
assert(auditPage.includes('质量门'), 'audit page does not render export quality gates')
assert(auditPage.includes('复现交接包'), 'audit page does not render reproducibility bundle')
assert(auditPage.includes('复现检查清单'), 'audit page does not render reproducibility checklist')
assert(auditPage.includes('外部成果验证'), 'audit page does not render external artifact verification')
assert(auditPage.includes('交接步骤'), 'audit page does not render handoff steps')
assert(reviewsPage.includes('/api/v1/reviews/audit'), 'reviews page does not query review audit')
assert(reviewsPage.includes('审查质量门'), 'reviews page does not render review audit gate')
assert(reviewsPage.includes('质量缺口'), 'reviews page does not render review audit issues')
assert(reviewsPage.includes('建议动作'), 'reviews page does not render review audit recommended actions')
assert(evidencePage.includes('/api/v1/evidence-records/summary'), 'evidence page does not query evidence summary')
assert(evidencePage.includes('证据概览'), 'evidence page does not render evidence summary')
assert(evidencePage.includes('建议动作'), 'evidence page does not render recommended next action')
assert(evidencePage.includes('质量缺口'), 'evidence page does not render evidence quality gaps')
assert(evidencePage.includes('覆盖范围'), 'evidence page does not render evidence coverage')
assert(evidencePage.includes('复现计划'), 'evidence page does not render replication plan')
assert(researchContextPage.includes('/api/v1/research/context'), 'research context page does not query context endpoint')
assert(researchContextPage.includes('恢复上下文'), 'research context page does not render recovery context')
assert(researchContextPage.includes('建议动作'), 'research context page does not render next actions')
assert(appShell.includes("'/research/context': '研究上下文'"), 'app shell title missing research context route')
assert(appShell.includes("'/research/readiness': '就绪检查'"), 'app shell title missing research readiness route')
assert(appShell.includes("'/research/rounds': '研究轮次'"), 'app shell title missing research rounds route')
assert(globals.includes('overflow-x: auto'), 'mobile navigation should not push content off the first viewport')
assert(globals.includes('flex-wrap: nowrap'), 'mobile navigation should stay in a compact horizontal rail')
assert(researchReadinessPage.includes('/api/v1/research/readiness'), 'research readiness page does not query readiness endpoint')
assert(researchReadinessPage.includes('就绪检查'), 'research readiness page does not render readiness check')
assert(researchReadinessPage.includes('阻塞缺口'), 'research readiness page does not render blocking gaps')
assert(researchReadinessPage.includes('检查项'), 'research readiness page does not render checks')
assert(researchReadinessPage.includes('建议动作'), 'research readiness page does not render recommended actions')
assert(researchRoundsPage.includes('/api/v1/research/rounds'), 'research rounds page does not query rounds endpoint')
assert(researchRoundsPage.includes('requestEnvelope<RoundDetail>'), 'research rounds page does not query round trace detail')
assert(researchRoundsPage.includes('研究轮次'), 'research rounds page does not render round ledger')
assert(researchRoundsPage.includes('追踪包'), 'research rounds page does not render round trace pack')
assert(researchRoundsPage.includes('未解析引用'), 'research rounds page does not render unresolved refs')
assert(researchRoundsPage.includes('建议动作'), 'research rounds page does not render trace next actions')
assert(researchRoundsPage.includes('工作树'), 'research rounds page does not render worktree references in Chinese')
assert(researchRoundsPage.includes('提交'), 'research rounds page does not render commit references in Chinese')
assert(researchRoundsPage.includes('roundBranch'), 'research rounds completion does not preserve the round branch reference')
assert(methodologyPage.includes('/api/v1/research/design/audit'), 'methodology page does not query design audit')
assert(methodologyPage.includes('/api/v1/plans'), 'methodology page does not query canonical plans endpoint')
assert(methodologyPage.includes('/api/v1/research/method-templates'), 'methodology page does not query method templates')
assert(methodologyPage.includes('方法模板'), 'methodology page does not render method templates')
assert(methodologyPage.includes('复现实验'), 'methodology page does not render reproduction template')
assert(methodologyPage.includes('消融实验'), 'methodology page does not render ablation template')
assert(methodologyPage.includes('评测对比'), 'methodology page does not render benchmark comparison template')
assert(methodologyPage.includes('研究设计审计'), 'methodology page does not render design audit')
assert(methodologyPage.includes('预注册质量门'), 'methodology page does not render preregistration gate')
assert(methodologyPage.includes('可回答问题'), 'methodology page does not render answerability gate')
assert(methodologyPage.includes('可证伪假设'), 'methodology page does not render falsifiability gate')
assert(methodologyPage.includes('协议执行边界'), 'methodology page does not render protocol boundary')
assert(benchmarksPage.includes('/api/v1/benchmarks/audit'), 'benchmarks page does not query benchmark audit')
assert(benchmarksPage.includes('/api/v1/benchmark-runs/compare'), 'benchmarks page does not query benchmark run comparison')
assert(benchmarksPage.includes('评测合同审计'), 'benchmarks page does not render benchmark contract audit')
assert(benchmarksPage.includes('结果对比'), 'benchmarks page does not render benchmark run comparison')
assert(benchmarksPage.includes('最佳运行'), 'benchmarks page does not render best benchmark run')
assert(benchmarksPage.includes('指标范围'), 'benchmarks page does not render benchmark score range')
assert(benchmarksPage.includes('证据准备缺口'), 'benchmarks page does not render benchmark evidence readiness gaps')
assert(benchmarksPage.includes('外部适配器'), 'benchmarks page does not render external adapter contract')
assert(benchmarksPage.includes('输入合同'), 'benchmarks page does not render benchmark input contract')
assert(benchmarksPage.includes('输出合同'), 'benchmarks page does not render benchmark output contract')
assert(benchmarksPage.includes('成果要求'), 'benchmarks page does not render benchmark artifact requirements')
assert(!auditPage.includes('JSON.stringify(event.payload'), 'audit page still renders raw event payload JSON')
assert(!benchmarksPage.includes('JSON.stringify(run.scores'), 'benchmarks page still renders raw score JSON')
assert(!benchmarksPage.includes('JSON.stringify(run.artifact_refs'), 'benchmarks page still renders raw artifact ref JSON')
assert(!benchmarksPage.includes('JSON.stringify(run.provenance'), 'benchmarks page still renders raw provenance JSON')
assert(researchRoundsPage.includes('成果引用'), 'research rounds page should render artifact references in Chinese')
assert(!researchRoundsPage.includes(' · artifact '), 'research rounds page still renders artifact as user-facing English')
assert(statusPage.includes('/api/v1/system/readiness'), 'status page does not query system readiness')
assert(statusPage.includes('/api/v1/system/security'), 'status page does not query system security')
assert(statusPage.includes('部署就绪'), 'status page does not render deployment readiness')
assert(statusPage.includes('检查项'), 'status page does not render readiness checks')
assert(statusPage.includes('建议动作'), 'status page does not render readiness recommended actions')
assert(statusPage.includes('认证与审计'), 'status page does not render security and audit status')
assert(statusPage.includes('公开入口'), 'status page does not render public endpoints')
assert(statusPage.includes('审计策略'), 'status page does not render audit policy')
assert(capabilitiesPage.includes('/api/v1/agent/onboarding'), 'capabilities page does not query agent onboarding bundle')
assert(capabilitiesPage.includes('Agent 接入自检'), 'capabilities page does not render agent onboarding status')
assert(capabilitiesPage.includes('Skill 加载顺序'), 'capabilities page does not render skill loading order')
assert(capabilitiesPage.includes('建议首批调用'), 'capabilities page does not render recommended first calls')
assert(capabilitiesPage.includes('只读边界'), 'capabilities page does not render onboarding integrity boundary')

console.log('frontend static contract ok')
