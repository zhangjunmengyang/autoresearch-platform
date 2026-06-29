# Session Loop Example

Use this sequence when an external Agent or Runtime opens a formal research session. Keep the visible path as a compact method loop, and use the heavier ledger endpoints only as quality gates or trace backing.

## Compact Method Loop

1. Bootstrap: `GET /api/v1/agent/onboarding`, `GET /api/v1/method-loop`, `GET /api/v1/system/security`, `GET /api/v1/system/readiness`, then verify endpoint details through `/api/v1/openapi.json`.
2. Idea Pool: recover prior context with `POST /api/v1/experiences/query` and `GET /api/v1/research/context?query=...&claim=...`; register missing papers, repos, datasets, benchmark gaps, researcher ideas, historical failures or runtime observations with `POST /api/v1/ideas`.
3. Hypothesis: register the falsifiable claim with `POST /api/v1/hypotheses`.
4. Plan: read `GET /api/v1/research/method-templates`, write the minimal plan with `POST /api/v1/plans`, and run `GET /api/v1/research/design/audit`.
5. Experiment: before external execution, call `GET /api/v1/research/readiness?query=...&claim=...&round_id=...&stage=before_experiment`. For trace backing, create or recover the round with `POST /api/v1/research/rounds` and `GET /api/v1/research/rounds/{round_id}`; use sessions, events and experiments only to record what the external Runtime did.
6. Result: write the compact result with `POST /api/v1/results`. If the result came from a benchmark, use `GET /api/v1/benchmarks/audit`, `POST /api/v1/benchmark-runs` and `GET /api/v1/benchmark-runs/compare?benchmark_id=...&metric=...` as supporting records. Run `GET /api/v1/artifacts/audit?session_id=...` before using external artifacts as evidence.
7. Review: create evidence records only when there is a concrete result to judge with `POST /api/v1/evidence-records`, then call `GET /api/v1/evidence-records/summary?claim=...`. Use `quality_gaps` and `replication_plan` to decide whether the next step is another experiment or a review. Write the review with `POST /api/v1/reviews` and run `GET /api/v1/reviews/audit?q=...`.
8. Decision: before accepting or rejecting the hypothesis, call `GET /api/v1/research/readiness?query=...&claim=...&round_id=...&stage=before_decision`, then write `POST /api/v1/decisions`.
9. Lesson: export a handoff bundle with `GET /api/v1/research/audit/export?query=...&claim=...&session_id=...&round_id=...`, close the session if one exists with `POST /api/v1/research/sessions/{session_id}/close`, run `GET /api/v1/research/readiness?query=...&claim=...&round_id=...&stage=before_curation`, preview with `POST /api/v1/experiences/curation/preview`, and only then apply with `POST /api/v1/experiences/curation/apply`.

## Rules

- Check `/api/v1/openapi.json` before using endpoint details.
- Check `GET /api/v1/agent/onboarding` first to recover security, readiness, capability groups, Skill loading order and recommended first calls.
- Check `GET /api/v1/method-loop` before choosing route names; the canonical stages are Idea Pool, Hypothesis, Plan, Experiment, Result, Review, Decision and Lesson.
- Check `GET /api/v1/system/security` before protected calls. When `auth_required` is true, send the deployment token only through the `Authorization: Bearer <token>` header and never write it into platform records.
- Check `GET /api/v1/system/readiness` before formal work; `blocked` means platform deployment must be repaired first, and JSON `degraded` mode should be recorded as a development limitation.
- Use `/api/v1/research/context` to recover existing facts and avoid duplicating prior work.
- Use `GET /api/v1/research/method-templates` before writing a new plan shape; templates are read-only scaffolds and never execute experiments.
- Run `GET /api/v1/research/design/audit` before intake or experiment execution; blocked design gaps require answerable questions, falsifiable hypotheses, controls, criteria and artifact requirements.
- Use `GET /api/v1/research/readiness` as a read-only preflight before experiment, review, decision and curation stages.
- For code-changing方案, create worktree and branch in the external Runtime, then store only references in `/api/v1/research/rounds`.
- Use `GET /api/v1/research/rounds/{round_id}` to recover the round trace pack before continuing work and after patching refs.
- Resolve `unresolved_refs` before treating a round as complete evidence.
- Run `GET /api/v1/artifacts/audit` before using artifacts as evidence; blocked metadata gaps require re-registering external references.
- Run `GET /api/v1/benchmarks/audit` before benchmark execution; blocked suite contract gaps require adding external adapter, input, output, metrics and artifact requirements.
- Run `GET /api/v1/benchmark-runs/compare` after submitting multiple runs; use it to choose best/baseline/conflicting runs and repair missing artifact or runner provenance before evidence.
- Use `blocked` or `degraded` when evidence is incomplete.
- Submit artifact references instead of raw outputs.
- Audit logs are metadata-only. Do not put request bodies, provider keys, Bearer tokens, raw external inputs, benchmark dumps or checkpoints into audit payloads.
- Do not execute experiments through the platform.
- Do not write a review or decision before creating evidence records when there is a concrete result to judge.
- Query evidence summary before accepting a claim; conflict, insufficient states, `quality_gaps` and `replication_plan` require more external Runtime work.
- Run `GET /api/v1/reviews/audit` before decisions; missing reviewer provenance, comments, evidence_refs or score/concerns require a stronger review.
- Do not write a decision without evidence references.
- Export `GET /api/v1/research/audit/export` before handoff or curation when another Agent needs a reproducible bundle.
- Curation preview must show resolved `source_trace` and no blocking `governance_gaps` before `POST /api/v1/experiences/curation/apply`.
