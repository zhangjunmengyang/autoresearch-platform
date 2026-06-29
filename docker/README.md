# Docker

Docker packaging is intentionally thin in v1. The durable deployment target is FastAPI plus PostgreSQL using the Alembic schema in `backend/migrations/`.

Local development can run without Docker through:

```bash
make doctor
make bootstrap
make start
```

The compose file starts three services:

- `api`: FastAPI REST/OpenAPI platform.
- `frontend`: React workbench.
- `postgres`: durable database service for deployments that opt into PostgreSQL.

The API defaults to `AUTORESEARCH_STORE_BACKEND=json`, which uses `data/autoresearch_store.json`. Set `AUTORESEARCH_STORE_BACKEND=postgres` when the Alembic migration has been applied and `AUTORESEARCH_DATABASE_URL` points at the PostgreSQL service.

Set `AUTORESEARCH_API_TOKEN` for non-local deployments that need the built-in Bearer-token boundary. When it is set, external Runtime calls to non-public API endpoints must include:

```bash
Authorization: Bearer $AUTORESEARCH_API_TOKEN
```

The token is not a provider-key manager and should not be written into platform records, artifact payloads or audit notes.

When `AUTORESEARCH_STORE_BACKEND=postgres`, the API container runs `alembic upgrade head` before starting FastAPI. The migration uses `AUTORESEARCH_DATABASE_URL`, converting `postgresql://` to the SQLAlchemy `postgresql+psycopg://` driver URL automatically.

The Alembic schema preserves platform text IDs with `id TEXT PRIMARY KEY` so external Runtime references remain stable across sources, sessions, rounds, artifacts, evidence and decisions. Do not replace these IDs with UUID surrogate keys in deployment-specific migrations.

Before treating a container stack as production-ready, call:

```bash
curl http://127.0.0.1:8010/api/v1/system/readiness
curl http://127.0.0.1:8010/api/v1/system/security
```

`degraded` is expected for local JSON development. `blocked` means the configured database or schema contract is not ready for production use. A PostgreSQL deployment should report `ready` before external Runtime traffic is routed to it.

```bash
cp .env.example .env
docker compose up
```

Platform containers must not mount or directly mutate external Runtime working directories. Runtime outputs should be registered through REST as artifact references.
