---
name: auto-research
description: Use when an external Agent or Runtime operates AutoResearch Platform through REST/OpenAPI for memory-grounded research, readiness checks, round trace recovery, source insight, benchmark runs, generic runtime event logging, and explicit experience curation.
---

# AutoResearch Runtime Workflow

Use `/api/v1/openapi.json` as the route and schema checker. Use this skill as the method and endpoint-composition source.

The platform is a control plane and ledger. It does not call models, execute benchmarks, train models, run agent loops, create worktrees, read external Runtime directories, or read large artifact payloads.

## Load Order

1. Always read `references/bootstrap.md` before a formal run.
2. For planning and preregistration, read `references/research-design.md`.
3. For code-changing rounds, sessions, experiments, artifacts, benchmark runs or handoff, read `references/execution-ledger.md`.
4. For evidence, review or decision work, read `references/evidence-review-decision.md`.
5. For durable memory updates, read `references/experience-curation.md`.
6. If any request touches platform boundaries, blocked/degraded handling, external files, raw payloads, credentials or large artifacts, read `references/safety-boundaries.md`.

## Capability References

- `references/bootstrap.md`: security, deployment readiness, OpenAPI drift check, historical memory and context recovery.
- `references/research-design.md`: sources, insights, hypotheses, method templates, methodology objects, `GET /api/v1/research/design/audit`, and intake.
- `references/execution-ledger.md`: research rounds, 追踪包, `GET /api/v1/research/rounds/{round_id}`, sessions, events, experiments, artifacts, benchmark audit and handoff.
- `references/evidence-review-decision.md`: evidence records, `quality_gaps`, `replication_plan`, review audit and decision records.
- `references/experience-curation.md`: explicit curation preview/apply, `source_trace`, `governance_gaps`, topic summaries and source provenance.
- `references/safety-boundaries.md`: status semantics, credential handling, metadata-only artifacts, no execution and no hidden relationship inference.

Detailed examples:

- `examples/session-loop.md`: full session loop endpoint order.
- `examples/experience-curation.md`: explicit experience curation actions and evidence rules.

## Minimum Loop

1. `GET /api/v1/agent/onboarding`
2. `GET /api/v1/system/security`
3. `GET /api/v1/system/readiness`
4. `POST /api/v1/experiences/query`
5. `GET /api/v1/research/context?query=...&claim=...`
6. `GET /api/v1/research/readiness?query=...&claim=...&round_id=...&stage=before_experiment`
7. Read `GET /api/v1/research/method-templates`, register design and run `GET /api/v1/research/design/audit`.
8. Record the round/session work through REST only.
9. Before using outputs as evidence, run `GET /api/v1/artifacts/audit` and `GET /api/v1/reviews/audit` as appropriate.
10. Before handoff or curation, run `GET /api/v1/research/audit/export` and inspect `reproducibility.checklist`, `external_artifacts` and `handoff_steps`.
11. Durable memory must go through `POST /api/v1/experiences/curation/preview` before `POST /api/v1/experiences/curation/apply`.

## Non-Negotiables

- Treat `blocked` and `degraded` as valid results; do not force completion when evidence, references, design quality, artifact metadata or review quality is incomplete.
- Use `GET /api/v1/research/readiness` as a read-only 就绪检查 before execution, review, decision and curation.
- Use the round 追踪包 as read-only evidence; resolve `unresolved_refs` before treating a round as complete.
- For a new方案 that changes code or experiment setup, create worktree/branch in the external Runtime, then write only references back to the platform.
- Query evidence summary before accepting a claim; `quality_gaps` and `replication_plan` drive the next experiment or review.
- Never store raw prompts, provider keys, bearer tokens, large artifacts, benchmark dumps, checkpoints, audio/video/PDF bodies or external Runtime working files in the platform.
