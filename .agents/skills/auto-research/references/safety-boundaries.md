# Safety Boundaries

Use this whenever a request touches execution, credentials, raw data, large artifacts, external files or uncertain status.

## Platform Boundary

The platform provides REST/OpenAPI facts, status, ledgers, artifact references, explicit experience maintenance and a React workbench.

Do not ask the platform to:

- call LLM providers
- route providers, manage keys, rate limits or cost
- run benchmark executors
- train models
- search architectures
- run agent loops
- create worktrees or commit code
- read/write external Runtime directories, databases or temporary scripts
- infer hidden relationships beyond explicit references
- store raw prompts, audio/video/PDF bodies, checkpoints or large benchmark outputs

## Status Semantics

- `blocked` is a valid answer. Stop and repair the missing contract, evidence, reference or deployment gap.
- `degraded` is a valid answer. Continue only when the degradation is acceptable and record it in the ledger.
- Do not convert uncertain results into completed records.

## Artifact Rules

Large artifacts stay in external storage. Platform records should contain URI, hash, MIME, size, storage, summary and small metadata only.

`GET /api/v1/artifacts/audit` checks metadata only. It does not download, open or validate external files.

## Credential Rules

Tokens stay in request headers. Never write provider keys, bearer tokens or secrets into platform records, events, artifacts, audit notes or experience text.
