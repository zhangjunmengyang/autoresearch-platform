# FARS Runtime Console Reduction Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 AutoResearch Platform 的人类界面从对象管理和人工填报面收敛成 FARS 风格的自动研究运行看板。AI Runtime 通过 REST/OpenAPI 写入 idea、hypothesis、plan、experiment、result、review、decision、lesson；人类只观察 deployments、research runs、outputs、质量门和阻塞状态。

**Architecture:** 不破坏后端合同。保留旧路由供 API debug 和外部 Runtime 兼容，但从主导航、Dashboard 和 Research Workbench 中移除“登记/写入/账本/人工复盘”式入口，改为 FARS/Karpathy 命名的只读生产主线。

**Tech Stack:** React/Vite, TanStack Query, FastAPI/OpenAPI, Markdown docs, Node static contract tests, pytest.

---

### Task 1: Product Surface Reduction

**Files:**
- Modify: `frontend/src/lib/page-config.ts`
- Modify: `frontend/src/components/AppShell.tsx`

- [x] **Step 1: Collapse main navigation**

Keep the visible navigation to production observer surfaces:

```text
Console: FARS 看板, Research Runs, Outputs
System: 能力目录, 系统状态
```

Do not expose sources, insights, methodology, sessions, evidence, benchmarks, reviews, decisions, experiences or research rounds as primary human workflow entries.

- [x] **Step 2: Update shell copy**

Rename the product subtitle and header note so the shell states that the platform is an AI-driven research control plane and that people watch runtime state instead of filling the loop.

### Task 2: FARS Runtime Dashboard

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/styles/globals.css`

- [x] **Step 1: Replace loop cards**

Replace the object-entry metric cards with a FARS runtime console layout:

```text
FARS Runtime Console
FARS DEPLOYMENTS
RESEARCH RUNS
OUTPUTS
REVIEW / DECISION
```

Use status collection counts to derive deployments, active runs, output references, completed reports and blocked/degraded items. Keep the UI read-only and link only to observer pages.

- [x] **Step 2: Add method stage lane**

Show the FARS-style stage lane:

```text
Ideation -> Planning -> Experimentation -> Writing -> Review -> Decision
```

Map existing collection counts into each stage, but do not expose a form-like action per stage.

### Task 3: Research Workbench Reduction

**Files:**
- Modify: `frontend/src/pages/ResearchWorkbench.tsx`

- [x] **Step 1: Replace action grids**

Replace human action links with read-only cards for:

```text
FARS DEPLOYMENTS
RESEARCH RUNS
PIPELINE SNAPSHOT
RUNTIME CONTRACT
```

Use REST query results where possible and degrade to loading/empty state without asking humans to fill missing data.

- [x] **Step 2: Keep audit as detail only**

Expose context, readiness and audit export as small diagnostic links. Do not put ledger, evidence, benchmark or decision forms in the main path.

### Task 4: Documentation Alignment

**Files:**
- Modify: `docs/architecture/reference.md`
- Modify: `docs/examples/runtime-cookbook.md`
- Modify: `.agents/skills/auto-research/SKILL.md`

- [x] **Step 1: State UI boundary**

Add a clear statement that the React workbench is observer-only for humans. Write operations are for external Runtime through REST/OpenAPI.

- [x] **Step 2: Align loop names**

Use FARS-like stage names in docs while preserving the current canonical API mapping.

### Task 5: Static Contract and Verification

**Files:**
- Modify: `frontend/src/app.test.mjs`

- [x] **Step 1: Update static tests**

Assert that the visible nav and workbench contain FARS observer terms and do not contain form-first labels such as “登记”, “写入”, “人工”, “账本” or “评测登记”.

- [x] **Step 2: Run verification**

Run:

```bash
cd frontend && npm test
cd frontend && npm run typecheck
make test
make openapi
```

Then verify the rendered Dashboard and Research Runs pages in the browser at desktop and mobile widths.
