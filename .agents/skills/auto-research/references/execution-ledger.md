# Execution Ledger

Use this when external work produces code changes, experiments, events, artifacts, benchmark runs or handoff material.

## Research Rounds

1. For a new方案, create a round with `POST /api/v1/research/rounds`.
2. If code or experiment setup changes, create worktree/branch in the external Runtime.
3. Store only `worktree`, `implementation_refs`, `experiment_refs`, `artifact_refs`, `evidence_refs` and `decision_refs`.
4. Query `GET /api/v1/research/rounds/{round_id}` before continuing and after patching references.
5. Treat the 追踪包 as read-only evidence. Resolve `unresolved_refs` before using the round as complete evidence.
6. Do not mark a round `completed` until it has at least one trace reference: commit, experiment, artifact, evidence or decision.

## Session Ledger

1. Start a session with memory context, constraints, primary path and information gain.
2. Record events for observations, decisions, tool runs, external instructions, generic runtime events and blockers.
3. Pre-register experiments before execution.
4. Query `GET /api/v1/research/events` and `GET /api/v1/research/experiments` when recovering prior process history.
5. Close the session with failed attempts, platform gaps, validated lessons and `next_agent_one_liner`.

## Artifacts And Benchmarks

- Store artifact references, not large payloads.
- Query `GET /api/v1/artifacts` when recovering prior outputs or checking reusable evidence.
- Query `GET /api/v1/artifacts/audit?session_id=...` before using artifacts as evidence, review input or decision support.
- Query `GET /api/v1/benchmarks/audit` before benchmark execution.
- Benchmark suites must describe external adapter, input contract, output contract, metric contract and artifact requirements.
- Submit benchmark runs only after the external Runtime executes the benchmark.
- Query `GET /api/v1/benchmark-runs/compare?benchmark_id=...&metric=...` after multiple runs to compare best run, score range, status distribution and evidence readiness gaps.
- Completed benchmark scores need artifact references or runner provenance.

## Handoff

Before handoff, replication or curation, call `GET /api/v1/research/audit/export?query=...&claim=...&session_id=...&round_id=...`.

Inspect:

- `reproducibility.checklist`
- `external_artifacts`
- `handoff_steps`

Verify artifact URI/hash in the external Runtime. The platform must remain read-only.
