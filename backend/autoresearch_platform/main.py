"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from autoresearch_platform.core.config import get_settings
from autoresearch_platform.core.openapi_docs import OPENAPI_DESCRIPTION, OPENAPI_TAGS, install_agent_openapi
from autoresearch_platform.core.security import authorize_request, should_audit_request
from autoresearch_platform.routes.v1.router import router as v1_router
from autoresearch_platform.services import JsonResearchStore, PostgresResearchStore, ResearchStore

settings = get_settings()
store: ResearchStore = (
    PostgresResearchStore(settings.database_url)
    if settings.store_backend == "postgres"
    else JsonResearchStore(settings.store_path)
)

app = FastAPI(
    title=settings.app_name,
    description=OPENAPI_DESCRIPTION,
    version="0.1.0",
    openapi_url=f"{settings.api_prefix}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=OPENAPI_TAGS,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix=settings.api_prefix)
install_agent_openapi(app)


def _write_audit_log(request: Request, *, status_code: int, auth_outcome: str) -> None:
    try:
        store.create_record(
            "logs",
            "log",
            {
                "event_type": "api_request",
                "title": f"{request.method} {request.url.path}",
                "actor": request.headers.get("x-autoresearch-actor", "anonymous"),
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "auth_outcome": auth_outcome,
                "query_keys": sorted(request.query_params.keys()),
                "payload": {
                    "body_storage": False,
                    "content_type": request.headers.get("content-type", ""),
                    "user_agent": request.headers.get("user-agent", ""),
                },
            },
        )
    except Exception:
        # Audit logging must not make a research API response fail.
        return


@app.middleware("http")
async def security_and_audit_middleware(request: Request, call_next):
    auth = authorize_request(
        request,
        api_prefix=settings.api_prefix,
        api_token=settings.api_token,
    )
    if not auth.allowed:
        response = JSONResponse({"detail": auth.reason}, status_code=401)
        if should_audit_request(request, auth):
            _write_audit_log(request, status_code=response.status_code, auth_outcome=auth.outcome)
        return response

    response = await call_next(request)
    if should_audit_request(request, auth):
        _write_audit_log(request, status_code=response.status_code, auth_outcome=auth.outcome)
    return response


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"name": settings.app_name, "openapi": f"{settings.api_prefix}/openapi.json"}
