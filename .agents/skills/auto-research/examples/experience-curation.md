# Experience Curation Example

Long-term experience is explicit. Do not create it by copying session fields mechanically.

## Create

Use `create` when a new lesson is supported by evidence. Prefer source references that point to decisions, evidence records, reviews, benchmark runs or artifacts:

```json
{
  "action": "create",
  "runtime": {"name": "external-runtime", "operator": "external-runtime"},
  "experience": {
    "title": "Benchmark runs need provenance",
    "problem": "Scores without runner or artifact evidence are not auditable.",
    "topics": ["agent-memory"]
  },
  "source_refs": [{"type": "decision", "id": "decision_demo"}]
}
```

Call `POST /api/v1/experiences/curation/preview` first. Inspect `source_trace`, `governance_gaps` and `recommended_next_actions`. Call `apply` only when every blocking gap is resolved; unresolved source refs must be fixed instead of accepted as durable memory.

## Update

Use `update` when an existing lesson needs correction:

```json
{
  "action": "update",
  "runtime": {"name": "external-runtime", "operator": "external-runtime"},
  "experience": {
    "id": "experience_demo",
    "title": "Corrected lesson title",
    "problem": "Corrected and evidence-backed lesson."
  },
  "source_refs": [{"type": "benchmark_run", "id": "benchrun_demo"}]
}
```

## Reject

Use `reject` when evidence invalidates a prior lesson. Keep `source_refs` pointing to the decision, evidence record, review, benchmark or artifact that invalidated it.

## Supersede

Use `supersede` when stronger evidence replaces an old lesson:

```json
{
  "action": "supersede",
  "runtime": {"name": "external-runtime", "operator": "external-runtime"},
  "experience": {
    "supersedes": "experience_old",
    "title": "New stronger lesson",
    "problem": "The old lesson was incomplete."
  },
  "source_refs": [{"type": "decision", "id": "decision_new"}]
}
```

## Topic Summary

Use `topic_summary` only after reviewed evidence exists. Topic summaries are synthesis records, not raw notes.
