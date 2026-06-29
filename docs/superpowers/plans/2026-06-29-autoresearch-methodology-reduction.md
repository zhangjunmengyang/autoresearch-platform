# AutoResearch Methodology Reduction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 收敛 AutoResearch Platform 的产品和文档表达，使它围绕 FARS/Karpathy 风格的 `Idea -> Hypothesis -> Plan -> Experiment -> Result -> Review -> Decision -> Lesson` 方法论闭环，而不是暴露一组松散科研对象。

**Architecture:** 首轮做非破坏性收敛层: 保留现有后端 endpoint 以避免一次性打碎合同，但把架构文档、Runtime cookbook、Dashboard、ResearchWorkbench 和前端静态合同改成新的核心闭环。后续破坏性 OpenAPI 合并以这个闭环为目标，把旧对象逐步合并到 `idea/hypothesis/plan/experiment/result/review/decision/lesson`。

**Tech Stack:** FastAPI/OpenAPI, React/Vite, TanStack Query, Markdown docs, Node static contract tests, pytest.

---

### Task 1: Documentation Convergence

**Files:**
- Modify: `docs/architecture/reference.md`
- Modify: `docs/architecture/external-runtime-api.md`
- Modify: `docs/examples/runtime-cookbook.md`

- [x] **Step 1: Reframe architecture reference**

Replace the capability table in `docs/architecture/reference.md` with a method loop table:

```markdown
## 方法论闭环

平台面向外部 Runtime 的生产闭环是:

```text
Idea Pool -> Hypothesis -> Plan -> Experiment -> Result -> Review -> Decision -> Lesson -> Next Hypothesis
```

| 层 | 职责 |
| --- | --- |
| Idea Pool | 论文、repo、benchmark gap、研究员想法、历史失败和外部观察 |
| Hypothesis | 本轮要验证的研究假设，必须能追溯到 idea |
| Plan | 最小实验计划，记录唯一变化、验证方式、接受/拒绝标准和结果要求 |
| Experiment | 外部 Runtime 的一次执行记录；平台不执行实验 |
| Result | 分数、日志、图表、论文草稿、badcase 文件等外部 artifact 引用和轻量摘要 |
| Review | 对 result 的解释、审查、复盘或 artifact-aware review |
| Decision | keep、discard、continue、retry、blocked、archived 等迭代判断 |
| Lesson | 明确沉淀的可复用经验，用来指导下一轮 hypothesis 或 plan |
```

- [x] **Step 2: Collapse external runtime default flow**

In `docs/architecture/external-runtime-api.md`, replace the 31-step default flow with an 8-step method loop. Keep endpoint examples as current implementation mapping:

```markdown
## 默认流程

1. 接入自检: `GET /api/v1/agent/onboarding`
2. 恢复 idea pool: `POST /api/v1/experiences/query`, `GET /api/v1/research/context`
3. 登记 hypothesis 与 plan: 当前用 `POST /api/v1/hypotheses`、`POST /api/v1/research/protocols`
4. 启动 experiment: 当前用 `POST /api/v1/research/sessions`、`POST /api/v1/research/rounds`
5. 写入 result: 当前用 experiment、benchmark run 和 artifact endpoints
6. 写入 review: 当前用 evidence summary 和 review endpoints
7. 写入 decision: 当前用 `POST /api/v1/decisions`
8. 沉淀 lesson: `POST /api/v1/experiences/curation/preview` then `apply`
```

- [x] **Step 3: Collapse runtime cookbook minimum loop**

In `docs/examples/runtime-cookbook.md`, replace the 32-step minimum loop with the same 8-step loop and add a short "current API mapping" note so external Runtime users see a simple production path first.

### Task 2: Frontend Primary Path Reduction

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/pages/ResearchWorkbench.tsx`
- Modify: `frontend/src/app.test.mjs`

- [x] **Step 1: Reduce dashboard metrics**

Change `Dashboard.tsx` from 14 object counters and a 10-step workflow to 8 loop cards:

```ts
const loopCards = [
  { label: 'Idea Pool', path: '/sources', countKeys: ['sources', 'insights'] },
  { label: 'Hypothesis', path: '/insights', countKeys: ['hypotheses'] },
  { label: 'Plan', path: '/research/methodology', countKeys: ['research_questions', 'protocols'] },
  { label: 'Experiment', path: '/sessions', countKeys: ['sessions', 'research_rounds', 'experiments'] },
  { label: 'Result', path: '/artifacts', countKeys: ['artifacts', 'benchmark_runs'] },
  { label: 'Review', path: '/evidence', countKeys: ['evidence_records', 'reviews'] },
  { label: 'Decision', path: '/decisions', countKeys: ['decisions'] },
  { label: 'Lesson', path: '/knowledge/experiences', countKeys: ['experiences'] },
]
```

- [x] **Step 2: Reduce research workbench sections**

Change `ResearchWorkbench.tsx` to show three sections only:

```ts
const loopActions = [
  { path: '/sources', title: 'Idea Pool', copy: '管理论文、repo、研究员想法和历史失败等假设来源。' },
  { path: '/insights', title: 'Hypothesis', copy: '把 idea 收敛成可验证假设。' },
  { path: '/research/methodology', title: 'Plan', copy: '登记最小实验计划、接受/拒绝标准和结果要求。' },
  { path: '/sessions', title: 'Experiment', copy: '记录外部 Runtime 的执行过程。' },
  { path: '/artifacts', title: 'Result', copy: '登记分数、日志、图表、报告等外部结果引用。' },
  { path: '/evidence', title: 'Review', copy: '复盘结果、证据和质量缺口。' },
  { path: '/decisions', title: 'Decision', copy: '写入 keep、discard、continue、blocked 等判断。' },
  { path: '/knowledge/experiences', title: 'Lesson', copy: '沉淀可复用经验指导下一轮。' },
]
```

Keep secondary links for context/readiness/rounds/audit/capabilities/status under "高级审计".

- [x] **Step 3: Update static contract tests**

In `frontend/src/app.test.mjs`, replace assertions that require the old 10-step workflow labels and old research workbench grouping with assertions for:

```js
for (const label of ['Idea Pool', 'Hypothesis', 'Plan', 'Experiment', 'Result', 'Review', 'Decision', 'Lesson']) {
  assert(dashboardPage.includes(label), `dashboard missing loop label ${label}`)
  assert(researchWorkbenchPage.includes(label), `research workbench missing loop label ${label}`)
}
```

### Task 3: Verification

**Files:**
- No source file changes unless verification exposes a direct mismatch.

- [x] **Step 1: Run frontend static contract**

Run:

```bash
cd frontend && npm test
```

Expected: `frontend static contract ok`.

- [x] **Step 2: Run full test suite**

Run:

```bash
make test
```

Expected: backend pytest passes and frontend static contract passes.

- [x] **Step 3: Regenerate OpenAPI**

Run:

```bash
make openapi
```

Expected: command exits 0. After Task 4, `docs/openapi.json` includes the canonical method-loop endpoints.

### Task 4: Canonical Method Loop API

**Files:**
- Modify: `backend/autoresearch_platform/schemas/models.py`
- Modify: `backend/autoresearch_platform/routes/v1/api.py`
- Modify: `backend/autoresearch_platform/core/openapi_docs.py`
- Modify: `backend/autoresearch_platform/core/security.py`
- Modify: `backend/tests/test_api_contracts.py`
- Modify: `.agents/skills/auto-research/SKILL.md`

- [x] **Step 1: Add loop schema aliases**

Add slim request models for method-loop concepts that map onto existing store collections:

```text
IdeaCreate -> sources
PlanCreate -> protocols
ResultCreate -> artifacts
Lesson remains experiences curation preview/apply only
```

- [x] **Step 2: Add canonical loop routes**

Add:

```text
GET /api/v1/method-loop
POST /api/v1/ideas
GET /api/v1/ideas
POST /api/v1/plans
GET /api/v1/plans
POST /api/v1/results
GET /api/v1/results
GET /api/v1/lessons
```

Keep lesson writes on `POST /api/v1/experiences/curation/preview` and `apply` to preserve the explicit curation boundary.

- [x] **Step 3: Update OpenAPI discovery**

Add `method_loop` capability, add `/api/v1/method-loop` to public read-only discovery, and make onboarding recommend `GET /api/v1/method-loop`.

- [x] **Step 4: Verify new route contract**

Add tests proving the new routes map to backing collections and that `lessons` reads experiences created through curation apply.
