# Research Design

Use this when turning a broad research goal into auditable platform records.

## Design Chain

1. Write source inputs with `POST /api/v1/sources` when context shows missing sources.
2. Write insights with `POST /api/v1/insights`.
3. Register hypotheses with `POST /api/v1/hypotheses`.
4. Read `GET /api/v1/research/method-templates` before creating new method cards or protocols.
   - Use templates such as literature synthesis, reproduction, ablation, benchmark comparison and failure analysis.
   - Treat templates as read-only design scaffolds; they do not generate experiments or execute benchmarks.
5. Register methodology objects when useful:
   - `POST /api/v1/research/programs`
   - `POST /api/v1/research/questions`
   - `POST /api/v1/research/method-cards`
   - `POST /api/v1/research/protocols`
6. Query `GET /api/v1/research/design/audit` before intake or experiment execution.
7. Create or claim an intake item with `/api/v1/research/intake` only after the design gate is acceptable.

## Design Quality

The design audit is a read-only gate, not a design generator.

- Method templates are read-only design guides. Use `required_records`, `protocol_defaults`, `artifact_requirements`, `evidence_expectations` and `review_gates` to prepare records, then explicitly write method cards and protocols through REST.
- A research question needs rationale and success criteria.
- A hypothesis needs expected effect, acceptance criteria, rejection criteria and source or insight references.
- A protocol needs one change, controls, acceptance/rejection criteria, artifact requirements, method card linkage and hypothesis linkage.

If `GET /api/v1/research/design/audit` returns `blocked`, repair answerability, falsifiability, controls, criteria or artifact requirements instead of executing experiments.

## Intake Boundary

Intake is a queue record. Claiming or starting intake does not execute an experiment. The external Runtime owns execution and writes only platform records through REST/OpenAPI.
