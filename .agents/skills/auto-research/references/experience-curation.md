# Experience Curation

Use this only when a durable lesson is warranted after evidence, review or decision.

## Required Flow

1. Call `GET /api/v1/research/readiness?stage=before_curation`.
2. Build an explicit curation payload from reviewed ledger, artifact, benchmark, evidence, review or decision records.
3. Call `POST /api/v1/experiences/curation/preview`.
4. Inspect `source_trace`, `governance_gaps`, `warnings`, `recommended_next_actions` and `safety`.
5. Call `POST /api/v1/experiences/curation/apply` only when every blocking gap is resolved.

## Source Rules

- Every durable experience needs resolvable `source_refs`.
- Prefer evidence records, reviews or decisions as sources.
- Session, artifact and benchmark run sources are allowed but should normally be backed by reviewed evidence before durable reuse.
- Do not create long-term experience by copying session fields mechanically.

## Actions

- `create`: new evidence-backed lesson.
- `update`: corrected lesson.
- `reject`: invalidated prior lesson.
- `supersede`: stronger lesson replaces older one.
- `topic_summary`: reviewed topic-level synthesis only.

See `examples/experience-curation.md` for request shapes.
