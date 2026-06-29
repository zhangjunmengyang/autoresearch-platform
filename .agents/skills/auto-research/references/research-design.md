# Research Design

Use this when turning a broad research goal into auditable method-loop records.

## Design Chain

1. Read `GET /api/v1/method-loop` and keep the visible path as Idea Pool -> Hypothesis -> Plan -> Experiment -> Result -> Review -> Decision -> Lesson.
2. Write missing Idea Pool entries with `POST /api/v1/ideas`.
3. Register hypotheses with `POST /api/v1/hypotheses`.
4. Read `GET /api/v1/research/method-templates` before choosing or extending a plan shape.
   - Use templates such as literature synthesis, reproduction, ablation, benchmark comparison and failure analysis.
   - Treat templates as read-only design scaffolds; they do not generate experiments or execute benchmarks.
5. Register the minimal plan with `POST /api/v1/plans`.
6. Register backing methodology objects only when the audit needs richer structure:
   - `POST /api/v1/research/programs`
   - `POST /api/v1/research/questions`
   - `POST /api/v1/research/method-cards`
   - `POST /api/v1/research/protocols`
7. Query `GET /api/v1/research/design/audit` before intake or experiment execution.
8. Create or claim an intake item with `/api/v1/research/intake` only after the design gate is acceptable.

## Design Quality

The design audit is a read-only gate, not a design generator.

- Method templates are read-only design guides. Use `required_records`, `protocol_defaults`, `artifact_requirements`, `evidence_expectations` and `review_gates` to prepare records, then explicitly write method cards and protocols through REST.
- An Idea Pool record needs kind, provenance or summary, and enough context to trace the source.
- A hypothesis needs expected effect, acceptance criteria, rejection criteria and idea/source references.
- A plan needs one change, validation method, controls, acceptance/rejection criteria and result requirements.
- A protocol or method card is optional backing detail, not the primary user-facing workflow.

If `GET /api/v1/research/design/audit` returns `blocked`, repair answerability, falsifiability, controls, criteria or artifact requirements instead of executing experiments.

## Intake Boundary

Intake is a queue record. Claiming or starting intake does not execute an experiment. The external Runtime owns execution and writes only platform records through REST/OpenAPI.
