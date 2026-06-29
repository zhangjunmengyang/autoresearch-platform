# Session Loop Example

Use this sequence when an external Agent or Runtime opens a formal research session.

1. `GET /api/v1/agent/onboarding`
2. `GET /api/v1/system/security`
3. `GET /api/v1/system/readiness`
4. `GET /api/v1/capabilities`
5. `POST /api/v1/experiences/query`
6. `GET /api/v1/research/context?query=...&claim=...`
7. `GET /api/v1/research/rounds/{round_id}` when continuing an existing round
8. `GET /api/v1/research/readiness?query=...&claim=...&round_id=...&stage=before_experiment`
9. `POST /api/v1/research/rounds`
10. `POST /api/v1/sources`
11. `POST /api/v1/insights`
12. `POST /api/v1/hypotheses`
13. `GET /api/v1/research/method-templates`
14. `POST /api/v1/research/programs`
15. `POST /api/v1/research/questions`
16. `POST /api/v1/research/method-cards`
17. `POST /api/v1/research/protocols`
18. `GET /api/v1/research/design/audit`
19. `POST /api/v1/research/intake`
20. `POST /api/v1/research/intake/{item_id}/claim`
21. `POST /api/v1/research/intake/{item_id}/start-session`
22. `POST /api/v1/research/sessions/{session_id}/events`
23. `POST /api/v1/research/sessions/{session_id}/experiments`
24. `POST /api/v1/research/sessions/{session_id}/artifacts`
25. `GET /api/v1/benchmarks/audit`
26. `POST /api/v1/benchmark-runs`
27. `GET /api/v1/benchmark-runs/compare?benchmark_id=...&metric=...`
28. `GET /api/v1/artifacts/audit?session_id=...`
29. `PATCH /api/v1/research/rounds/{round_id}`
30. `GET /api/v1/research/rounds/{round_id}` to verify the trace pack and `unresolved_refs`
31. `POST /api/v1/evidence-records`
32. `GET /api/v1/research/readiness?query=...&claim=...&round_id=...&stage=before_decision`
33. `GET /api/v1/evidence-records/summary?claim=...`
34. `POST /api/v1/reviews`
35. `GET /api/v1/reviews/audit?q=...`
36. `POST /api/v1/decisions`
37. `GET /api/v1/research/audit/export?query=...&claim=...&session_id=...&round_id=...`
38. `POST /api/v1/research/sessions/{session_id}/close`
39. `GET /api/v1/research/readiness?query=...&claim=...&round_id=...&stage=before_curation`
40. `POST /api/v1/experiences/curation/preview`
41. `POST /api/v1/experiences/curation/apply`

Rules:

- Check `/api/v1/openapi.json` before using endpoint details.
- Check `GET /api/v1/agent/onboarding` first to recover security, readiness, capability groups, Skill loading order and recommended first calls.
- Check `GET /api/v1/system/security` before protected calls. When `auth_required` is true, send the deployment token only through the `Authorization: Bearer <token>` header and never write it into platform records.
- Check `GET /api/v1/system/readiness` before formal work; `blocked` means platform deployment must be repaired first, and JSON `degraded` mode should be recorded as a development limitation.
- Use `/api/v1/research/context` to recover existing facts and avoid duplicating prior work.
- Use `GET /api/v1/research/method-templates` before writing a new method card or protocol; templates are read-only scaffolds and never execute experiments.
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
