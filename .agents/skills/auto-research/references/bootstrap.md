# Bootstrap

Load this first for any formal AutoResearch run.

## Startup Checks

0. If operating from a repository checkout or release bundle, run the read-only onboarding smoke before a formal run:
   - `python3 scripts/validate_agent_onboarding.py --base-url http://127.0.0.1:8010/api/v1`
   - If `status=fail`, stop and report the failed checks.
   - If `onboarding_state=degraded`, proceed only when degraded research is acceptable and record the limitation in the session.
   - The script reads only onboarding and OpenAPI; it does not write platform data or touch external Runtime files.
1. Call `GET /api/v1/agent/onboarding`.
   - Inspect `state`, `security`, `readiness`, `capability_groups`, `skill.load_order`, `recommended_first_calls` and `recommended_next_actions`.
   - Treat it as a read-only onboarding bundle, not an execution plan.
2. Call `GET /api/v1/system/security` when you need the latest auth policy.
   - If `auth_required` is true, send the deployment token only in the `Authorization` header.
   - Do not write tokens into sources, events, artifacts, reviews, decisions, experiences, logs or notes.
3. Call `GET /api/v1/system/readiness` when you need the latest deployment gate.
   - `blocked`: stop and report the platform deployment gap.
   - `degraded`: proceed only for local/dev research and record the limitation.
   - `ready`: formal use is allowed.
4. Read `/api/v1/openapi.json` before relying on endpoint details. Treat OpenAPI as the route/schema drift checker.

## Context Recovery

1. Query durable memory with `POST /api/v1/experiences/query`.
2. Query `GET /api/v1/research/context?query=...&claim=...`.
3. Follow returned `risk_flags` and `recommended_next_actions` unless OpenAPI shows the contract changed.
4. If continuing an existing round, query `GET /api/v1/research/rounds/{round_id}` before doing any new work.

## Readiness Gates

Use `GET /api/v1/research/readiness?query=...&claim=...&round_id=...&stage=...` before these stages:

- `before_experiment`
- `before_review`
- `before_decision`
- `before_curation`

Resolve `blocked` checks first. Keep `degraded` in the session record.
