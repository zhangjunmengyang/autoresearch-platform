# Evidence, Review And Decision

Use this after a concrete result, replication attempt, benchmark run, artifact or source has evidence value.

## Evidence Records

1. Submit evidence records with `POST /api/v1/evidence-records`.
2. Every evidence record needs `evidence_refs`.
3. Bind the claim to supporting, contradicting, mixed, inconclusive, replication or failed-replication evidence.
4. Query `GET /api/v1/evidence-records/summary?claim=...` before review or decision.

## Evidence Summary

Read the summary as a deterministic audit, not a generated conclusion.

- `contested`: investigate conflict before accepting the claim.
- `insufficient`: collect or register more evidence.
- `quality_gaps`: repair weak confidence, missing replication, single-session evidence or missing subject binding.
- `replication_plan`: use as the next experiment or protocol input.

## Review

1. Submit automated critic, external Runtime or necessary human review with `POST /api/v1/reviews`.
2. Query `GET /api/v1/reviews/audit?q=...` before writing decisions.
3. Missing reviewer provenance, comments, evidence references, score or concerns means the review is not strong enough for durable decisions.

## Decision

1. Submit decisions with `POST /api/v1/decisions`.
2. Decisions must include `evidence_refs`.
3. Use decisions to record accept, reject, continue, block, supersede or archive.
4. Decisions are audit records, not automatic experience extraction.
